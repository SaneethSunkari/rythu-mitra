"""Scenario-specific follow-up logic layered on top of the core crop engine."""

from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from bot.canal_alerts import CanalAlertService
from bot.crop_cycle_service import CropCycleService, parse_farming_date
from bot.farmer_profile import (
    CROP_ALIASES,
    FarmerProfile as StoredFarmerProfile,
    _normalize_text,
)
from data.nizamabad_district import (
    CROPS,
    CURRENT_SEASON,
    DISTRICT_PLANTED_ACRES,
    MANDALS,
    SCHEMES,
)
from data.specialty_crops import SPECIALTY_CROPS
from engine.crop_engine import (
    FarmerProfile as EngineFarmerProfile,
    add_price_prediction,
    filter_profitability,
    filter_season,
    filter_soil,
    filter_supply_cap,
    filter_water_weather,
    get_current_season_name,
    get_weather_forecast,
    recommend,
)
from engine.district_cap import DistrictCapTracker
from engine.long_cycle_outlook import LongCycleOutlookService, render_long_cycle_reply
from engine.price_pipeline import LOCAL_PRICE_CACHE_PATH, PricePipeline
from engine.weather_pipeline import WeatherPipeline


LEGAL_PRIVATE_INTEREST_REDLINE_ANNUAL = 24.0
KVK_PHONE = "08462-226360"
CROP_CYCLE_SERVICE = CropCycleService()
CANAL_ALERT_SERVICE = CanalAlertService(crop_cycle_service=CROP_CYCLE_SERVICE)
LONG_CYCLE_OUTLOOK_SERVICE = LongCycleOutlookService()


def maybe_handle_followup(profile: StoredFarmerProfile, message_text: str) -> str | None:
    """Return a specialized scenario reply when the follow-up matches one."""

    normalized = _normalize_text(message_text)
    if not normalized:
        return None

    if _is_crisis_question(normalized):
        return _crisis_reply()

    if _is_bot_wrong_question(normalized):
        return _bot_wrong_reply(profile)

    if _is_crop_failure_question(normalized):
        return _crop_failure_reply(profile)

    if _is_sell_land_question(normalized):
        return _sell_land_reply(profile)

    if _is_fairness_question(normalized):
        reply = _fairness_reply(profile, normalized)
        if reply:
            return reply

    if _is_alternative_crop_question(normalized):
        reply = _alternative_crop_reply(profile, normalized)
        if reply:
            return reply

    if _is_trader_offer_question(normalized):
        reply = _trader_offer_reply(profile, normalized)
        if reply:
            return reply

    if _is_market_sale_question(normalized):
        reply = _best_market_reply(profile, normalized)
        if reply:
            return reply

    if _has_high_interest_pattern(normalized):
        return _high_interest_reply(profile, normalized)

    if _is_deadline_panic(normalized):
        return _debt_deadline_reply(profile, normalized)

    if _is_scheme_question(normalized):
        return _personalized_scheme_reply(profile)

    if _is_crop_pressure_question(normalized):
        reply = _crop_pressure_reply(profile, normalized)
        if reply:
            return reply

    if _is_idle_land_question(normalized):
        return _idle_land_reply(profile)

    if _is_input_cost_question(normalized):
        return _input_cost_reply(profile)

    if _is_delayed_monsoon_question(normalized):
        return _delayed_monsoon_reply(profile)

    if _is_drought_question(normalized):
        return _drought_reply(profile)

    if _is_feedback_question(normalized):
        return _season_feedback_reply()

    if _is_intercrop_question(normalized):
        return _intercrop_reply(profile)

    if _is_referral_question(normalized):
        return _referral_reply()

    if _is_text_symptom_question(normalized):
        reply = _text_symptom_reply(profile, normalized)
        if reply:
            return reply

    if _is_labour_shortage_question(normalized):
        return _labour_shortage_reply(profile)

    if _is_seed_variety_question(normalized):
        return _seed_variety_reply(profile)

    if _is_counterfeit_seed_question(normalized):
        return _counterfeit_seed_reply()

    if _is_pesticide_upsell_question(normalized):
        return _pesticide_upsell_reply(profile)

    if _is_buyer_not_found_question(normalized):
        return _buyer_not_found_reply(profile)

    if _is_weather_alert_question(normalized):
        return _daily_weather_preview_reply()

    if _is_calendar_question(normalized):
        return _season_calendar_reply(profile, normalized)

    if _is_proactive_disease_question(normalized):
        return _proactive_disease_reply(profile)

    if _is_drying_question(normalized):
        return _drying_alert_reply(profile, normalized)

    if _is_specialty_monitoring_question(normalized):
        return _specialty_monitoring_reply(profile, normalized)

    if _is_long_cycle_outlook_question(normalized):
        return _long_cycle_outlook_reply(profile, normalized)

    if _is_canal_release_question(normalized):
        return _canal_release_reply(profile, normalized)

    reply = _contextual_advice_reply(profile, normalized)
    if reply:
        return reply

    return None


def _build_engine_farmer(profile: StoredFarmerProfile) -> EngineFarmerProfile:
    return EngineFarmerProfile(
        mandal=profile.mandal,
        acres=profile.acres or 0,
        soil_zone=profile.soil_type,
        water_source=profile.water_source,
        loan_burden_rs=profile.loan_burden_rs,
        last_crops=profile.last_three_crops,
        farmer_id=profile.phone_number,
    )


def _money(value: int | float | None) -> str:
    if value is None:
        return "₹0"
    return f"₹{int(round(value)):,}"


def _load_current_price_rows() -> list[dict[str, Any]]:
    cache_path = Path(LOCAL_PRICE_CACHE_PATH)
    if cache_path.exists():
        try:
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            if isinstance(payload, list) and payload:
                return payload
        except json.JSONDecodeError:
            pass
    return PricePipeline().build_fallback_rows()


def _extract_supported_crop(normalized_text: str, profile: StoredFarmerProfile | None = None) -> str | None:
    aliases = sorted(CROP_ALIASES.items(), key=lambda item: len(item[0]), reverse=True)
    for alias, canonical in aliases:
        if canonical not in CROPS and canonical not in SPECIALTY_CROPS:
            continue
        if re.search(rf"\b{re.escape(alias)}\b", normalized_text):
            return canonical

    if profile:
        for crop in profile.last_three_crops:
            if crop in CROPS or crop in SPECIALTY_CROPS:
                return crop
    return None


def _extract_multiple_supported_crops(normalized_text: str) -> list[str]:
    found: list[str] = []
    aliases = sorted(CROP_ALIASES.items(), key=lambda item: len(item[0]), reverse=True)
    for alias, canonical in aliases:
        if canonical not in CROPS and canonical not in SPECIALTY_CROPS:
            continue
        if canonical in found:
            continue
        if re.search(rf"\b{re.escape(alias)}\b", normalized_text):
            found.append(canonical)
    return found


def _extract_price_offer(normalized_text: str) -> int | None:
    match = re.search(r"(?:₹|rs\.?\s*)?(\d{3,5})(?:\s*/?\s*qtl)?", normalized_text)
    if not match:
        return None
    return int(match.group(1))


def _extract_interest_monthly_pct(normalized_text: str) -> float | None:
    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:%|percent)?\s*(?:per\s*)?(?:month|monthly|nelaku|nela)",
        normalized_text,
    )
    if match:
        return float(match.group(1))
    return None


def _extract_days_count(normalized_text: str) -> int | None:
    match = re.search(r"(\d{1,3})\s*(?:day|days|rojulu|roju)", normalized_text)
    if match:
        return int(match.group(1))
    return None


def _crowded_crops_summary(limit: int = 3) -> list[dict[str, Any]]:
    tracker = DistrictCapTracker()
    seasonal_bot = tracker.get_recommended_acres_by_crop(CURRENT_SEASON)
    rows: list[dict[str, Any]] = []

    for crop_slug, crop_data in CROPS.items():
        safe_cap = crop_data.get("safe_cap_acres")
        if not safe_cap:
            continue
        planted = DISTRICT_PLANTED_ACRES.get(crop_slug, 0)
        bot_acres = seasonal_bot.get(crop_slug, 0)
        pct = ((planted + bot_acres) / safe_cap) * 100
        rows.append(
            {
                "crop": crop_slug,
                "pct": round(pct, 1),
                "planted": planted,
                "bot_acres": bot_acres,
            }
        )

    rows.sort(key=lambda item: item["pct"], reverse=True)
    return rows[:limit]


def _build_crop_snapshot(profile: StoredFarmerProfile, crop_slug: str) -> dict[str, Any] | None:
    if crop_slug not in CROPS:
        return None

    farmer = _build_engine_farmer(profile)
    season_name = get_current_season_name()
    weather = get_weather_forecast(farmer.mandal)

    season_ok = crop_slug in filter_season([crop_slug], season_name)
    soil_ok = crop_slug in filter_soil([crop_slug], farmer.soil_zone, farmer.mandal)
    water_ok = crop_slug in filter_water_weather([crop_slug], farmer.water_source, weather)
    _, supply_info = filter_supply_cap([crop_slug], farmer.mandal, farmer.acres)
    supply = supply_info.get(crop_slug, {})

    price_predictions = add_price_prediction([crop_slug], farmer.water_source)
    price = price_predictions.get(crop_slug)
    profitability = None
    if price:
        profit_rows = filter_profitability(
            [crop_slug],
            farmer.acres,
            farmer.water_source,
            farmer.loan_burden,
            price_predictions,
        )
        if profit_rows:
            profitability = profit_rows[0]

    if not season_ok:
        reason = f"Season mismatch ({season_name})"
    elif not soil_ok:
        reason = "Soil or local suitability mismatch"
    elif not water_ok:
        reason = "Water requirement not met"
    elif supply.get("status") == "REJECT":
        reason = supply.get("reason", "Supply cap exceeded")
    elif not profitability:
        reason = "Loss or cash risk at floor price"
    else:
        reason = None

    return {
        "crop": crop_slug,
        "season_ok": season_ok,
        "soil_ok": soil_ok,
        "water_ok": water_ok,
        "supply": supply,
        "price": price,
        "profitability": profitability,
        "rejection_reason": reason,
        "viable": reason is None,
    }


def _best_market_options(profile: StoredFarmerProfile, crop_slug: str) -> list[dict[str, Any]]:
    price_rows = [row for row in _load_current_price_rows() if row.get("crop_slug") == crop_slug]
    distance_map = {
        item["name"]: float(item["distance_km"])
        for item in MANDALS[profile.mandal].get("nearest_mandis", [])
    }

    crop_data = CROPS[crop_slug]
    yield_key = "canal_irrigated" if "canal" in (profile.water_source or "") else "rainfed"
    yield_data = crop_data.get("yield_qtl_per_acre", {})
    yield_row = yield_data.get(yield_key) or yield_data.get("rainfed") or yield_data.get("canal_irrigated") or {"avg": 10}
    estimated_total_qtl = max(1.0, float(yield_row["avg"]) * float(profile.acres or 1))

    options: list[dict[str, Any]] = []
    for row in price_rows:
        mandi_name = row["mandi_name"]
        if mandi_name not in distance_map:
            continue
        modal = float(row.get("modal_price_rs_per_qtl") or 0)
        distance_km = distance_map[mandi_name]
        transport_total = max(250.0, distance_km * 35.0)
        transport_per_qtl = transport_total / estimated_total_qtl
        commission_per_qtl = modal * 0.02
        net_per_qtl = modal - transport_per_qtl - commission_per_qtl
        options.append(
            {
                "mandi_name": mandi_name,
                "distance_km": distance_km,
                "modal_price": int(round(modal)),
                "transport_total": int(round(transport_total)),
                "transport_per_qtl": int(round(transport_per_qtl)),
                "commission_per_qtl": int(round(commission_per_qtl)),
                "net_per_qtl": int(round(net_per_qtl)),
            }
        )

    options.sort(key=lambda item: item["net_per_qtl"], reverse=True)
    return options


def _recommendation_bundle(profile: StoredFarmerProfile) -> tuple[EngineFarmerProfile, dict[str, Any]]:
    farmer = _build_engine_farmer(profile)
    return farmer, recommend(farmer)


def _contextual_advice_reply(profile: StoredFarmerProfile, normalized_text: str) -> str | None:
    mentioned_crops = _extract_multiple_supported_crops(normalized_text)
    compare_signal = any(
        phrase in normalized_text
        for phrase in (
            "which is better",
            "edi better",
            "yedi better",
            "compare",
            "difference",
            "versus",
            "vs",
            "better for me",
        )
    )
    why_signal = any(
        phrase in normalized_text
        for phrase in (
            "why not",
            "enduku vaddu",
            "enduku kaadu",
            "enduku suggest cheyyaledu",
            "enduku recommend cheyyaledu",
        )
    )
    preference = _extract_preference_focus(normalized_text)
    broad_advice_signal = any(
        phrase in normalized_text
        for phrase in (
            "emi veyali",
            "which crop",
            "best crop",
            "best option",
            "ippudu emi",
            "naku suggest",
            "naaku suggest",
            "mee suggestion",
            "suggest cheyyu",
        )
    )

    if why_signal and mentioned_crops:
        return _why_not_crop_reply(profile, mentioned_crops[0])

    if compare_signal and mentioned_crops:
        return _compare_crops_reply(profile, mentioned_crops[:2])

    if preference:
        return _preference_guided_reply(profile, preference, mentioned_crops[:1])

    if broad_advice_signal:
        return _general_context_reply(profile)

    return None


def _extract_preference_focus(normalized_text: str) -> str | None:
    low_risk = any(
        phrase in normalized_text
        for phrase in ("takkuva risk", "safe option", "safer option", "less risk", "risk takkuva", "low risk")
    )
    high_income = any(
        phrase in normalized_text
        for phrase in ("high income", "income ekkuva", "profit ekkuva", "ekkuva profit", "ekkuva income", "high profit")
    )
    if low_risk and high_income:
        return "high_income_low_risk"
    if any(
        phrase in normalized_text
        for phrase in ("takkuva risk", "safe option", "safer option", "less risk", "risk takkuva", "low risk")
    ):
        return "low_risk"
    if any(
        phrase in normalized_text
        for phrase in (
            "takkuva investment",
            "low investment",
            "low cost",
            "input takkuva",
            "investment takkuva",
            "cost ekkuva",
            "ekkuva cost",
            "investment ekkuva",
            "input cost ekkuva",
        )
    ):
        return "low_investment"
    if high_income:
        return "high_income"
    if any(
        phrase in normalized_text
        for phrase in ("quick cash", "fast money", "tvaraga dabbulu", "short term", "early cash")
    ):
        return "quick_cash"
    if any(
        phrase in normalized_text
        for phrase in ("less water", "takkuva water", "water takkuva", "neellu takkuva", "low water")
    ):
        return "low_water"
    if any(
        phrase in normalized_text
        for phrase in ("less labour", "takkuva labour", "takkuva labor", "labour takkuva", "labor takkuva")
    ):
        return "low_labour"
    if any(
        phrase in normalized_text
        for phrase in ("price safe", "market safe", "dhara safe", "safe market")
    ):
        return "market_safety"
    return None


def _describe_focus(focus: str) -> str:
    labels = {
        "low_risk": "takkuva risk",
        "low_investment": "takkuva investment",
        "high_income": "ekkuva income",
        "high_income_low_risk": "ekkuva income + takkuva risk",
        "quick_cash": "quick cash flow",
        "low_water": "takkuva water need",
        "low_labour": "takkuva labour load",
        "market_safety": "market safety",
    }
    return labels.get(focus, focus)


def _sort_rows_for_focus(rows: list[dict[str, Any]], focus: str) -> list[dict[str, Any]]:
    def water_score(crop_slug: str) -> int:
        requirement = CROPS[crop_slug].get("water_requirement")
        order = {"low": 0, "medium": 1, "high": 2, "very_high": 3}
        return order.get(requirement, 99)

    def labour_score(crop_slug: str) -> tuple[int, int]:
        crop = CROPS[crop_slug]
        return (
            int(crop.get("input_cost_per_acre", 0)),
            int(crop.get("grow_duration_days", 999)),
        )

    if focus in {"low_risk", "market_safety"}:
        return sorted(rows, key=lambda item: item["net_floor"], reverse=True)
    if focus == "high_income":
        return sorted(rows, key=lambda item: item["net_current"], reverse=True)
    if focus == "high_income_low_risk":
        return sorted(
            rows,
            key=lambda item: (
                item["net_floor"],
                item["net_current"],
            ),
            reverse=True,
        )
    if focus == "low_investment":
        return sorted(
            rows,
            key=lambda item: (
                CROPS[item["crop"]].get("input_cost_per_acre", 0),
                -item["net_floor"],
            ),
        )
    if focus == "quick_cash":
        return sorted(
            rows,
            key=lambda item: (
                CROPS[item["crop"]].get("grow_duration_days", 999),
                -item["net_floor"],
            ),
        )
    if focus == "low_water":
        return sorted(
            rows,
            key=lambda item: (
                water_score(item["crop"]),
                -item["net_floor"],
            ),
        )
    if focus == "low_labour":
        return sorted(
            rows,
            key=lambda item: (
                labour_score(item["crop"]),
                -item["net_floor"],
            ),
        )
    return rows


def _rank_for_focus(result: dict[str, Any], focus: str) -> list[dict[str, Any]]:
    ranked = list(result.get("ranked", []))
    return _sort_rows_for_focus(ranked, focus)


def _crop_summary_line(row: dict[str, Any]) -> str:
    crop = CROPS[row["crop"]]
    return (
        f"{crop.get('telugu_name', row['crop'])} ({row['crop'].upper()}): "
        f"expected {_money(row['net_current'])}, worst case {_money(row['net_floor'])}."
    )


def _general_context_reply(profile: StoredFarmerProfile) -> str:
    _, result = _recommendation_bundle(profile)
    top = result.get("top_pick")
    second = result.get("second_pick")

    if not top:
        return (
            "Naanna, mee current profile batti strong safe crop clear ga kanapadaledu. "
            f"Specific crop peru cheppandi lekapothe KVK {KVK_PHONE} side kuda check cheddam."
        )

    top_row = next((item for item in result.get("ranked", []) if item["crop"] == top["crop"]), None)
    lines = [
        f"Naanna, mee profile ki ippudu best safe option {CROPS[top['crop']].get('telugu_name', top['crop'])}.",
    ]
    if top_row:
        lines.append(
            f"Expected {_money(top_row['net_current'])}, worst case {_money(top_row['net_floor'])} varaku hold avtundi."
        )
    if second:
        lines.append(
            f"Second side {CROPS[second['crop']].get('telugu_name', second['crop'])} kuda undi."
        )
    lines.append(
        "Meeru compare cheyyali ante crop peru cheppandi, lekapothe takkuva risk / takkuva investment / quick cash ani cheppandi."
    )
    return " ".join(lines)


def _why_not_crop_reply(profile: StoredFarmerProfile, crop_slug: str) -> str | None:
    snapshot = _build_crop_snapshot(profile, crop_slug)
    if not snapshot:
        return None

    crop_name = CROPS[crop_slug].get("telugu_name", crop_slug)
    _, result = _recommendation_bundle(profile)
    top = result.get("top_pick")

    if snapshot["viable"] and snapshot["profitability"]:
        return (
            f"Naanna, {crop_name} full ga reject kaaledu. "
            f"Kani current shortlist lo top kaadu. Floor-safe profit {_money(snapshot['profitability']['net_floor'])} varaku undi. "
            "Top option tho compare chesthe risk-adjusted ga konchem weak ga undi."
        )

    reason = snapshot.get("rejection_reason") or "current profile ki strong ga set avvaledu"
    lines = [f"Naanna, {crop_name} ni nenu suggest cheyyaledu reason: {reason}."]
    if top:
        top_name = CROPS[top["crop"]].get("telugu_name", top["crop"])
        lines.append(f"Mee profile ki {top_name} safer ga kanipistondi.")
    lines.append("Meeru danini compare cheyyali ante nenu side-by-side chepthanu.")
    return " ".join(lines)


def _compare_crops_reply(profile: StoredFarmerProfile, crop_slugs: list[str]) -> str | None:
    unique_crops = []
    for crop_slug in crop_slugs:
        if crop_slug not in unique_crops:
            unique_crops.append(crop_slug)
    if not unique_crops:
        return None

    snapshots = [snap for crop in unique_crops if (snap := _build_crop_snapshot(profile, crop))]
    if not snapshots:
        return None

    def compare_key(snapshot: dict[str, Any]) -> tuple[int, int]:
        viability = 1 if snapshot["viable"] and snapshot["profitability"] else 0
        floor = snapshot["profitability"]["net_floor"] if snapshot["profitability"] else -10**12
        return viability, floor

    best = max(snapshots, key=compare_key)
    lines = ["Naanna, mee profile batti direct compare chesthanu."]
    for snapshot in snapshots:
        crop = CROPS[snapshot["crop"]]
        crop_name = crop.get("telugu_name", snapshot["crop"])
        if snapshot["profitability"]:
            lines.append(
                f"{crop_name}: expected {_money(snapshot['profitability']['net_current'])}, "
                f"worst case {_money(snapshot['profitability']['net_floor'])}."
            )
        if snapshot["rejection_reason"]:
            lines.append(f"{crop_name} weak point: {snapshot['rejection_reason']}.")

    best_name = CROPS[best["crop"]].get("telugu_name", best["crop"])
    lines.append(f"Ippudu mee profile ki {best_name} better side lo undi.")
    return " ".join(lines)


def _preference_guided_reply(
    profile: StoredFarmerProfile,
    focus: str,
    mentioned_crop_slugs: list[str],
) -> str:
    _, result = _recommendation_bundle(profile)
    ranked = _rank_for_focus(result, focus)
    if not ranked:
        return (
            f"Naanna, {_describe_focus(focus)} batti shortlist ippudu clear ga dorakaledu. "
            "Specific crop peru cheppandi, nenu compare chesi chepthanu."
        )

    if mentioned_crop_slugs:
        mentioned = _build_crop_snapshot(profile, mentioned_crop_slugs[0])
        if mentioned and mentioned["profitability"]:
            crop_name = CROPS[mentioned["crop"]].get("telugu_name", mentioned["crop"])
            top = ranked[0]
            top_name = CROPS[top["crop"]].get("telugu_name", top["crop"])
            if top["crop"] == mentioned["crop"]:
                return (
                    f"Naanna, {_describe_focus(focus)} angle lo kuda {crop_name} strong ga undi. "
                    f"Expected {_money(mentioned['profitability']['net_current'])}, "
                    f"worst case {_money(mentioned['profitability']['net_floor'])}."
                )
            return (
                f"Naanna, {_describe_focus(focus)} angle lo {crop_name} kanna {top_name} better ga kanipistondi. "
                f"{top_name} lo {_crop_summary_line(top)}"
            )

    top_default = result.get("top_pick")
    top_focus = ranked[0]
    lines = [
        f"Naanna, {_describe_focus(focus)} batti shortlist ivvi.",
    ]
    if top_default and top_focus["crop"] == top_default["crop"]:
        top_name = CROPS[top_focus["crop"]].get("telugu_name", top_focus["crop"])
        lines.append(f"Honest ga cheppali ante ee angle lo kuda {top_name} ne strongest ga undi.")
    for row in ranked[:3]:
        lines.append(_crop_summary_line(row))
    lines.append("Mee mind lo crop peru unte cheppandi, danini ee angle lo direct ga compare chesthanu.")
    return " ".join(lines)


def _alternative_crop_reply(profile: StoredFarmerProfile, normalized_text: str = "") -> str:
    _, result = _recommendation_bundle(profile)
    ranked = result.get("ranked", [])
    top = result.get("top_pick")
    focus = _extract_preference_focus(normalized_text)

    if len(ranked) < 2:
        if top:
            crop_name = CROPS[top["crop"]].get("telugu_name", top["crop"])
            return (
                f"Naanna, mee profile batti {crop_name} okkate ippudu floor-safe option ga kanipistondi. "
                "Vere crop adigithe risk perigedhi lekapothe loss chance ekkuva undi. "
                "Meeru specific ga ye crop gurinchi alochistunnaro cheppandi, nenu compare chesi chepthanu."
            )
        return (
            "Naanna, mee profile ki ippudu strong alternative shortlist clear ga ledu. "
            "Ye crop meeku mind lo undho cheppandi, danini separate ga compare chesi chepthanu."
        )

    alternatives = ranked[1:4]
    if focus:
        alternatives = _sort_rows_for_focus(alternatives, focus)
    lines = [
        "Naanna, sare. Top option ni pakkana petti vere safe crops shortlist chesthanu.",
    ]

    if top:
        top_name = CROPS[top["crop"]].get("telugu_name", top["crop"])
        lines.append(f"Top lo inka {top_name} undi, kani meeru vere option adigaru kabatti alternatives ivvi.")
        if focus:
            lines.append(f"Mee {_describe_focus(focus)} preference batti chusi chepthunna.")
            focus_ranked = _rank_for_focus(result, focus)
            if focus_ranked and focus_ranked[0]["crop"] == top["crop"]:
                lines.append(
                    f"Honest ga cheppali ante mee {_describe_focus(focus)} target ki {top_name} ne inka strongest answer."
                )

    for index, row in enumerate(alternatives, start=1):
        crop = CROPS[row["crop"]]
        lines.append(
            f"{index}. {crop.get('telugu_name', row['crop'])} ({row['crop'].upper()}): "
            f"expected {_money(row['net_current'])}, worst case {_money(row['net_floor'])}."
        )

    if focus and not alternatives:
        lines.append("Top option ni teesesthe mee preference ki vere safe crop ippudu dorakaledu.")
    elif focus and len(alternatives) == 1:
        alt_name = CROPS[alternatives[0]["crop"]].get("telugu_name", alternatives[0]["crop"])
        if top:
            top_name = CROPS[top["crop"]].get("telugu_name", top["crop"])
            lines.append(
                f"Meeru top ni pakkana pedite {alt_name} okkate safe alternative migilindi, kani {top_name} kanna weaker side lo undi."
            )
        else:
            lines.append("Top option ni pakkana pedite ippudu okkate safe alternative migilindi.")

    if focus:
        if top:
            lines.append("Meeru top option accept chesthara, lekapothe ee alternative ni detail ga compare cheyyala?")
        else:
            lines.append("Ee alternative ni detail ga compare cheyyala lekapothe vere crop peru cheppala?")
    else:
        lines.append(
            "Mee target enti cheppandi naanna: takkuva risk aa, takkuva input cost aa, lekapothe quick cash flow aa. "
            "Appudu nenu shortlist ni inka sharp ga narrow chesthanu."
        )
    return " ".join(lines)


def _crop_pressure_reply(profile: StoredFarmerProfile, normalized_text: str) -> str | None:
    crop_slug = _extract_supported_crop(normalized_text, profile)
    farmer, result = _recommendation_bundle(profile)
    top_pick = result.get("top_pick")

    if not crop_slug:
        crowded = _crowded_crops_summary()
        crowded_text = ", ".join(
            f"{CROPS[item['crop']].get('telugu_name', item['crop'])} {item['pct']}%"
            for item in crowded
        )
        return (
            "Naanna, district lo ippudu pressure ekkuva unna crops ivvi: "
            f"{crowded_text}. Mee land ki exact ga chudalante crop peru cheppandi."
        )

    snapshot = _build_crop_snapshot(profile, crop_slug)
    if not snapshot:
        return None

    supply = snapshot["supply"]
    pct = supply.get("projected_pct_filled") or supply.get("pct_filled")
    telugu_crop = CROPS[crop_slug].get("telugu_name", crop_slug)
    lines = [
        f"Naanna, {telugu_crop} ki district pressure ippudu {pct}% safe cap daggara undi."
        if pct is not None
        else f"Naanna, {telugu_crop} ki district pressure check chesanu."
    ]

    profit = snapshot["profitability"]
    if profit:
        lines.append(
            f"Floor price lo mee {profile.acres} acres ki {_money(profit['net_floor'])} safe ga migulutundi."
        )
    if snapshot["rejection_reason"]:
        lines.append(f"Ee profile ki problem: {snapshot['rejection_reason']}.")

    if top_pick and top_pick["crop"] != crop_slug:
        top_snapshot = _build_crop_snapshot(profile, top_pick["crop"])
        if top_snapshot and top_snapshot["profitability"]:
            top_telugu = CROPS[top_pick["crop"]].get("telugu_name", top_pick["crop"])
            lines.append(
                f"{top_telugu} floor lo {_money(top_snapshot['profitability']['net_floor'])} varaku safer ga undi."
            )

    if snapshot["rejection_reason"] or supply.get("status") in {"OVERSUPPLY", "REJECT"}:
        lines.append("Naanu lecture cheyyatledu naanna. Facts cheppanu. Decision meeru cheyyandi.")
    else:
        lines.append("Ee crop possible, kani crowd pressure watch lo undi. Decision meeru cheyyandi.")

    return " ".join(lines)


def _fairness_reply(profile: StoredFarmerProfile, normalized_text: str) -> str | None:
    crops = _extract_multiple_supported_crops(normalized_text)
    if not crops:
        return None

    your_crop = crops[-1]
    other_crop = crops[0] if len(crops) > 1 else None
    your_snapshot = _build_crop_snapshot(profile, your_crop)
    other_snapshot = _build_crop_snapshot(profile, other_crop) if other_crop else None

    lines = ["Naanna, logic hide cheyyanu."]
    if other_snapshot:
        other_pct = other_snapshot["supply"].get("projected_pct_filled") or other_snapshot["supply"].get("pct_filled")
        if other_pct is not None:
            lines.append(
                f"{CROPS[other_crop].get('telugu_name', other_crop)} meeru compare chesthunna crop time ki {other_pct}% cap daggara undi."
            )
    if your_snapshot:
        if your_snapshot["profitability"]:
            lines.append(
                f"Mee profile ki {CROPS[your_crop].get('telugu_name', your_crop)} floor-safe profit {_money(your_snapshot['profitability']['net_floor'])} varaku undi."
            )
        if your_snapshot["rejection_reason"]:
            lines.append(
                f"{CROPS[your_crop].get('telugu_name', your_crop)} kuda reject ayithe reason: {your_snapshot['rejection_reason']}."
            )

    if other_snapshot and other_snapshot["profitability"]:
        lines.append(
            f"Compare chesthe {CROPS[other_crop].get('telugu_name', other_crop)} floor-safe profit {_money(other_snapshot['profitability']['net_floor'])}."
        )

    lines.append("Mee profit-safe logic batti suggestion vachhindi. Naanu guarantee ivvaleddu, kani reason idi.")
    return " ".join(lines)


def _best_market_reply(profile: StoredFarmerProfile, normalized_text: str) -> str | None:
    crop_slug = _extract_supported_crop(normalized_text, profile)
    if not crop_slug:
        return None

    options = _best_market_options(profile, crop_slug)
    if not options:
        return (
            "Mee mandal nundi reachable mandi net price ippudu calculate cheyyalekapoyanu naanna. "
            "Konchem tarvatha malli adugandi."
        )

    top = options[0]
    lines = [
        f"Naanna, {CROPS[crop_slug].get('telugu_name', crop_slug)} ki reachable mandis net price chusanu.",
    ]
    for option in options[:3]:
        lines.append(
            f"{option['mandi_name']}: modal {_money(option['modal_price'])}/qtl, "
            f"transport approx {_money(option['transport_total'])} total, "
            f"net {_money(option['net_per_qtl'])}/qtl."
        )
    lines.append(
        f"Best reachable mandi ippatiki {top['mandi_name']}. Raw rate kaadu naanna - transport mariyu 2% commission teesesi net cheppanu."
    )
    return " ".join(lines)


def _trader_offer_reply(profile: StoredFarmerProfile, normalized_text: str) -> str | None:
    crop_slug = _extract_supported_crop(normalized_text, profile)
    offer = _extract_price_offer(normalized_text)
    if not crop_slug or offer is None:
        return None

    options = _best_market_options(profile, crop_slug)
    if not options:
        return None

    top = options[0]
    diff = top["net_per_qtl"] - offer
    if diff <= 0:
        return (
            f"Naanna, trader offer {_money(offer)}/qtl already mandi net kanna thakkuva kaadu. "
            f"Best reachable mandi net {_money(top['net_per_qtl'])}/qtl. Immediate cash avasaram unte consider cheyyavachu."
        )

    return (
        f"Naanna, trader offer {_money(offer)}/qtl. "
        f"Best reachable mandi {top['mandi_name']} net {_money(top['net_per_qtl'])}/qtl. "
        f"Difference {_money(diff)}/qtl loss. Immediate avasaram lekapothe trader ki ivvakunda mandi option chudandi."
    )


def _high_interest_reply(profile: StoredFarmerProfile, normalized_text: str) -> str:
    monthly_pct = _extract_interest_monthly_pct(normalized_text) or 0
    annual_pct = round(monthly_pct * 12, 1)
    waiver_cap = min(profile.loan_burden_rs or 0, 200000)
    lines = [
        f"Naanna, {monthly_pct}% per month ante approx {annual_pct}% annual.",
        f"{LEGAL_PRIVATE_INTEREST_REDLINE_ANNUAL}% annual kanna ekkuva aithe chala risky private debt ani treat cheyyali.",
    ]
    if waiver_cap > 0:
        lines.append(f"Mee current loan lo waiver side nundi {_money(waiver_cap)} varaku check cheyyadam immediate.")
    lines.append("KCC side nundi 7% annual bank credit chala better.")
    lines.append("Aadhaar, passbook, land docs tho Mandal Agriculture Office ki vellandi.")
    return " ".join(lines)


def _debt_deadline_reply(profile: StoredFarmerProfile, normalized_text: str) -> str:
    days = _extract_days_count(normalized_text)
    bandhu_amount = int(round((profile.acres or 0) * 5000))
    waiver_cap = min(profile.loan_burden_rs or 0, 200000)

    lines = ["Naanna, mundu oka saari breathe teesukondi. Options kalisi chuddam."]
    if days:
        lines.append(f"Deadline inka {days} rojulu unnattu artham ayindi.")
    if bandhu_amount > 0:
        lines.append(f"Rythu Bandhu season-side approx {_money(bandhu_amount)} support untundi.")
    lines.append("PM-KISAN instalment side nundi ₹2,000/yearly cycle lo check cheyyandi.")
    if waiver_cap > 0:
        lines.append(f"Crop loan waiver side nundi {_money(waiver_cap)} varaku eligibility check cheyyandi.")
    lines.append("Immediate ga bank branch lo restructure lekapothe extension request pettandi.")
    return " ".join(lines)


def _personalized_scheme_reply(profile: StoredFarmerProfile) -> str:
    bandhu_amount = int(round((profile.acres or 0) * 5000))
    waiver_cap = min(profile.loan_burden_rs or 0, 200000)
    lines = ["Naanna, mee profile batti useful schemes short ga chepthanu."]
    if bandhu_amount > 0:
        lines.append(
            f"{SCHEMES['rythu_bandhu']['telugu_name']}: season ki {_money(bandhu_amount)} approx "
            f"({SCHEMES['rythu_bandhu']['payment_months'][0]}, {SCHEMES['rythu_bandhu']['payment_months'][1]})."
        )
    if waiver_cap > 0:
        lines.append(
            f"{SCHEMES['crop_loan_waiver_2024']['telugu_name']}: up to {_money(waiver_cap)} check cheyyandi."
        )
    lines.append(f"{SCHEMES['pm_kisan']['telugu_name']}: ₹2,000 instalment x 3 every year.")
    lines.append(f"{SCHEMES['kisan_credit_card']['telugu_name']}: {SCHEMES['kisan_credit_card']['interest_rate']}.")
    return " ".join(lines)


def _idle_land_reply(profile: StoredFarmerProfile) -> str:
    candidates = []
    for crop_slug in ("green_gram", "black_gram", "sesame"):
        if crop_slug in filter_soil([crop_slug], profile.soil_type, profile.mandal):
            candidates.append(crop_slug)

    chosen = candidates[0] if candidates else "green_gram"
    crop = CROPS[chosen]
    return (
        f"Naanna, two seasons madhya idle land unte {crop.get('telugu_name', chosen)} chudandi. "
        f"Idi short cycle crop - approx {crop.get('grow_duration_days', 60)} rojulu. "
        f"Input cost around {_money(crop.get('input_cost_per_acre', 0))}/acre. "
        "Soil cover untundi, konchem cash flow kuda vasthundi."
    )


def _input_cost_reply(profile: StoredFarmerProfile) -> str:
    farmer, result = _recommendation_bundle(profile)
    low_cost = sorted(
        (
            {
                "crop": row["crop"],
                "cost_per_acre": CROPS[row["crop"]].get("input_cost_per_acre", 0),
                "net_floor": row["net_floor"],
            }
            for row in result["ranked"]
        ),
        key=lambda item: item["cost_per_acre"],
    )
    if not low_cost:
        return "Input cost pressure unna time lo safe alternatives ippudu identify cheyyalekapoyanu naanna."

    lines = ["Naanna, input cost perigite low-cost safe options ki shift chudali."]
    top = result.get("top_pick")
    if top and low_cost and low_cost[0]["crop"] == top["crop"]:
        top_name = CROPS[top["crop"]].get("telugu_name", top["crop"])
        lines.append(
            f"Truth ga cheppali ante mee shortlist lo {top_name} already lowest input cost side lo strongest option."
        )
    for option in low_cost[:3]:
        lines.append(
            f"{CROPS[option['crop']].get('telugu_name', option['crop'])}: "
            f"input approx {_money(option['cost_per_acre'])}/acre, "
            f"floor-safe profit {_money(option['net_floor'])}."
        )
    if top and len(low_cost) > 1 and low_cost[0]["crop"] == top["crop"]:
        next_option = low_cost[1]
        next_name = CROPS[next_option["crop"]].get("telugu_name", next_option["crop"])
        lines.append(
            f"Vere crop insist chesthe next practical option {next_name}, kani input cost ekkuva / floor profit takkuva undi."
        )
    return " ".join(lines)


def _delayed_monsoon_reply(profile: StoredFarmerProfile) -> str:
    weather = get_weather_forecast(profile.mandal)
    next_rain = weather.get("next_7_day_rain_mm")
    farmer, result = _recommendation_bundle(profile)
    top = result.get("top_pick")
    alt = result.get("second_pick")

    lines = ["Naanna, varsham late ayithe paddy laanti high-water crop ni rush cheyyakandi."]
    if next_rain is not None:
        lines.append(f"Next 7 rojulu approx {next_rain} mm rain forecast undi.")
    if top:
        lines.append(f"Delay continue aithe {CROPS[top['crop']].get('telugu_name', top['crop'])} safer option.")
    if alt:
        lines.append(f"Second side {CROPS[alt['crop']].get('telugu_name', alt['crop'])} kuda chudavachu.")
    lines.append("2-3 rojula gap lo malli weather check chesi final decision theesukondi.")
    return " ".join(lines)


def _drought_reply(profile: StoredFarmerProfile) -> str:
    weather = get_weather_forecast(profile.mandal)
    next_rain = weather.get("next_7_day_rain_mm")
    farmer, result = _recommendation_bundle(profile)
    dry_options = [
        row for row in result["ranked"]
        if CROPS[row["crop"]].get("water_requirement") in {"low", "medium"}
    ]

    lines = ["Naanna, water stress unna time lo high-water crops avoid cheyyali."]
    if next_rain is not None:
        lines.append(f"Next 7 rojula rain approx {next_rain} mm matrame kanipisthundi.")
    if dry_options:
        shortlist = ", ".join(CROPS[item["crop"]].get("telugu_name", item["crop"]) for item in dry_options[:3])
        lines.append(f"Mee profile ki lower-water shortlist: {shortlist}.")
    lines.append("Already crop standing unte early-morning irrigation, weed control, moisture save cheyyandi.")
    return " ".join(lines)


def _season_feedback_reply() -> str:
    return (
        "Bagundi naanna. Season close ayithe 3 vishayalu cheppandi: "
        "1) final crop enti, 2) yield entha vachhindi, 3) final selling rate / biggest problem enti. "
        "Next season logic improve cheyyataaniki idi chala useful."
    )


def _intercrop_reply(profile: StoredFarmerProfile) -> str:
    if profile.soil_type in {"red_clayey", "mixed"}:
        pair = "maize + red gram"
    else:
        pair = "soybean + red gram"
    return (
        f"Naanna, mee land ki one simple intercropping pair {pair}. "
        "Main crop cash flow kosam, companion crop risk spread kosam. "
        "Ippudu full intercropping engine score ledu, kani risk spread kosam idi practical pair."
    )


def _referral_reply() -> str:
    return (
        "Bagundi naanna. Mee friend lekapothe pakkinti farmer direct ga ee WhatsApp number ki message cheyyamani cheppandi. "
        "Nenu 3-4 messages lo mandal, acres, soil, water collect chesi separate ga guidance istanu."
    )


def _text_symptom_reply(profile: StoredFarmerProfile, normalized_text: str) -> str | None:
    crop_slug = _extract_supported_crop(normalized_text, profile)
    if not crop_slug:
        crop_slug = next((crop for crop in profile.last_three_crops if crop in CROPS), None)
    if not crop_slug:
        return None

    diseases = CROPS[crop_slug].get("common_diseases", {})
    if not diseases:
        return None

    disease_key = None
    if crop_slug == "maize" and any(word in normalized_text for word in ("hole", "worm", "whorl", "ragged")):
        disease_key = "fall_army_worm"
    elif crop_slug == "paddy" and any(word in normalized_text for word in ("diamond", "spot", "machha", "leaf edge")):
        disease_key = "blast"
    elif crop_slug == "turmeric" and any(word in normalized_text for word in ("rot", "yellow", "collapse", "kullu")):
        disease_key = "rhizome_rot"

    if not disease_key or disease_key not in diseases:
        return (
            f"Naanna, photo lekunda exact ga guess cheyyatam tappu. "
            f"Symptoms batti sure ga cheppalenu. Daylight photo pampandi lekapothe KVK {KVK_PHONE} ki call cheyyandi."
        )

    disease = diseases[disease_key]
    return (
        f"Naanna, photo lekunda exact ga cheppalenu. Kani mee description batti idi {disease.get('telugu', disease_key)} la undi. "
        f"Treatment: {disease.get('treatment')}. Approx cost {_money(disease.get('cost_per_acre', 0))}/acre. "
        f"Confidence takkuva kabatti confirm kavali ante photo pampandi lekapothe KVK {KVK_PHONE}."
    )


def _daily_weather_preview_reply() -> str:
    try:
        summary = WeatherPipeline().run(persist=False)
    except Exception:
        return "Daily weather alert ippudu fetch cheyyalekapoyanu naanna. Konchem tarvatha malli try cheddam."

    daily_rows = summary.get("daily_rows_prepared", 0)
    location = summary.get("location", {}).get("name", "Nizamabad")
    return (
        f"{location} morning weather snapshot ready undi naanna. "
        f"Next {daily_rows} rojula daily forecast mariyu hourly rain checks available unnayi."
    )


def _season_calendar_reply(profile: StoredFarmerProfile, normalized_text: str) -> str:
    state = CROP_CYCLE_SERVICE.get_state(profile.phone_number)
    sowing_date = _extract_embedded_date(normalized_text)
    crop_slug = _extract_supported_crop(normalized_text, profile) or state.crop_name

    if not crop_slug and (sowing_date or "calendar" in normalized_text or "schedule" in normalized_text):
        _, result = _recommendation_bundle(profile)
        top = result.get("top_pick")
        if top:
            crop_slug = top["crop"]

    if sowing_date and crop_slug:
        payload = CROP_CYCLE_SERVICE.set_sowing(
            profile.phone_number,
            crop_name=crop_slug,
            sowing_date=sowing_date,
        )
        events = payload["calendar"]["events"][:5]
        lines = [
            f"Naanna, {CROPS[crop_slug].get('telugu_name', crop_slug)} season calendar set chesanu.",
            f"Sowing date: {payload['calendar']['sowing_date']}.",
            "Next important windows:",
        ]
        for event in events[1:4]:
            lines.append(f"- Day {event['day_from_sowing']}: {event['title']} ({event['date']})")
        lines.append("Ippati nunchi crop-stage reminders ki idi base avutundi.")
        return "\n".join(lines)

    calendar_payload = CROP_CYCLE_SERVICE.get_calendar(profile.phone_number)
    if calendar_payload:
        events = calendar_payload["events"][:5]
        lines = [
            f"Naanna, current season calendar {CROPS[calendar_payload['crop']].get('telugu_name', calendar_payload['crop'])} kosam ready undi.",
            f"Sowing date: {calendar_payload['sowing_date']}.",
        ]
        for event in events[1:4]:
            lines.append(f"- Day {event['day_from_sowing']}: {event['title']} ({event['date']})")
        lines.append(
            f"Harvest window: {calendar_payload['harvest_window']['start_date']} nunchi "
            f"{calendar_payload['harvest_window']['end_date']} varaku."
        )
        return "\n".join(lines)

    return (
        "Season calendar start cheyyalante crop peru mariyu sowing date pampandi naanna. "
        "Udaharanaki: maize sowing date 2026-06-20."
    )


def _proactive_disease_reply(profile: StoredFarmerProfile) -> str:
    preview = CROP_CYCLE_SERVICE.preview_alerts(profile.phone_number)
    crop_name = preview["state"].get("crop_name")
    sowing_date = preview["state"].get("sowing_date")
    if not crop_name or not sowing_date:
        return (
            "Proactive disease alert start cheyyalante mundu crop mariyu sowing date set cheyyali naanna. "
            "Udaharanaki: paddy sowing date 2026-06-20."
        )

    proactive = preview["proactive_alerts"]
    if not proactive:
        return (
            "Ippudu major disease pressure signal kanapadatam ledu naanna. "
            "Kani season calendar prakaram next monitoring window miss avvakandi."
        )

    lines = ["Naanna, current proactive alerts ivvi:"]
    for alert in proactive[:3]:
        lines.append(f"- {alert['title']}: {alert['message']}")
    return "\n".join(lines)


def _drying_alert_reply(profile: StoredFarmerProfile, normalized_text: str) -> str:
    state = CROP_CYCLE_SERVICE.get_state(profile.phone_number)
    if "start" in normalized_text or "today" in normalized_text or "drying" in normalized_text:
        if "drying" in normalized_text and ("start" in normalized_text or "today" in normalized_text):
            crop_slug = _extract_supported_crop(normalized_text, profile) or state.crop_name
            CROP_CYCLE_SERVICE.set_drying_start(
                profile.phone_number,
                drying_start=_extract_embedded_date(normalized_text) or "today",
                crop_name=crop_slug,
            )
            state = CROP_CYCLE_SERVICE.get_state(profile.phone_number)

    if not state.drying_start:
        return (
            "Drying alert kosam start date cheppandi naanna. "
            "Udaharanaki: start drying today lekapothe paddy drying 2026-10-22."
        )

    preview = CROP_CYCLE_SERVICE.preview_alerts(profile.phone_number)
    drying_alerts = preview["drying_alerts"]
    lines = [f"Naanna, drying watch active undi. Start date: {state.drying_start}."]
    for alert in drying_alerts[:3]:
        lines.append(f"- {alert['title']}: {alert['message']}")
    return "\n".join(lines)


def _long_cycle_outlook_reply(profile: StoredFarmerProfile, normalized_text: str) -> str:
    crop_slug = _extract_supported_crop(normalized_text, profile)
    if not crop_slug and "dragon" in normalized_text:
        crop_slug = "dragon_fruit"
    if not crop_slug:
        return (
            "Long-cycle outlook kosam crop peru cheppandi naanna. "
            "Udaharanaki: dragon fruit lekapothe turmeric."
        )

    outlook = LONG_CYCLE_OUTLOOK_SERVICE.build_outlook(crop_slug, horizon_months=6)
    return render_long_cycle_reply(outlook)


def _canal_release_reply(profile: StoredFarmerProfile, normalized_text: str) -> str:
    match = re.search(r"last water\s+(\d{1,2})\s+days?\s+ago", normalized_text)
    if match:
        days = int(match.group(1))
        date_value = (date.today() - timedelta(days=days)).isoformat()
        CROP_CYCLE_SERVICE.set_last_water(profile.phone_number, last_water_date=date_value)

    alerts = CANAL_ALERT_SERVICE.evaluate_farmer_alerts(
        profile.phone_number,
        profile.mandal,
    )
    if not alerts:
        return (
            "Ippudu mee mandal ki active canal release feed kanapadatam ledu naanna. "
            "Feed vachesina ventane hours mundu alert istanu."
        )

    return alerts[0]["message"]


def _specialty_monitoring_reply(profile: StoredFarmerProfile, normalized_text: str) -> str:
    crop_slug = "dragon_fruit" if "dragon" in normalized_text else _extract_supported_crop(normalized_text, profile)
    if crop_slug != "dragon_fruit":
        return None

    sowing_date = _extract_embedded_date(normalized_text) or "today"
    payload = CROP_CYCLE_SERVICE.set_sowing(
        profile.phone_number,
        crop_name="dragon_fruit",
        sowing_date=sowing_date,
    )
    events = payload["calendar"]["events"]
    first_event = next((event for event in events if event["type"] == "monitoring"), events[1])

    lines = [
        "Naanna, mee dragon fruit 6-month season calendar ready.",
        "Month 1-2: monthly photo - root establishment check.",
        "Month 3-4: every 2 weeks - cladode growth rate.",
        "Month 5: flowering prediction starts - temperature + humidity monitoring.",
        "Month 6: harvest timing + buyer activation.",
        f"First reminder: {first_event['date']}. Buyer search: already starting.",
    ]
    return " ".join(lines)


def _crop_failure_reply(profile: StoredFarmerProfile) -> str:
    return (
        "Naanna, idi vini baadha ga undi. Mundu field photos, damaged area, mariyu date note cheskondi. "
        "Mandal Agriculture Office ki immediate ga chupinchandi. Loan pressure unte waiver mariyu restructure side kuda parallel ga chuddam. "
        f"Urgent agronomy support kosam KVK {KVK_PHONE}."
    )


def _bot_wrong_reply(profile: StoredFarmerProfile) -> str:
    return (
        "Naanna, outcome baga raakapothe nenu straight ga own chesthanu. "
        "Recommendation time lo unna data versus actual market ni side-by-side malli chusi next step decide cheddam. "
        "Immediate ga mee actual yield mariyu final selling rate cheppandi. Loss reduce cheyyadaniki remaining options chuddam."
    )


def _crisis_reply() -> str:
    return (
        "Naanna, mee safety ippudu mukhyam. Dayachesi okkarega undakandi - ippude mee intlo okaru lekapothe pakkinti vallani pilandi. "
        "India Tele-MANAS 24x7 mental health helpline 14416 lekapothe 1800-89-14416 ki ippude call cheyyandi. "
        "Immediate danger lo unte nearest hospital ki lekapothe emergency help ki ippude vellandi."
    )


def _sell_land_reply(profile: StoredFarmerProfile) -> str:
    waiver_cap = min(profile.loan_burden_rs or 0, 200000)
    return (
        "Naanna, pressure lo bhoomi ammadam final step ga pettaam - ippude aa decision teesukokandi. "
        f"Mee current loan ki waiver side {_money(waiver_cap)} varaku, KCC side 7% annual option, mariyu restructure path mundu chuddam. "
        "Bhoomi అమ్మే mundu options anni close ayyaka matrame alochiddam."
    )


def _labour_shortage_reply(profile: StoredFarmerProfile) -> str:
    current_crop = next((crop for crop in profile.last_three_crops if crop in CROPS), None)
    crop_name = CROPS[current_crop].get("telugu_name", current_crop) if current_crop else "mee crop"
    return (
        f"Naanna, {crop_name} harvest labour dorakakapothe first maturity unna area ni split ga harvest cheyyandi. "
        "Village combine/harvester option unda check cheyyandi, lekapothe pakkinti farmers tho 2-day exchange labour set cheskondi. "
        "Late ayithe field loss perigedi kabatti full field okesari kakunda priority blocks lo mundu start cheyyandi."
    )


def _seed_variety_reply(profile: StoredFarmerProfile) -> str:
    farmer, result = _recommendation_bundle(profile)
    top = result.get("top_pick")
    crop_slug = top["crop"] if top else None
    crop_name = CROPS[crop_slug].get("telugu_name", crop_slug) if crop_slug else "mee crop"
    water = profile.water_source or "local water"
    return (
        f"Naanna, {crop_name} kosam certified seed packet matrame theeskondi - local bill, batch number, mariyu sealed bag compulsory. "
        f"Mee {water} situation batti short-duration lekapothe stress-tolerant variety adugandi. "
        "Exact company peru cheppemundu dealer packet photo pampithe nenu cross-check chesthanu."
    )


def _counterfeit_seed_reply() -> str:
    return (
        "Naanna, wrong lekapothe counterfeit seed anipisthe packet, bill, batch number, mariyu field photos immediate ga preserve cheyyandi. "
        "Dealer daggara written complaint ivvandi. Mandal Agriculture Office ki same evidence tho complaint pettandi. "
        "Open bag ni padeseyyakandi - adhe proof."
    )


def _pesticide_upsell_reply(profile: StoredFarmerProfile) -> str:
    return (
        "Naanna, symptom clear ga lekapothe extra chemical konakandi. "
        "Shop cheppindani blind ga konadam kanna symptom lekapothe photo pampandi lekapothe text lo cheppandi. "
        "Nenu exact quantity unna treatment matrame chepthanu - unnecessary spray avoid cheyyali."
    )


def _buyer_not_found_reply(profile: StoredFarmerProfile) -> str:
    current_crop = next((crop for crop in profile.last_three_crops if crop in CROPS), None)
    crop_name = CROPS[current_crop].get("telugu_name", current_crop) if current_crop else "mee crop"
    return (
        f"Naanna, {crop_name} harvest deggera buyer lekapothe ippude parallel ga 3 paths start cheyyali: "
        "local FPO enquiry, e-NAM lot listing, mariyu storage option. "
        "Immediate distress sale ki vellakunda 2-3 buyer paths open petti negotiate cheyyandi."
    )


def _is_market_sale_question(normalized_text: str) -> bool:
    return any(
        phrase in normalized_text
        for phrase in ("ekkada ammal", "where sell", "best price", "ammali", "sell where", "mandi")
    )


def _is_trader_offer_question(normalized_text: str) -> bool:
    return any(word in normalized_text for word in ("trader", "offer", "istunnadu", "istunnaru", "teesukovala"))


def _is_fairness_question(normalized_text: str) -> bool:
    return any(word in normalized_text for word in ("fair", "unfair", "vaadiki", "vallaki", "naaku")) and len(_extract_multiple_supported_crops(normalized_text)) >= 1


def _has_high_interest_pattern(normalized_text: str) -> bool:
    return _extract_interest_monthly_pct(normalized_text) is not None


def _is_deadline_panic(normalized_text: str) -> bool:
    panic_markers = ("deadline", "repayment", "cheyyalekapotunnanu", "panic", "15 days", "rojulu")
    debt_context = ("loan", "appu", "debt", "repay", "repayment")
    return any(word in normalized_text for word in panic_markers) and any(word in normalized_text for word in debt_context)


def _is_scheme_question(normalized_text: str) -> bool:
    return any(word in normalized_text for word in ("scheme", "bandhu", "pm kisan", "bima", "kcc", "waiver"))


def _is_crop_pressure_question(normalized_text: str) -> bool:
    return any(word in normalized_text for word in ("andaru", "everyone", "pressure", "cap", "naanu kuda", "nenu kuda"))


def _is_alternative_crop_question(normalized_text: str) -> bool:
    phrases = (
        "vere crop",
        "inka vere crop",
        "maro crop",
        "maroka crop",
        "different crop",
        "another crop",
        "other crop",
        "alternative crop",
        "alternative option",
        "other option",
        "second option",
        "inkemaina crop",
        "inka emaina crop",
        "suggest different",
    )
    return any(phrase in normalized_text for phrase in phrases)


def _is_idle_land_question(normalized_text: str) -> bool:
    return any(
        phrase in normalized_text
        for phrase in ("idle land", "kaliga undi", "empty land", "between kharif", "between season")
    )


def _is_input_cost_question(normalized_text: str) -> bool:
    return any(
        phrase in normalized_text
        for phrase in (
            "input cost",
            "fertilizer cost",
            "chemical cost",
            "cost perig",
            "rate perig",
            "cost ekkuva",
            "ekkuva cost",
            "investment ekkuva",
        )
    )


def _is_delayed_monsoon_question(normalized_text: str) -> bool:
    return any(
        phrase in normalized_text
        for phrase in ("monsoon delay", "varsham late", "rain late", "sowing delay", "late ga undi")
    )


def _is_drought_question(normalized_text: str) -> bool:
    return any(
        phrase in normalized_text
        for phrase in ("drought", "water stress", "neellu levu", "varsham ledu", "soil dry")
    )


def _is_feedback_question(normalized_text: str) -> bool:
    return any(
        phrase in normalized_text
        for phrase in ("harvest ayindi", "season ayipoyindi", "feedback", "complete ayindi")
    )


def _is_intercrop_question(normalized_text: str) -> bool:
    return any(
        phrase in normalized_text
        for phrase in ("intercrop", "intercropping", "mix crop", "rendu crops")
    )


def _is_referral_question(normalized_text: str) -> bool:
    return any(
        phrase in normalized_text
        for phrase in ("friend", "another farmer", "neighbor", "pakkinti", "refer")
    )


def _is_text_symptom_question(normalized_text: str) -> bool:
    return any(
        phrase in normalized_text
        for phrase in ("yellow", "spot", "machha", "worm", "hole", "rot", "symptom")
    )


def _is_weather_alert_question(normalized_text: str) -> bool:
    return any(
        phrase in normalized_text
        for phrase in ("morning weather", "daily weather", "today weather", "weather alert")
    )


def _is_long_cycle_outlook_question(normalized_text: str) -> bool:
    return any(
        phrase in normalized_text
        for phrase in ("dragon fruit", "future price", "6 month", "6-month", "long cycle", "future lo dhara")
    )


def _is_canal_release_question(normalized_text: str) -> bool:
    return any(
        phrase in normalized_text
        for phrase in ("canal water release", "srsp", "rotation schedule", "last water", "canal alert")
    )


def _is_specialty_monitoring_question(normalized_text: str) -> bool:
    return any(
        phrase in normalized_text
        for phrase in ("dragon fruit plant", "dragon fruit plant chesanu", "special crop", "high value crop")
    )


def _is_calendar_question(normalized_text: str) -> bool:
    return any(
        phrase in normalized_text
        for phrase in ("season calendar", "calendar", "schedule", "sowing date", "reminder")
    )


def _is_proactive_disease_question(normalized_text: str) -> bool:
    return any(
        phrase in normalized_text
        for phrase in ("disease alert", "proactive", "blast risk", "rhizome rot risk", "monitoring reminder")
    )


def _is_drying_question(normalized_text: str) -> bool:
    return any(
        phrase in normalized_text
        for phrase in ("drying", "endabett", "endabedutunna", "cover now", "harvest drying")
    )


def _extract_embedded_date(normalized_text: str) -> str | None:
    patterns = [
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b\d{4}/\d{2}/\d{2}\b",
        r"\b\d{4}\s+\d{1,2}\s+\d{1,2}\b",
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b",
        r"\b(?:today|yesterday|tomorrow)\b",
        r"\b\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}\b",
        r"\b\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b",
        r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}(?:\s+\d{4})?\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized_text)
        if not match:
            continue
        candidate = match.group(0)
        if re.fullmatch(r"\d{4}\s+\d{1,2}\s+\d{1,2}", candidate):
            candidate = "-".join(candidate.split())
        if parse_farming_date(candidate):
            return candidate
    return None


def _is_crop_failure_question(normalized_text: str) -> bool:
    return any(
        phrase in normalized_text
        for phrase in ("crop failed", "poindi", "nashtam", "loss ayindi", "damage ayindi")
    )


def _is_bot_wrong_question(normalized_text: str) -> bool:
    return any(
        phrase in normalized_text
        for phrase in ("meeru cheppindi follow", "wrong recommendation", "meevalla loss", "meeru chepparu")
    )


def _is_crisis_question(normalized_text: str) -> bool:
    return any(
        phrase in normalized_text
        for phrase in ("sachipovali", "chachipothanu", "suicide", "jeevitham ayipoyindi", "i cannot live", "end chesukunta")
    )


def _is_sell_land_question(normalized_text: str) -> bool:
    return any(
        phrase in normalized_text
        for phrase in ("sell land", "bhoomi ammatha", "bhoomi ammey", "land ammes")
    )


def _is_labour_shortage_question(normalized_text: str) -> bool:
    return any(
        phrase in normalized_text
        for phrase in ("labour dorakadamledu", "labor dorakadamledu", "workers leru", "harvest labour")
    )


def _is_seed_variety_question(normalized_text: str) -> bool:
    return any(
        phrase in normalized_text
        for phrase in ("seed variety", "which seed", "ye seed", "ఏ seed", "hybrid seed")
    )


def _is_counterfeit_seed_question(normalized_text: str) -> bool:
    return any(
        phrase in normalized_text
        for phrase in ("fake seed", "counterfeit seed", "wrong seed", "nakili seed")
    )


def _is_pesticide_upsell_question(normalized_text: str) -> bool:
    return any(
        phrase in normalized_text
        for phrase in ("shop", "chemical", "extra spray", "pesticide", "mandhu")
    ) and any(
        phrase in normalized_text
        for phrase in ("recommend", "cheppadu", "konamani", "buy", "spray")
    )


def _is_buyer_not_found_question(normalized_text: str) -> bool:
    return any(
        phrase in normalized_text
        for phrase in ("buyer ledu", "buyer vasthada", "harvest ki vastundi", "buyer dorakaledu")
    )
