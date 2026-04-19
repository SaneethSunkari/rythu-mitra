"""Export a frontend-friendly dashboard dataset from the current backend state."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import engine.crop_engine as crop_engine_module
from data.nizamabad_district import (
    BOT_RECOMMENDED_ACRES,
    CROPS,
    CURRENT_SEASON,
    DISTRICT_PLANTED_ACRES,
    MANDALS,
    MANDIS,
)
from engine.crop_engine import (
    FarmerProfile,
    add_price_prediction,
    filter_profitability,
    filter_season,
    filter_soil,
    filter_supply_cap,
    filter_water_weather,
    generate_telugu_response,
    get_current_season_name,
    get_weather_forecast,
    recommend,
)
from engine.district_cap import DistrictCapTracker
from engine.price_pipeline import PricePipeline
from engine.weather_pipeline import WeatherPipeline


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = ROOT / "dashboard" / "src" / "data" / "dashboardData.json"
PRICE_CACHE_PATH = ROOT / "data" / "cache" / "mandi_prices_latest.json"
WEATHER_DAILY_CACHE_PATH = ROOT / "data" / "cache" / "weather_daily_forecasts.json"
DASHBOARD_WEATHER = {
    "expected_rainfall_mm": 820,
    "next_7_day_rain_mm": 12.0,
    "temp_max_avg_c": 34,
    "temp_min_avg_c": 24,
    "drought_risk": False,
    "flood_risk": False,
    "source": "dashboard_export_snapshot",
}

crop_engine_module.get_weather_forecast = lambda _mandal: DASHBOARD_WEATHER.copy()


def slug_to_label(slug: str) -> str:
    return slug.replace("_", " ").title()


def crop_meta(crop_slug: str) -> dict:
    crop = CROPS[crop_slug]
    return {
        "slug": crop_slug,
        "name": slug_to_label(crop_slug),
        "teluguName": crop.get("telugu_name", crop_slug),
        "season": crop.get("season", []),
        "active": crop.get("active_for_recommendation", True),
    }


def load_price_rows() -> list[dict]:
    if PRICE_CACHE_PATH.exists():
        return json.loads(PRICE_CACHE_PATH.read_text(encoding="utf-8"))
    return PricePipeline().build_fallback_rows()


def load_weather_rows() -> list[dict]:
    if WEATHER_DAILY_CACHE_PATH.exists():
        return json.loads(WEATHER_DAILY_CACHE_PATH.read_text(encoding="utf-8"))
    return WeatherPipeline().normalize_daily_rows(WeatherPipeline().fetch_forecast())


def build_crop_caps() -> list[dict]:
    tracker = DistrictCapTracker()
    season_bot_acres = tracker.get_recommended_acres_by_crop(CURRENT_SEASON)
    rows = []

    for crop_slug, crop in CROPS.items():
        if not crop.get("active_for_recommendation", True):
            continue

        safe_cap = crop.get("safe_cap_acres")
        planted = DISTRICT_PLANTED_ACRES.get(crop_slug, 0)
        bot_recommended = BOT_RECOMMENDED_ACRES.get(crop_slug, 0) + season_bot_acres.get(crop_slug, 0)
        total = planted + bot_recommended

        if safe_cap:
            pct = round((total / safe_cap) * 100, 1)
            if total >= safe_cap:
                status = "REJECT"
                label = "already crowded"
            elif pct >= 70:
                status = "OVERSUPPLY"
                label = "high caution"
            elif pct >= 45:
                status = "MEDIUM"
                label = "watch closely"
            else:
                status = "LOW"
                label = "opportunity"
        else:
            pct = None
            status = "LOW"
            label = "legacy baseline"

        rows.append({
            **crop_meta(crop_slug),
            "safeCapAcres": safe_cap,
            "plantedAcres": planted,
            "botRecommendedAcres": bot_recommended,
            "totalAcres": total,
            "pctFilled": pct,
            "status": status,
            "statusLabel": label,
        })

    status_order = {"REJECT": 0, "OVERSUPPLY": 1, "MEDIUM": 2, "LOW": 3}
    rows.sort(key=lambda item: (status_order.get(item["status"], 9), item["name"]))
    return rows


def build_filter_trace(farmer: FarmerProfile) -> list[dict]:
    season_name = get_current_season_name()
    weather = DASHBOARD_WEATHER.copy()
    candidates = [
        crop_name for crop_name, crop_data in CROPS.items()
        if crop_data.get("active_for_recommendation", True)
    ]
    after_season = filter_season(candidates, season_name)
    after_soil = filter_soil(after_season, farmer.soil_zone)
    after_water = filter_water_weather(after_soil, farmer.water_source, weather)
    after_supply, supply_info = filter_supply_cap(after_water, farmer.mandal, farmer.acres)
    price_preds = add_price_prediction(after_supply, farmer.water_source)
    ranked = filter_profitability(after_supply, farmer.acres, farmer.water_source, farmer.loan_burden, price_preds)

    oversupply = [
        crop_meta(crop_slug)["name"]
        for crop_slug, info in supply_info.items()
        if info.get("status") == "OVERSUPPLY"
    ]
    blocked_by_supply = [
        crop_meta(crop_slug)["name"]
        for crop_slug, info in supply_info.items()
        if info.get("status") == "REJECT"
    ]

    return [
        {
            "id": "season",
            "title": "Season gate",
            "kept": len(after_season),
            "removed": len(candidates) - len(after_season),
            "note": f"{season_name.title()} crops only. Out-of-season crops are removed before scoring starts.",
            "highlights": [crop_meta(crop)["name"] for crop in after_season[:5]],
        },
        {
            "id": "soil",
            "title": "Soil filter",
            "kept": len(after_soil),
            "removed": len(after_season) - len(after_soil),
            "note": f"Only crops compatible with {slug_to_label(farmer.soil_zone)} soil survive.",
            "highlights": [crop_meta(crop)["name"] for crop in after_soil[:5]],
        },
        {
            "id": "water",
            "title": "Water + weather filter",
            "kept": len(after_water),
            "removed": len(after_soil) - len(after_water),
            "note": f"Water source is {slug_to_label(farmer.water_source)}. Drought and flood risk are checked here.",
            "highlights": [crop_meta(crop)["name"] for crop in after_water[:5]],
        },
        {
            "id": "supply",
            "title": "District cap filter",
            "kept": len(after_supply),
            "removed": len(after_water) - len(after_supply),
            "note": "This is the anti-rat-race layer. The bot avoids recommending crops that are already crowding the district.",
            "highlights": blocked_by_supply[:3] or oversupply[:3] or [crop_meta(crop)["name"] for crop in after_supply[:3]],
        },
        {
            "id": "profit",
            "title": "Floor-price survivability",
            "kept": len(ranked),
            "removed": len(after_supply) - len(ranked),
            "note": "Only crops that stay profitable even at conservative floor prices make the final list.",
            "highlights": [crop_meta(item["crop"])["name"] for item in ranked[:3]],
        },
    ]


def build_mandal_snapshot() -> list[dict]:
    mandal_rows = []

    for mandal_slug, mandal in sorted(MANDALS.items()):
        primary_crops = mandal.get("primary_crops", [])
        farmer = FarmerProfile(
            mandal=mandal_slug,
            acres=5,
            soil_zone=mandal.get("soil_zone"),
            water_source=mandal.get("water"),
            loan_burden_rs=0,
            last_crops=primary_crops[:1],
            farmer_id=f"dashboard-{mandal_slug}",
        )
        result = recommend(farmer)
        top_pick = result.get("top_pick")
        second_pick = result.get("second_pick")
        top_supply = result.get("supply_info", {}).get(top_pick["crop"], {}) if top_pick else {}

        mandal_rows.append({
            "slug": mandal_slug,
            "name": slug_to_label(mandal_slug),
            "soilZone": mandal.get("soil_zone"),
            "waterSource": mandal.get("water"),
            "villages": mandal.get("villages"),
            "primaryCrops": [slug_to_label(crop) for crop in primary_crops],
            "nearestMandi": mandal.get("nearest_mandis", [{}])[0].get("name"),
            "nearestMandiDistanceKm": mandal.get("nearest_mandis", [{}])[0].get("distance_km"),
            "topPick": crop_meta(top_pick["crop"]) if top_pick else None,
            "secondPick": crop_meta(second_pick["crop"]) if second_pick else None,
            "topPickExpectedProfit": top_pick["net_current"] if top_pick else None,
            "topPickWorstProfit": top_pick["net_floor"] if top_pick else None,
            "competitionStatus": top_supply.get("status", "NONE"),
            "notes": mandal.get("notes", ""),
            "snapshotAssumption": "Representative 5-acre profile using default mandal soil and water with no loan burden.",
        })

    return mandal_rows


def build_demo_scenarios() -> list[dict]:
    scenarios = [
        {
            "id": "annaram-family",
            "title": "Annaram family test",
            "profile": {
                "mandal": "nandipet",
                "acres": 10,
                "soil_zone": "deep_calcareous",
                "water_source": "mixed",
                "loan_burden_rs": 200000,
                "last_crops": ["paddy"],
            },
            "messages": [
                "nandipet",
                "10 acres",
                "deep calcareous mixed water",
                "last crop paddy, loan 2 lakh undi",
            ],
        },
        {
            "id": "bodhan-canal",
            "title": "Bodhan canal farmer",
            "profile": {
                "mandal": "bodhan",
                "acres": 5,
                "soil_zone": "black_cotton",
                "water_source": "canal",
                "loan_burden_rs": 0,
                "last_crops": ["cotton"],
            },
            "messages": [
                "bodhan",
                "5 acres",
                "black cotton canal water",
                "last crop cotton, no loan",
            ],
        },
        {
            "id": "kamareddy-rainfed",
            "title": "Kamareddy rainfed farmer",
            "profile": {
                "mandal": "kamareddy",
                "acres": 6,
                "soil_zone": "red_clayey",
                "water_source": "rainfed",
                "loan_burden_rs": 80000,
                "last_crops": ["maize", "soybean"],
            },
            "messages": [
                "kamareddy",
                "6 acres",
                "red clayey rainfed",
                "last crop maize soybean, loan 80 thousand undi",
            ],
        },
    ]

    rendered = []

    for index, scenario in enumerate(scenarios, start=1):
        farmer = FarmerProfile(farmer_id=f"dashboard-demo-{index}", **scenario["profile"])
        result = recommend(farmer)

        transcript = [
            {"speaker": "bot", "text": "Mundu mee mandal cheppandi naanna."},
            {"speaker": "farmer", "text": scenario["messages"][0]},
            {"speaker": "bot", "text": "Mee acres entha naanna?"},
            {"speaker": "farmer", "text": scenario["messages"][1]},
            {
                "speaker": "bot",
                "text": "Mee soil type enti? Water source enti? Udaharanaki: black cotton, borewell.",
            },
            {"speaker": "farmer", "text": scenario["messages"][2]},
            {
                "speaker": "bot",
                "text": "Last 3 crops emi vesaru? Loan unda? Udaharanaki: paddy, turmeric, maize. Loan 2 lakh undi. Ledu ante 'no loan' ani cheppandi.",
            },
            {"speaker": "farmer", "text": scenario["messages"][3]},
            {"speaker": "bot", "text": generate_telugu_response(result)},
        ]

        rendered.append({
            "id": scenario["id"],
            "title": scenario["title"],
            "profile": {
                "mandal": slug_to_label(scenario["profile"]["mandal"]),
                "acres": scenario["profile"]["acres"],
                "soilZone": slug_to_label(scenario["profile"]["soil_zone"]),
                "waterSource": slug_to_label(scenario["profile"]["water_source"]),
                "loanBurden": scenario["profile"]["loan_burden_rs"],
                "lastCrops": [slug_to_label(crop) for crop in scenario["profile"]["last_crops"]],
            },
            "topPick": crop_meta(result["top_pick"]["crop"]) if result["top_pick"] else None,
            "secondPick": crop_meta(result["second_pick"]["crop"]) if result["second_pick"] else None,
            "filterTrace": build_filter_trace(farmer),
            "rejected": [
                {
                    "crop": slug_to_label(item["crop"]),
                    "reason": item["reason"],
                }
                for item in result["rejected"][:6]
            ],
            "teluguReply": generate_telugu_response(result),
            "conversation": transcript,
        })

    return rendered


def build_summary(crop_caps: list[dict], mandals: list[dict], price_rows: list[dict], weather_rows: list[dict]) -> dict:
    return {
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "currentSeason": CURRENT_SEASON,
        "mandalCount": len(MANDALS),
        "mandiCount": len(MANDIS),
        "cropCount": len(CROPS),
        "activeRecommendationCrops": len([crop for crop in CROPS.values() if crop.get("active_for_recommendation", True)]),
        "oversuppliedCropCount": len([item for item in crop_caps if item["status"] in {"REJECT", "OVERSUPPLY"}]),
        "openOpportunityCropCount": len([item for item in crop_caps if item["status"] == "LOW"]),
        "mandalTopPickCount": len([item for item in mandals if item.get("topPick")]),
        "priceRowCount": len(price_rows),
        "weatherDayCount": len(weather_rows),
    }


def main() -> None:
    crop_caps = build_crop_caps()
    price_rows = load_price_rows()
    weather_rows = load_weather_rows()
    mandals = build_mandal_snapshot()
    scenarios = build_demo_scenarios()

    payload = {
        "summary": build_summary(crop_caps, mandals, price_rows, weather_rows),
        "cropCaps": crop_caps,
        "mandals": mandals,
        "priceRows": price_rows,
        "weatherDaily": weather_rows,
        "demoScenarios": scenarios,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Wrote dashboard data -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
