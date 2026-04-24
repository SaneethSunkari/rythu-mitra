"""
Rythu Mitra — Crop Recommendation Engine
5-filter system. Never recommends a crop that fails any filter.
"""

import sys
import os
from functools import lru_cache

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.nizamabad_district import (
    MANDALS, CROPS, DISTRICT_PLANTED_ACRES,
    BOT_RECOMMENDED_ACRES, CURRENT_SEASON
)
from engine.cap_logic import (
    TELUGU_COMPETITION_LABELS,
    derive_pressure_status,
    get_effective_safe_cap,
)
from engine.district_cap import DistrictCapTracker
from engine.weather_pipeline import WeatherPipeline


# ── FARMER PROFILE ─────────────────────────────────────────────────────────────

class FarmerProfile:
    def __init__(
        self,
        mandal,
        acres,
        water_source=None,
        loan_burden_rs=0,
        last_crops=None,
        soil_zone=None,
        farmer_id=None,
        survey_number=None,
    ):
        if mandal not in MANDALS:
            raise ValueError(f"Unknown mandal: {mandal}. Check MANDALS dict.")
        self.mandal = mandal
        self.mandal_data = MANDALS[mandal]
        self.soil_zone = soil_zone or self.mandal_data["soil_zone"]
        self.water_source = water_source or self.mandal_data["water"]
        self.acres = acres
        self.loan_burden = loan_burden_rs   # total outstanding loan in ₹
        self.last_crops = last_crops or []
        self.farmer_id = farmer_id
        self.survey_number = survey_number

    def build_farmer_key(self) -> str:
        if self.farmer_id:
            return str(self.farmer_id)
        return (
            f"{self.mandal}|{self.acres}|{self.soil_zone}|"
            f"{self.water_source}|{','.join(self.last_crops)}"
        )


# ── WEATHER STUB (replaced by Open-Meteo API in production) ───────────────────

@lru_cache(maxsize=1)
def _district_weather_forecast() -> dict:
    """
    Returns season-aware rainfall and temperature guidance.
    Uses district seasonal expectations plus a live Open-Meteo short-term read
    when available, and falls back safely if the API cannot be reached.
    """
    fallback = {
        "expected_rainfall_mm": 820,
        "next_7_day_rain_mm": None,
        "temp_max_avg_c": 32,
        "temp_min_avg_c": 24,
        "drought_risk": False,
        "flood_risk": False,
        "source": "district_profile_stub",
    }

    try:
        payload = WeatherPipeline(forecast_days=7).fetch_forecast()
        daily = payload.get("daily", {})
        rain_sums = daily.get("precipitation_sum", [])
        rain_probs = daily.get("precipitation_probability_max", [])
        max_temps = daily.get("temperature_2m_max", [])
        min_temps = daily.get("temperature_2m_min", [])

        next_7_day_rain_mm = round(sum(rain_sums), 1) if rain_sums else 0.0
        temp_max_avg_c = round(sum(max_temps) / len(max_temps), 1) if max_temps else fallback["temp_max_avg_c"]
        temp_min_avg_c = round(sum(min_temps) / len(min_temps), 1) if min_temps else fallback["temp_min_avg_c"]
        drought_risk = next_7_day_rain_mm < 5 and temp_max_avg_c >= 39
        flood_risk = next_7_day_rain_mm >= 50 or any(prob >= 80 for prob in rain_probs)

        return {
            "expected_rainfall_mm": fallback["expected_rainfall_mm"],
            "next_7_day_rain_mm": next_7_day_rain_mm,
            "temp_max_avg_c": temp_max_avg_c,
            "temp_min_avg_c": temp_min_avg_c,
            "drought_risk": drought_risk,
            "flood_risk": flood_risk,
            "source": "open_meteo_plus_district_profile",
        }
    except Exception:
        return fallback


def get_weather_forecast(mandal: str) -> dict:
    """
    Mandal arg stays for API compatibility, but the forecast is district-wide.
    """
    return dict(_district_weather_forecast())


# ── FILTER 1: SOIL MATCH ───────────────────────────────────────────────────────

def filter_soil(candidates: list, soil_zone: str, mandal: str | None = None) -> list:
    """Remove crops that cannot grow in this soil type or are locally unsuitable."""
    mandal_data = MANDALS.get(mandal, {}) if mandal else {}
    unsuitable_crops = set(mandal_data.get("unsuitable_crops", []))
    return [
        c for c in candidates
        if soil_zone in CROPS[c]["soil_compatible"] and c not in unsuitable_crops
    ]


def get_current_season_name() -> str:
    """Extract kharif/rabi/zaid from CURRENT_SEASON like kharif_2025."""
    return CURRENT_SEASON.split("_", 1)[0].lower()


def filter_season(candidates: list, season_name: str) -> list:
    """Keep only crops that fit the active season."""
    return [
        c for c in candidates
        if season_name in CROPS[c].get("season", [])
    ]


# ── FILTER 2: WATER + WEATHER MATCH ───────────────────────────────────────────

def filter_water_weather(candidates: list, water_source: str,
                         weather: dict) -> list:
    """
    Water requirement tiers:
      very_high → canal only
      high      → canal or >700mm rainfall
      medium    → mixed / rainfed OK if >600mm
      low       → rainfed OK
    """
    keep = []
    rain = weather["expected_rainfall_mm"]

    for crop in candidates:
        req = CROPS[crop]["water_requirement"]
        if req == "very_high":
            if "canal" not in water_source:
                continue    # REJECT: sugarcane without canal → impossible
        elif req == "high":
            if water_source == "rainfed" and (rain < 700 or weather.get("drought_risk")):
                continue    # REJECT: paddy rainfed with low rain
        elif req == "medium":
            if water_source == "rainfed" and (rain < 500 or weather.get("drought_risk")):
                continue
        # low water crops pass all conditions
        keep.append(crop)
    return keep


# ── FILTER 3: DISTRICT SUPPLY CAP ─────────────────────────────────────────────

def filter_supply_cap(candidates: list, mandal: str,
                      farmer_acres: int) -> tuple[list, dict]:
    """
    KEY FEATURE — prevents bot from creating new rat race.

    Total supply = govt planted acres + bot recommended acres.
    If total exceeds 80% of safe cap → mark as OVERSUPPLY.
    If total + this farmer's acres would exceed 100% cap → REJECT.

    Returns: (viable_candidates, supply_info_dict)
    """
    keep = []
    supply_info = {}
    tracker = DistrictCapTracker()
    season_bot_acres = tracker.get_recommended_acres_by_crop(CURRENT_SEASON)

    for crop in candidates:
        crop_data = CROPS[crop]
        safe_cap, cap_basis = get_effective_safe_cap(crop)
        planted = DISTRICT_PLANTED_ACRES.get(crop, 0)
        bot_rec = BOT_RECOMMENDED_ACRES.get(crop, 0) + season_bot_acres.get(crop, 0)
        total_acres = planted + bot_rec
        projected_total = total_acres + farmer_acres

        # Sugarcane: only viable near mills
        if crop == "sugarcane":
            mill_mandals = crop_data.get("viable_mandals", [])
            if mandal not in mill_mandals:
                supply_info[crop] = {"status": "REJECT", "reason": "No sugar mill within 30km"}
                continue

        if not safe_cap:
            supply_info[crop] = {
                "status": "LOW",
                "planted_acres": planted,
                "bot_recommended": bot_rec,
                "total_acres": total_acres,
                "projected_total_acres": projected_total,
                "safe_cap": None,
                "pct_filled": None,
                "projected_pct_filled": None,
                "cap_basis": cap_basis,
            }
            keep.append(crop)
            continue

        status, pct_filled, projected_pct = derive_pressure_status(
            total_acres,
            projected_total,
            safe_cap,
        )

        supply_info[crop] = {
            "status": status,
            "planted_acres": planted,
            "bot_recommended": bot_rec,
            "total_acres": total_acres,
            "projected_total_acres": projected_total,
            "safe_cap": safe_cap,
            "pct_filled": pct_filled,
            "projected_pct_filled": projected_pct,
            "cap_basis": cap_basis,
        }

        if status != "REJECT":
            keep.append(crop)

    return keep, supply_info


# ── FILTER 4: PRICE PREDICTION ─────────────────────────────────────────────────

def add_price_prediction(candidates: list, water_source: str) -> dict:
    """
    Calculates realistic price range at harvest.
    Uses 5-year history to get floor, avg, ceiling.
    NEVER promises a single price — always gives range.
    """
    predictions = {}

    for crop in candidates:
        crop_data = CROPS[crop]

        # Sugarcane has fixed price — no prediction needed
        if crop == "sugarcane":
            predictions[crop] = {
                "floor_price": 370,
                "avg_price": 370,
                "ceiling_price": 370,
                "note": "Fixed government price. No market risk.",
            }
            continue

        history = crop_data.get("price_history_qtl", {})
        if not history:
            continue

        years = sorted(history.keys())
        floors = [history[y]["min"] for y in years]
        avgs = [history[y]["avg"] for y in years]
        ceilings = [history[y]["max"] for y in years]

        # Weight recent 2 years more heavily
        if len(avgs) >= 2:
            weighted_avg = (
                avgs[-1] * 0.4 + avgs[-2] * 0.3 +
                sum(avgs[:-2]) / max(len(avgs) - 2, 1) * 0.3
            )
        else:
            weighted_avg = avgs[-1]

        # Floor = worst year min (protects farmer from optimism)
        floor = min(floors)
        ceiling = max(ceilings)

        predictions[crop] = {
            "floor_price": round(floor),
            "avg_price": round(weighted_avg),
            "ceiling_price": round(ceiling),
            "current_price": history.get(max(years), {}).get("avg", weighted_avg),
            "years_data": len(years),
        }

    return predictions


# ── FILTER 5: NET PROFIT + CASH SURVIVABILITY ──────────────────────────────────

def filter_profitability(candidates: list, acres: int,
                         water_source: str, loan_burden: int,
                         price_predictions: dict) -> list:
    """
    Calculates net profit at floor price (worst case).
    REJECT if floor-price net is negative (protects farmer from loss).
    Returns ranked list: (crop, net_current, net_floor, yield_avg)
    """
    results = []
    seasonal_debt_service_due = round(max(loan_burden, 0) * 0.15)

    for crop in candidates:
        crop_data = CROPS[crop]
        pred = price_predictions.get(crop)
        if not pred:
            continue

        # Choose yield based on water source
        yield_key = "canal_irrigated" if "canal" in water_source else "rainfed"
        yield_data = crop_data.get("yield_qtl_per_acre", {})
        yields = (
            yield_data.get(yield_key)
            or yield_data.get("rainfed")
            or yield_data.get("canal_irrigated")
        )
        if not yields:
            continue

        avg_yield = yields["avg"]
        input_cost = crop_data.get("input_cost_per_acre", 0)

        # Transport: assume Armur mandi (reasonable mid-point)
        transport_per_quintal = 15      # ₹15/qtl avg transport cost
        commission_pct = 0.02           # 2% mandi commission

        def net(price_per_qtl):
            gross = avg_yield * price_per_qtl
            transport = avg_yield * transport_per_quintal
            commission = gross * commission_pct
            return round((gross - transport - commission - input_cost) * acres)

        net_current = net(pred["avg_price"])
        net_floor = net(pred["floor_price"])
        net_after_debt_service = net_floor - seasonal_debt_service_due

        # REJECT if floor-price net is negative or cannot survive debt pressure.
        if net_floor < 0 or net_after_debt_service < 0:
            continue

        if seasonal_debt_service_due == 0:
            cash_flow_status = "stable"
        else:
            debt_share = seasonal_debt_service_due / max(net_floor, 1)
            if debt_share >= 0.75:
                cash_flow_status = "tight"
            elif debt_share >= 0.4:
                cash_flow_status = "watch"
            else:
                cash_flow_status = "stable"

        results.append({
            "crop": crop,
            "net_current": net_current,
            "net_floor": net_floor,
            "net_after_debt_service": net_after_debt_service,
            "avg_yield": avg_yield,
            "input_cost_total": input_cost * acres,
            "seasonal_debt_service_due": seasonal_debt_service_due,
            "cash_flow_status": cash_flow_status,
            "price_current": pred["avg_price"],
            "price_floor": pred["floor_price"],
            "price_ceiling": pred["ceiling_price"],
        })

    # Sort by net floor price (safest bet first)
    results.sort(key=lambda x: x["net_floor"], reverse=True)
    return results


# ── MAIN ENGINE ────────────────────────────────────────────────────────────────

def recommend(farmer: FarmerProfile) -> dict:
    """
    Runs all 5 filters. Returns structured recommendation.
    """
    season_name = get_current_season_name()
    tracker = DistrictCapTracker()
    weather = get_weather_forecast(farmer.mandal)
    all_crops = [
        crop_name for crop_name, crop_data in CROPS.items()
        if crop_data.get("active_for_recommendation", True)
    ]

    # Pre-filter — Season
    after_season = filter_season(all_crops, season_name)

    # Filter 1 — Soil
    after_soil = filter_soil(after_season, farmer.soil_zone, farmer.mandal)

    # Filter 2 — Water + Weather
    after_water = filter_water_weather(after_soil, farmer.water_source, weather)

    # Filter 3 — District supply cap
    after_supply, supply_info = filter_supply_cap(
        after_water, farmer.mandal, farmer.acres
    )

    # Filter 4 — Price prediction
    price_preds = add_price_prediction(after_supply, farmer.water_source)

    # Filter 5 — Net profit + cash survivability
    ranked = filter_profitability(
        after_supply, farmer.acres,
        farmer.water_source, farmer.loan_burden,
        price_preds
    )
    ranked_crop_names = [r["crop"] for r in ranked]

    # Build rejected list for transparency
    rejected = []
    for crop in all_crops:
        if crop not in ranked_crop_names:
            if crop in supply_info and supply_info[crop]["status"] == "REJECT":
                rejected.append({"crop": crop, "reason": supply_info[crop].get("reason", "Supply cap exceeded")})
            elif crop not in after_season:
                rejected.append({"crop": crop, "reason": f"Season mismatch ({season_name})"})
            elif crop not in after_soil:
                rejected.append({"crop": crop, "reason": "Soil or local suitability mismatch"})
            elif crop not in after_water:
                rejected.append({"crop": crop, "reason": "Water requirement not met"})
            else:
                rejected.append({"crop": crop, "reason": "Loss or cash risk at floor price"})

    return {
        "farmer": farmer,
        "season": CURRENT_SEASON,
        "season_name": season_name,
        "weather": weather,
        "ranked": ranked,
        "supply_info": supply_info,
        "bot_recommended_acres_current_season": tracker.get_recommended_acres_by_crop(CURRENT_SEASON),
        "rejected": rejected,
        "top_pick": ranked[0] if ranked else None,
        "second_pick": ranked[1] if len(ranked) > 1 else None,
    }


# ── TELUGU RESPONSE GENERATOR ──────────────────────────────────────────────────

def generate_telugu_response(result: dict) -> str:
    """
    Converts engine output into Telugu bot response.
    Warm, specific, like a son speaking to his father.
    """
    f = result["farmer"]
    top = result["top_pick"]
    second = result["second_pick"]
    supply = result["supply_info"]

    if not top:
        return (
            f"Naanna, meeru soil ({f.soil_zone}) ki ee season lo "
            f"profitable crop suggest cheyyatam kashtam ga undi. "
            f"Nearest KVK Nizamabad contact cheyyandi: 08462-226360. "
            f"Vaallaki meeru situation cheppi advise theeskoandi."
        )

    crop_tel = CROPS[top["crop"]].get("telugu_name", top["crop"])
    sup = supply.get(top["crop"], {})
    competition_label = TELUGU_COMPETITION_LABELS.get(sup.get("status", "MEDIUM"), "")

    lines = [
        f"Naanna, naanu {f.acres} acres, {f.soil_zone} soil, "
        f"{f.water_source} water — anni crops analyse chesanu.",
        "",
        f"BEST CHOICE — {crop_tel} ({top['crop'].upper()}):",
        f"  Rate range: floor ₹{top['price_floor']:,} / avg ₹{top['price_current']:,} / ceiling ₹{top['price_ceiling']:,} per quintal",
        f"  Meeru {f.acres} acres ki expected profit: ₹{top['net_current']:,}",
        f"  Worst case profit: ₹{top['net_floor']:,}",
        f"  Appu pressure tharvatha migiledi: ₹{top['net_after_debt_service']:,}",
        f"  District lo: {competition_label}",
    ]

    if second:
        crop2_tel = CROPS[second["crop"]].get("telugu_name", second["crop"])
        lines += [
            "",
            f"SECOND OPTION — {crop2_tel} ({second['crop'].upper()}):",
            f"  Rate range: floor ₹{second['price_floor']:,} / avg ₹{second['price_current']:,} / ceiling ₹{second['price_ceiling']:,}",
            f"  Expected profit: ₹{second['net_current']:,}",
            f"  Worst case: ₹{second['net_floor']:,}",
        ]

    lines += [
        "",
        "Naanu guarantee ivvaleddu — market ela marustundo teliyadam ledu.",
        "Ee numbers data cheptunnai. Last word meeru — meeru feel cheppandi.",
        "Inka edaina doubt unte naaku cheppandi.",
    ]

    return "\n".join(lines)


# ── TEST ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("RYTHU MITRA — ENGINE TEST")
    print("Saneeth's father: Annaram, Nandipet mandal, 10 acres")
    print("=" * 60)

    farmer = FarmerProfile(
        mandal="nandipet",
        acres=10,
        water_source="mixed",
        loan_burden_rs=200000,
        last_crops=["paddy"]
    )

    result = recommend(farmer)

    print(f"\nSoil zone : {farmer.soil_zone}")
    print(f"Water     : {farmer.water_source}")
    print(f"\nRANKED CROPS (floor-price safe, best first):")
    for r in result["ranked"]:
        print(f"  {r['crop']:15} | net current ₹{r['net_current']:>9,} | net floor ₹{r['net_floor']:>9,} | competition: {result['supply_info'].get(r['crop'], {}).get('status', '?')}")

    print(f"\nREJECTED:")
    for r in result["rejected"]:
        print(f"  {r['crop']:15} | {r['reason']}")

    print(f"\n{'─' * 60}")
    print("TELUGU BOT RESPONSE:")
    print('─' * 60)
    print(generate_telugu_response(result))
