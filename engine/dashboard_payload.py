"""Shared payload builders for the interactive dashboard."""

from __future__ import annotations

from typing import Any

from data.nizamabad_district import CROPS
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


def slug_to_label(slug: str) -> str:
    return slug.replace("_", " ").title()


def crop_meta(crop_slug: str) -> dict[str, Any]:
    crop = CROPS[crop_slug]
    return {
        "slug": crop_slug,
        "name": slug_to_label(crop_slug),
        "teluguName": crop.get("telugu_name", crop_slug),
        "season": crop.get("season", []),
        "active": crop.get("active_for_recommendation", True),
    }


def build_filter_trace(farmer: FarmerProfile) -> list[dict[str, Any]]:
    season_name = get_current_season_name()
    weather = get_weather_forecast(farmer.mandal)
    candidates = [
        crop_name
        for crop_name, crop_data in CROPS.items()
        if crop_data.get("active_for_recommendation", True)
    ]
    after_season = filter_season(candidates, season_name)
    after_soil = filter_soil(after_season, farmer.soil_zone, farmer.mandal)
    after_water = filter_water_weather(after_soil, farmer.water_source, weather)
    after_supply, supply_info = filter_supply_cap(after_water, farmer.mandal, farmer.acres)
    price_preds = add_price_prediction(after_supply, farmer.water_source)
    ranked = filter_profitability(
        after_supply,
        farmer.acres,
        farmer.water_source,
        farmer.loan_burden,
        price_preds,
    )

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
            "note": f"Water source is {slug_to_label(farmer.water_source)}. Rainfall, drought, and flood risk are checked here.",
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
            "highlights": [crop_meta(item["crop"])["name"] for item in ranked[:4]],
        },
    ]


def _format_ranked_row(row: dict[str, Any], supply_info: dict[str, Any]) -> dict[str, Any]:
    return {
        **crop_meta(row["crop"]),
        "expectedProfit": row["net_current"],
        "worstProfit": row["net_floor"],
        "inputCostTotal": row["input_cost_total"],
        "avgYieldQtlPerAcre": row["avg_yield"],
        "priceCurrent": row["price_current"],
        "priceFloor": row["price_floor"],
        "priceCeiling": row["price_ceiling"],
        "competitionStatus": supply_info.get("status"),
        "competitionPctFilled": supply_info.get("projected_pct_filled", supply_info.get("pct_filled")),
    }


def build_dashboard_analysis(farmer: FarmerProfile) -> dict[str, Any]:
    result = recommend(farmer)
    supply_info = result.get("supply_info", {})
    ranked = [
        _format_ranked_row(row, supply_info.get(row["crop"], {}))
        for row in result.get("ranked", [])
    ]
    top_pick = ranked[0] if ranked else None
    second_pick = ranked[1] if len(ranked) > 1 else None
    weather = result.get("weather", {})

    return {
        "profile": {
            "mandal": farmer.mandal,
            "mandalLabel": slug_to_label(farmer.mandal),
            "acres": farmer.acres,
            "soilZone": farmer.soil_zone,
            "soilLabel": slug_to_label(farmer.soil_zone),
            "waterSource": farmer.water_source,
            "waterLabel": slug_to_label(farmer.water_source),
            "loanBurdenRs": farmer.loan_burden,
            "lastCrops": farmer.last_crops,
            "lastCropLabels": [slug_to_label(crop) for crop in farmer.last_crops],
        },
        "topPick": top_pick,
        "secondPick": second_pick,
        "ranked": ranked,
        "rejected": [
            {
                "crop": item["crop"],
                "name": slug_to_label(item["crop"]),
                "teluguName": CROPS.get(item["crop"], {}).get("telugu_name", item["crop"]),
                "reason": item["reason"],
            }
            for item in result.get("rejected", [])
        ],
        "filterTrace": build_filter_trace(farmer),
        "teluguReply": generate_telugu_response(result),
        "weather": {
            "expectedRainfallMm": weather.get("expected_rainfall_mm"),
            "next7DayRainMm": weather.get("next_7_day_rain_mm"),
            "tempMaxAvgC": weather.get("temp_max_avg_c"),
            "tempMinAvgC": weather.get("temp_min_avg_c"),
            "droughtRisk": weather.get("drought_risk"),
            "floodRisk": weather.get("flood_risk"),
            "source": weather.get("source", "crop_engine"),
        },
    }
