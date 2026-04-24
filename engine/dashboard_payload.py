"""Shared live payload builders for the public website and decision studio."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from statistics import median
from typing import Any

from data.nizamabad_district import (
    BOT_RECOMMENDED_ACRES,
    CROPS,
    CURRENT_SEASON,
    DISTRICT_PLANTED_ACRES,
    MANDALS,
    MANDIS,
)
from data.seed_catalog import SEED_VARIETY_CATALOG
from engine.cap_logic import STATUS_LABELS, derive_pressure_status, get_effective_safe_cap
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
from engine.price_pipeline import DATA_GOV_RESOURCE_ID, LOCAL_PRICE_CACHE_PATH, PricePipeline
from engine.weather_pipeline import LOCAL_DAILY_CACHE_PATH, WeatherPipeline


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


def _read_json_rows(path: str) -> list[dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return payload if isinstance(payload, list) else []


def _latest_timestamp(rows: list[dict[str, Any]], key: str = "fetched_at_utc") -> str | None:
    values = [str(row.get(key)) for row in rows if row.get(key)]
    return max(values) if values else None


def load_current_price_rows(prefer_live: bool = True) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return current mandi rows plus source metadata for bot/website use."""

    pipeline = PricePipeline()
    notes: list[str] = []

    if prefer_live:
        live_rows, notes = pipeline.fetch_live_rows()
        if live_rows:
            expected_pairs = pipeline._expected_pairs()
            live_pairs = {(row["mandi_slug"], row["crop_slug"]) for row in live_rows}
            missing_pairs = expected_pairs - live_pairs
            fallback_rows = pipeline.build_fallback_rows(missing_pairs=missing_pairs)
            rows = live_rows + fallback_rows
            return rows, {
                "mode": "live_with_fallback_fill" if fallback_rows else "live",
                "sourceLabel": (
                    "Current crop prices come from the Government of India mandi dataset on "
                    "data.gov.in, generated through the AGMARKNET portal."
                ),
                "resourceId": DATA_GOV_RESOURCE_ID,
                "priceFreshnessUtc": _latest_timestamp(rows),
                "liveRowCount": len(live_rows),
                "fallbackRowCount": len(fallback_rows),
                "notes": notes,
            }

    cached_rows = _read_json_rows(LOCAL_PRICE_CACHE_PATH)
    if cached_rows:
        live_count = sum(1 for row in cached_rows if row.get("source") == "data_gov_in")
        fallback_count = len(cached_rows) - live_count
        return cached_rows, {
            "mode": "cached",
            "sourceLabel": (
                "Cached mandi board from the latest backend sync. Some rows may still use "
                "historical fallback if live mandi pairs were missing."
            ),
            "resourceId": DATA_GOV_RESOURCE_ID,
            "priceFreshnessUtc": _latest_timestamp(cached_rows),
            "liveRowCount": live_count,
            "fallbackRowCount": fallback_count,
            "notes": notes or ["Using locally cached mandi rows."],
        }

    fallback_rows = pipeline.build_fallback_rows()
    return fallback_rows, {
        "mode": "fallback",
        "sourceLabel": (
            "Live mandi rows are unavailable right now, so the website is using historical "
            "district fallback rows instead of pretending the board is live."
        ),
        "resourceId": DATA_GOV_RESOURCE_ID,
        "priceFreshnessUtc": _latest_timestamp(fallback_rows),
        "liveRowCount": 0,
        "fallbackRowCount": len(fallback_rows),
        "notes": notes or ["Live mandi rows unavailable; switched to fallback."],
    }


def _spot_cache_bucket(minutes: int = 30) -> int:
    return int(datetime.now(timezone.utc).timestamp() // (minutes * 60))


_WARMED_SPOT_BUCKETS: set[int] = set()
_WARMED_MARKET_ROW_KEYS: set[tuple[str, int]] = set()


@lru_cache(maxsize=4)
def _cached_live_spot_board(_bucket: int) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    pipeline = PricePipeline(timeout_seconds=8)
    snapshots, notes = pipeline.fetch_live_spot_snapshots()
    latest = max((item.get("arrivalDate") for item in snapshots.values() if item.get("arrivalDate")), default=None)
    _WARMED_SPOT_BUCKETS.add(_bucket)
    return snapshots, {
        "mode": "live" if snapshots else "unavailable",
        "sourceLabel": (
            "Current crop spot prices come from the Government of India mandi dataset on "
            "data.gov.in, generated through the AGMARKNET portal."
        ),
        "resourceId": DATA_GOV_RESOURCE_ID,
        "spotFreshnessUtc": latest,
        "notes": notes,
        "cropCount": len(snapshots),
    }


def load_live_spot_board(
    prefer_live: bool = True,
    *,
    warm_only: bool = False,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    bucket = _spot_cache_bucket()
    if not prefer_live or (warm_only and bucket not in _WARMED_SPOT_BUCKETS):
        return {}, {
            "mode": "disabled",
            "sourceLabel": "Live crop spot board disabled for this request.",
            "resourceId": DATA_GOV_RESOURCE_ID,
            "spotFreshnessUtc": None,
            "notes": [],
            "cropCount": 0,
    }
    return _cached_live_spot_board(bucket)


@lru_cache(maxsize=4)
def _cached_live_market_board(_bucket: int) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    pipeline = PricePipeline(timeout_seconds=8)
    board, notes = pipeline.fetch_live_market_board()
    latest = max(
        (
            row.get("arrivalDate")
            for rows in board.values()
            for row in rows
            if row.get("arrivalDate")
        ),
        default=None,
    )
    return board, {
        "mode": "live" if board else "unavailable",
        "sourceLabel": (
            "Live mandi board from the Government of India dataset on data.gov.in, "
            "generated through the AGMARKNET portal."
        ),
        "resourceId": DATA_GOV_RESOURCE_ID,
        "marketFreshnessUtc": latest,
        "notes": notes,
        "cropCount": len(board),
    }


def load_live_market_board(prefer_live: bool = True) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    if not prefer_live:
        return {}, {
            "mode": "disabled",
            "sourceLabel": "Live mandi board disabled for this request.",
            "resourceId": DATA_GOV_RESOURCE_ID,
            "marketFreshnessUtc": None,
            "notes": [],
            "cropCount": 0,
        }
    return _cached_live_market_board(_spot_cache_bucket())


@lru_cache(maxsize=32)
def _cached_live_market_rows(crop_slug: str, _bucket: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    pipeline = PricePipeline(timeout_seconds=8)
    _WARMED_MARKET_ROW_KEYS.add((crop_slug, _bucket))
    return pipeline.fetch_live_market_rows_for_crop(crop_slug)


def load_live_market_rows_for_crop(
    crop_slug: str,
    *,
    prefer_live: bool = True,
    warm_only: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    bucket = _spot_cache_bucket()
    if not prefer_live or (warm_only and (crop_slug, bucket) not in _WARMED_MARKET_ROW_KEYS):
        return [], {
            "mode": "disabled",
            "notes": [],
            "marketFreshnessUtc": None,
            "cropCount": 0,
        }
    return _cached_live_market_rows(crop_slug, bucket)


def load_weather_daily_rows(prefer_live: bool = True) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return weather rows plus source metadata for bot/website use."""

    pipeline = WeatherPipeline()
    if prefer_live:
        try:
            payload = pipeline.fetch_forecast()
            rows = pipeline.normalize_daily_rows(payload)
            return rows, {
                "mode": "live",
                "sourceLabel": "Live district weather stream from Open-Meteo for Nizamabad.",
                "weatherFreshnessUtc": _latest_timestamp(rows),
                "notes": [],
            }
        except Exception as exc:
            notes = [f"Open-Meteo fetch failed: {exc}"]
    else:
        notes = []

    cached_rows = _read_json_rows(LOCAL_DAILY_CACHE_PATH)
    if cached_rows:
        return cached_rows, {
            "mode": "cached",
            "sourceLabel": "Cached Nizamabad weather stream from the latest backend sync.",
            "weatherFreshnessUtc": _latest_timestamp(cached_rows),
            "notes": notes or ["Using locally cached weather rows."],
        }

    return [], {
        "mode": "empty",
        "sourceLabel": "Weather stream unavailable right now.",
        "weatherFreshnessUtc": None,
        "notes": notes,
    }


def build_market_options_for_farmer(
    *,
    mandal_slug: str,
    water_source: str,
    acres: float,
    crop_slug: str,
    price_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Estimate best reachable market after transport and commission."""

    current_rows = price_rows or load_current_price_rows()[0]
    matching_rows = [row for row in current_rows if row.get("crop_slug") == crop_slug]
    distance_map = {
        item["name"]: float(item["distance_km"])
        for item in MANDALS[mandal_slug].get("nearest_mandis", [])
    }

    crop_data = CROPS[crop_slug]
    yield_key = "canal_irrigated" if "canal" in (water_source or "") else "rainfed"
    yield_data = crop_data.get("yield_qtl_per_acre", {})
    yield_row = (
        yield_data.get(yield_key)
        or yield_data.get("rainfed")
        or yield_data.get("canal_irrigated")
        or {"avg": 10}
    )
    estimated_total_qtl = max(1.0, float(yield_row["avg"]) * float(acres or 1))

    options: list[dict[str, Any]] = []
    for row in matching_rows:
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
                "mandiName": mandi_name,
                "distanceKm": round(distance_km, 1),
                "modalPriceRsPerQtl": int(round(modal)),
                "transportTotalRs": int(round(transport_total)),
                "transportPerQtlRs": int(round(transport_per_qtl)),
                "commissionPerQtlRs": int(round(commission_per_qtl)),
                "netPerQtlRs": int(round(net_per_qtl)),
                "priceDate": row.get("price_date"),
                "source": row.get("source"),
            }
        )

    options.sort(key=lambda item: item["netPerQtlRs"], reverse=True)
    return options


def _profit_for_price(
    *,
    crop_slug: str,
    acres: float,
    water_source: str,
    loan_burden: int,
    price_per_qtl: int | float | None,
) -> dict[str, Any] | None:
    if price_per_qtl in (None, ""):
        return None

    crop_data = CROPS[crop_slug]
    yield_key = "canal_irrigated" if "canal" in (water_source or "") else "rainfed"
    yield_data = crop_data.get("yield_qtl_per_acre", {})
    yields = (
        yield_data.get(yield_key)
        or yield_data.get("rainfed")
        or yield_data.get("canal_irrigated")
    )
    if not yields:
        return None

    avg_yield = float(yields["avg"])
    input_cost = float(crop_data.get("input_cost_per_acre", 0))
    transport_per_quintal = 15.0
    commission_pct = 0.02
    seasonal_debt_service_due = round(max(loan_burden, 0) * 0.15)

    gross = avg_yield * float(price_per_qtl)
    transport = avg_yield * transport_per_quintal
    commission = gross * commission_pct
    net = round((gross - transport - commission - input_cost) * float(acres))
    return {
        "net": net,
        "netAfterDebtService": net - seasonal_debt_service_due,
        "avgYieldQtlPerAcre": avg_yield,
    }


def build_trade_signal_for_crop(
    *,
    mandal_slug: str,
    water_source: str,
    acres: float,
    crop_slug: str,
    current_price_rows: list[dict[str, Any]] | None = None,
    current_price_meta: dict[str, Any] | None = None,
    live_market_board: dict[str, list[dict[str, Any]]] | None = None,
    live_market_rows: list[dict[str, Any]] | None = None,
    live_market_meta: dict[str, Any] | None = None,
    live_spot_board: dict[str, dict[str, Any]] | None = None,
    live_spot_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    local_options = build_market_options_for_farmer(
        mandal_slug=mandal_slug,
        water_source=water_source,
        acres=acres,
        crop_slug=crop_slug,
        price_rows=current_price_rows,
    )
    best_local = local_options[0] if local_options else None

    live_rows = list(live_market_rows or (live_market_board or {}).get(crop_slug, []))
    live_rows.sort(key=lambda item: item.get("modalPriceRsPerQtl") or 0, reverse=True)
    best_live = live_rows[0] if live_rows else None
    live_spot = (live_spot_board or {}).get(crop_slug)

    if best_live:
        mode = "live_regional_market"
        source_label = (live_market_meta or {}).get(
            "sourceLabel",
            "Live mandi board from the Government of India dataset on data.gov.in.",
        )
        freshness = (live_market_meta or {}).get("marketFreshnessUtc")
        headline = (
            f"Live trade signal from {best_live.get('state') or best_live.get('scopeLabel')}. "
            "Use this as the freshest market context; local net calculations stay secondary "
            "unless a live local row exists."
        )
    elif live_spot:
        mode = "live_spot_only"
        source_label = (live_spot_meta or {}).get(
            "sourceLabel",
            "Current crop spot prices come from the Government of India mandi dataset on data.gov.in.",
        )
        freshness = (live_spot_meta or {}).get("spotFreshnessUtc")
        headline = "Only a representative live crop spot row is available right now."
    elif best_local:
        mode = "cached_local_board"
        source_label = (current_price_meta or {}).get(
            "sourceLabel",
            "Cached mandi board from the latest backend sync.",
        )
        freshness = (current_price_meta or {}).get("priceFreshnessUtc")
        headline = "Live crop rows were unavailable, so this is using the cached local mandi board."
    else:
        mode = "unavailable"
        source_label = "No usable trade signal is available for this crop right now."
        freshness = None
        headline = "No live or local board row is available for this crop."

    primary_options: list[dict[str, Any]] = []
    if best_live:
        primary_options = [
            {
                "mandiName": row.get("marketName"),
                "district": row.get("district"),
                "state": row.get("state"),
                "scopeLabel": row.get("scopeLabel"),
                "modalPriceRsPerQtl": row.get("modalPriceRsPerQtl"),
                "floorPriceRsPerQtl": row.get("floorPriceRsPerQtl"),
                "ceilingPriceRsPerQtl": row.get("ceilingPriceRsPerQtl"),
                "priceDate": row.get("arrivalDate"),
                "source": row.get("source"),
                "netPerQtlRs": row.get("modalPriceRsPerQtl"),
                "tradeMode": "live_regional_market",
            }
            for row in live_rows[:5]
        ]
    elif best_local:
        primary_options = [{**item, "tradeMode": "cached_local_board"} for item in local_options[:5]]

    return {
        "mode": mode,
        "headline": headline,
        "sourceLabel": source_label,
        "freshnessUtc": freshness,
        "bestOption": primary_options[0] if primary_options else None,
        "primaryOptions": primary_options,
        "bestLocalOption": best_local,
        "localOptions": local_options[:5],
        "bestLiveOption": primary_options[0] if best_live else None,
        "liveRows": primary_options if best_live else [],
        "liveSpot": live_spot,
    }


def build_seed_guidance_for_crop(
    farmer: FarmerProfile,
    crop_slug: str,
) -> dict[str, Any]:
    catalog = SEED_VARIETY_CATALOG.get(crop_slug, [])
    checklist = [
        "Certified packet with lot number and germination label undali.",
        "Dealer handwritten packet lekapothe open loose seed vaddu.",
        "Bill tiskondi. Problem vaste compensation proof ga panikosthundi.",
    ]

    return {
        "crop": crop_slug,
        "cropName": slug_to_label(crop_slug),
        "teluguName": CROPS[crop_slug].get("telugu_name", crop_slug),
        "varieties": catalog[:3],
        "purchaseChecklist": checklist,
        "fitSummary": (
            f"Choose varieties that suit {slug_to_label(farmer.mandal)}, "
            f"{slug_to_label(farmer.soil_zone)} soils, and {slug_to_label(farmer.water_source)} water conditions."
        ),
    }


def _cap_basis_label(cap_basis: str | None) -> str:
    labels = {
        "official_safe_cap": "official district safe cap",
        "adaptive_reference_cap": "adaptive cap built from district reference acreage and crop fit",
        "modeled_from_official_reference": "modeled from district reference acreage",
        "no_safe_cap": "no safe-cap baseline",
    }
    return labels.get(cap_basis or "", cap_basis or "district baseline")


def _build_crop_board_for_farmer(
    farmer: FarmerProfile,
    *,
    current_price_rows: list[dict[str, Any]] | None = None,
    current_price_meta: dict[str, Any] | None = None,
    live_market_board: dict[str, list[dict[str, Any]]] | None = None,
    live_market_meta: dict[str, Any] | None = None,
    live_spot_board: dict[str, dict[str, Any]] | None = None,
    live_spot_meta: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Build an inspectable board for every active crop, even blocked ones."""

    all_candidates = [
        crop_slug
        for crop_slug, crop_data in CROPS.items()
        if crop_data.get("active_for_recommendation", True)
    ]
    season_name = get_current_season_name()
    weather = get_weather_forecast(farmer.mandal)
    _, supply_info = filter_supply_cap(all_candidates, farmer.mandal, farmer.acres)

    price_predictions = add_price_prediction(all_candidates, farmer.water_source)
    profitability_rows = filter_profitability(
        all_candidates,
        farmer.acres,
        farmer.water_source,
        farmer.loan_burden,
        price_predictions,
    )
    profitability_map = {row["crop"]: row for row in profitability_rows}
    current_price_rows = current_price_rows or load_current_price_rows(prefer_live=False)[0]
    live_spot_board = live_spot_board or {}
    live_market_board = live_market_board or {}

    rows: list[dict[str, Any]] = []
    for crop_slug in all_candidates:
        crop = CROPS[crop_slug]
        supply = supply_info.get(crop_slug, {})
        price = price_predictions.get(crop_slug)
        profit = profitability_map.get(crop_slug)
        trade_signal = build_trade_signal_for_crop(
            mandal_slug=farmer.mandal,
            water_source=farmer.water_source,
            acres=farmer.acres,
            crop_slug=crop_slug,
            current_price_rows=current_price_rows,
            current_price_meta=current_price_meta,
            live_market_board=live_market_board,
            live_market_meta=live_market_meta,
            live_spot_board=live_spot_board,
            live_spot_meta=live_spot_meta,
        )
        best_market = trade_signal.get("bestLiveOption") or trade_signal.get("bestLocalOption")
        live_spot = live_spot_board.get(crop_slug)
        live_outcome = _profit_for_price(
            crop_slug=crop_slug,
            acres=farmer.acres,
            water_source=farmer.water_source,
            loan_burden=farmer.loan_burden,
            price_per_qtl=live_spot.get("modalPriceRsPerQtl") if live_spot else None,
        )
        current_profit = live_outcome["net"] if live_outcome else (profit.get("net_current") if profit else None)

        season_ok = crop_slug in filter_season([crop_slug], season_name)
        soil_ok = crop_slug in filter_soil([crop_slug], farmer.soil_zone, farmer.mandal)
        water_ok = crop_slug in filter_water_weather([crop_slug], farmer.water_source, weather)

        if not season_ok:
            rejection_reason = f"Season mismatch ({season_name})"
        elif not soil_ok:
            rejection_reason = "Soil or local suitability mismatch"
        elif not water_ok:
            rejection_reason = "Water requirement not met"
        elif supply.get("status") == "REJECT":
            rejection_reason = supply.get("reason", "Supply cap exceeded")
        elif not profit:
            rejection_reason = "Loss or cash risk at floor price"
        else:
            rejection_reason = None

        rows.append(
            {
                "slug": crop_slug,
                "name": slug_to_label(crop_slug),
                "teluguName": crop.get("telugu_name", crop_slug),
                "priceFloor": price.get("floor_price") if price else None,
                "priceCurrent": (
                    live_spot.get("modalPriceRsPerQtl")
                    if live_spot
                    else (price.get("avg_price") if price else None)
                ),
                "harvestModeledPrice": price.get("avg_price") if price else None,
                "priceCeiling": price.get("ceiling_price") if price else None,
                "expectedProfit": current_profit,
                "harvestModeledProfit": profit.get("net_current") if profit else None,
                "worstProfit": profit.get("net_floor") if profit else None,
                "bestMandi": best_market["mandiName"] if best_market else None,
                "bestMandiPrice": best_market["modalPriceRsPerQtl"] if best_market else None,
                "bestMandiPriceDate": best_market.get("priceDate") if best_market else None,
                "bestMandiPriceSource": best_market.get("source") if best_market else None,
                "bestMandiDistrict": best_market.get("district") if best_market else None,
                "bestMandiState": best_market.get("state") if best_market else None,
                "tradeSignalMode": trade_signal.get("mode"),
                "tradeSignalLabel": trade_signal.get("headline"),
                "spotPrice": live_spot.get("modalPriceRsPerQtl") if live_spot else None,
                "spotPriceFloor": live_spot.get("floorPriceRsPerQtl") if live_spot else None,
                "spotPriceCeiling": live_spot.get("ceilingPriceRsPerQtl") if live_spot else None,
                "spotPriceDate": live_spot.get("arrivalDate") if live_spot else None,
                "spotMarket": live_spot.get("representativeMarket") if live_spot else None,
                "spotDistrict": live_spot.get("representativeDistrict") if live_spot else None,
                "spotScopeLabel": live_spot.get("scopeLabel") if live_spot else None,
                "competitionStatus": supply.get("status", "LOW"),
                "competitionStatusLabel": STATUS_LABELS.get(supply.get("status", "LOW"), "open lane"),
                "competitionPctFilled": supply.get("projected_pct_filled", supply.get("pct_filled")),
                "capBasis": supply.get("cap_basis"),
                "capBasisLabel": _cap_basis_label(supply.get("cap_basis")),
                "reason": rejection_reason,
                "isRecommended": rejection_reason is None,
            }
        )

    status_order = {"LOW": 0, "MEDIUM": 1, "APPROACHING": 2, "OVERSUPPLY": 3, "REJECT": 4}
    rows.sort(
        key=lambda item: (
            0 if item["isRecommended"] else 1,
            status_order.get(item["competitionStatus"], 9),
            -(item["expectedProfit"] or -10**12),
        )
    )
    return rows


def build_home_proof_cards() -> list[dict[str, Any]]:
    return [
        {
            "title": "The shortlist is earned",
            "body": "Every crop must survive season, soil, water, pressure, and floor-profit checks before it can appear.",
        },
        {
            "title": "Blocked crops still stay visible",
            "body": "Crowded lanes like paddy or turmeric still show price and downside, so the market is visible even when the answer is no.",
        },
        {
            "title": "This is more than a market board",
            "body": "Prices stay visible, but so do crowding, downside, and the exact reason one crop survives while another does not.",
        },
    ]


def build_fairness_summary(result: dict[str, Any]) -> dict[str, Any]:
    top = result.get("top_pick")
    second = result.get("second_pick")
    ranked = result.get("ranked", [])
    supply_info = result.get("supply_info", {})
    rejected = result.get("rejected", [])

    if not top:
        return {
            "summary": "No crop survived all five filters for this profile.",
            "evidence": [],
        }

    top_supply = supply_info.get(top["crop"], {})
    evidence = [
        {
            "label": "Top crop floor safety",
            "value": f"₹{top['net_floor']:,}",
        },
        {
            "label": "Top crop projected district fill",
            "value": (
                f"{top_supply.get('projected_pct_filled')}%"
                if top_supply.get("projected_pct_filled") is not None
                else "reference baseline"
            ),
        },
    ]

    if second:
        second_supply = supply_info.get(second["crop"], {})
        evidence.append(
            {
                "label": "Second crop floor safety",
                "value": f"₹{second['net_floor']:,}",
            }
        )
        evidence.append(
            {
                "label": "Second crop projected district fill",
                "value": (
                    f"{second_supply.get('projected_pct_filled')}%"
                    if second_supply.get("projected_pct_filled") is not None
                    else "reference baseline"
                ),
            }
        )

    blocked = []
    for item in rejected:
        if item["reason"] in {"Supply cap exceeded", "Soil or local suitability mismatch"}:
            blocked.append(f"{slug_to_label(item['crop'])}: {item['reason']}")
        if len(blocked) == 3:
            break

    summary = (
        f"{slug_to_label(top['crop'])} wins because it survives all five filters and keeps "
        f"₹{top['net_floor']:,} alive even at floor price."
    )
    if second:
        summary += (
            f" {slug_to_label(second['crop'])} stays visible as the second lane, "
            f"but its downside cushion is lower."
        )

    return {
        "summary": summary,
        "evidence": evidence,
        "blockedExamples": blocked,
        "rankCount": len(ranked),
    }


def build_accountability_trail(result: dict[str, Any]) -> dict[str, Any]:
    farmer = result["farmer"]
    top = result.get("top_pick")
    if not top:
        return {
            "decisionVersion": CURRENT_SEASON,
            "profileKey": farmer.build_farmer_key(),
            "recommendation": "No safe crop",
            "reason": "All crops failed at least one hard filter.",
        }

    return {
        "decisionVersion": CURRENT_SEASON,
        "profileKey": farmer.build_farmer_key(),
        "recommendation": slug_to_label(top["crop"]),
        "reason": (
            f"{slug_to_label(top['crop'])} survived soil, water, supply, price, and "
            f"floor-profit checks for {slug_to_label(farmer.mandal)}."
        ),
    }


def build_cap_alerts(result: dict[str, Any]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    for crop_slug, info in result.get("supply_info", {}).items():
        status = info.get("status")
        if status not in {"APPROACHING", "OVERSUPPLY", "REJECT"}:
            continue
        alerts.append(
            {
                "crop": crop_slug,
                "name": slug_to_label(crop_slug),
                "teluguName": CROPS[crop_slug].get("telugu_name", crop_slug),
                "status": status,
                "statusLabel": STATUS_LABELS.get(status, status.lower()),
                "projectedPctFilled": info.get("projected_pct_filled"),
                "safeCapAcres": info.get("safe_cap"),
                "totalAcres": info.get("projected_total_acres"),
            }
        )
    alerts.sort(key=lambda item: (item["projectedPctFilled"] or 0), reverse=True)
    return alerts[:6]


def build_crop_caps() -> list[dict[str, Any]]:
    tracker = DistrictCapTracker()
    season_bot_acres = tracker.get_recommended_acres_by_crop(CURRENT_SEASON)
    rows = []

    for crop_slug, crop in CROPS.items():
        if not crop.get("active_for_recommendation", True):
            continue

        safe_cap, cap_basis = get_effective_safe_cap(crop_slug)
        planted = DISTRICT_PLANTED_ACRES.get(crop_slug, 0)
        bot_recommended = BOT_RECOMMENDED_ACRES.get(crop_slug, 0) + season_bot_acres.get(crop_slug, 0)
        total = planted + bot_recommended
        status, pct, projected_pct = derive_pressure_status(total, total, safe_cap)

        rows.append(
            {
                **crop_meta(crop_slug),
                "safeCapAcres": safe_cap,
                "plantedAcres": planted,
                "botRecommendedAcres": bot_recommended,
                "totalAcres": total,
                "pctFilled": pct,
                "projectedPctFilled": projected_pct,
                "status": status,
                "statusLabel": STATUS_LABELS.get(status, status.lower()),
                "capBasis": cap_basis,
            }
        )

    status_order = {"REJECT": 0, "OVERSUPPLY": 1, "APPROACHING": 2, "MEDIUM": 3, "LOW": 4}
    rows.sort(key=lambda item: (status_order.get(item["status"], 9), item["name"]))
    return rows


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
        if info.get("status") in {"OVERSUPPLY", "APPROACHING"}
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
            "highlights": blocked_by_supply[:3]
            or oversupply[:3]
            or [crop_meta(crop)["name"] for crop in after_supply[:3]],
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
        "capBasis": supply_info.get("cap_basis"),
        "capBasisLabel": _cap_basis_label(supply_info.get("cap_basis")),
        "cashFlowStatus": row.get("cash_flow_status"),
    }


def build_dashboard_analysis(
    farmer: FarmerProfile,
    price_rows: list[dict[str, Any]] | None = None,
    price_meta: dict[str, Any] | None = None,
    live_market_board: dict[str, list[dict[str, Any]]] | None = None,
    live_market_meta: dict[str, Any] | None = None,
    live_spot_board: dict[str, dict[str, Any]] | None = None,
    live_spot_meta: dict[str, Any] | None = None,
    soil_context: dict[str, Any] | None = None,
    prefer_live_trade_rows: bool = True,
) -> dict[str, Any]:
    result = recommend(farmer)
    supply_info = result.get("supply_info", {})
    ranked = [
        _format_ranked_row(row, supply_info.get(row["crop"], {}))
        for row in result.get("ranked", [])
    ]
    top_pick = ranked[0] if ranked else None
    second_pick = ranked[1] if len(ranked) > 1 else None
    weather = result.get("weather", {})
    current_price_rows, current_price_meta = (
        (price_rows, price_meta)
        if price_rows is not None and price_meta is not None
        else load_current_price_rows(prefer_live=False)
    )
    current_live_market_board = live_market_board or {}
    current_live_market_meta = live_market_meta or {
        "mode": "disabled",
        "sourceLabel": "Live market board is resolved per crop in the analysis surface.",
        "marketFreshnessUtc": None,
        "cropCount": 0,
    }
    current_live_spot_board, current_live_spot_meta = (
        (live_spot_board, live_spot_meta)
        if live_spot_board is not None and live_spot_meta is not None
        else load_live_spot_board(warm_only=True)
    )

    market_advice = None
    seed_guidance = None
    crop_board = _build_crop_board_for_farmer(
        farmer,
        current_price_rows=current_price_rows,
        current_price_meta=current_price_meta,
        live_market_board=current_live_market_board,
        live_market_meta=current_live_market_meta,
        live_spot_board=current_live_spot_board,
        live_spot_meta=current_live_spot_meta,
    )
    rank_index = {row["slug"]: index for index, row in enumerate(ranked)}
    top_slug = top_pick["slug"] if top_pick else None
    second_slug = second_pick["slug"] if second_pick else None
    crop_board.sort(
        key=lambda item: (
            0 if item["slug"] == top_slug else 1 if item["slug"] == second_slug else 2,
            rank_index.get(item["slug"], 999),
            0 if item["isRecommended"] else 1,
            -(item["expectedProfit"] or -10**12),
        )
    )
    def enrich_ranked_crop(item: dict[str, Any] | None) -> dict[str, Any] | None:
        if not item:
            return None
        live_spot = current_live_spot_board.get(item["slug"], {})
        live_market_rows_for_crop, live_market_meta_for_crop = load_live_market_rows_for_crop(
            item["slug"],
            prefer_live=prefer_live_trade_rows,
        )
        trade_signal = build_trade_signal_for_crop(
            mandal_slug=farmer.mandal,
            water_source=farmer.water_source,
            acres=farmer.acres,
            crop_slug=item["slug"],
            current_price_rows=current_price_rows,
            current_price_meta=current_price_meta,
            live_market_board=current_live_market_board,
            live_market_rows=live_market_rows_for_crop,
            live_market_meta=live_market_meta_for_crop,
            live_spot_board=current_live_spot_board,
            live_spot_meta=current_live_spot_meta,
        )
        best_local = trade_signal.get("bestLiveOption") or trade_signal.get("bestLocalOption")
        live_outcome = _profit_for_price(
            crop_slug=item["slug"],
            acres=farmer.acres,
            water_source=farmer.water_source,
            loan_burden=farmer.loan_burden,
            price_per_qtl=live_spot.get("modalPriceRsPerQtl") if live_spot else None,
        )
        return {
            **item,
            "priceCurrent": live_spot.get("modalPriceRsPerQtl") if live_spot else item.get("priceCurrent"),
            "harvestModeledPrice": item.get("priceCurrent"),
            "spotPrice": live_spot.get("modalPriceRsPerQtl"),
            "spotPriceFloor": live_spot.get("floorPriceRsPerQtl"),
            "spotPriceCeiling": live_spot.get("ceilingPriceRsPerQtl"),
            "spotPriceDate": live_spot.get("arrivalDate"),
            "spotMarket": live_spot.get("representativeMarket"),
            "spotDistrict": live_spot.get("representativeDistrict"),
            "spotScopeLabel": live_spot.get("scopeLabel"),
            "expectedProfit": live_outcome["net"] if live_outcome else item.get("expectedProfit"),
            "harvestModeledProfit": item.get("harvestModeledProfit", item.get("expectedProfit")),
            "bestMandi": best_local.get("mandiName") if best_local else None,
            "bestMandiPrice": best_local.get("modalPriceRsPerQtl") if best_local else None,
            "bestMandiPriceDate": best_local.get("priceDate") if best_local else None,
            "bestMandiPriceSource": best_local.get("source") if best_local else None,
            "bestMandiDistrict": best_local.get("district") if best_local else None,
            "bestMandiState": best_local.get("state") if best_local else None,
            "tradeSignalMode": trade_signal.get("mode"),
            "tradeSignalLabel": trade_signal.get("headline"),
        }
    top_pick = enrich_ranked_crop(top_pick)
    second_pick = enrich_ranked_crop(second_pick)

    if top_pick:
        top_live_market_rows, top_live_market_meta = load_live_market_rows_for_crop(
            top_pick["slug"],
            prefer_live=prefer_live_trade_rows,
        )
        trade_signal = build_trade_signal_for_crop(
            mandal_slug=farmer.mandal,
            water_source=farmer.water_source,
            acres=farmer.acres,
            crop_slug=top_pick["slug"],
            current_price_rows=current_price_rows,
            current_price_meta=current_price_meta,
            live_market_board=current_live_market_board,
            live_market_rows=top_live_market_rows,
            live_market_meta=top_live_market_meta,
            live_spot_board=current_live_spot_board,
            live_spot_meta=current_live_spot_meta,
        )
        market_advice = {
            "crop": top_pick["slug"],
            "cropName": top_pick["name"],
            "options": trade_signal["primaryOptions"][:3],
            "bestOption": trade_signal["bestOption"],
            "bestLocalOption": trade_signal["bestLocalOption"],
            "localOptions": trade_signal["localOptions"][:3],
            "sourceLabel": trade_signal["sourceLabel"],
            "mode": trade_signal.get("mode"),
            "headline": trade_signal.get("headline"),
            "freshnessUtc": trade_signal.get("freshnessUtc"),
            "localBoardMode": current_price_meta.get("mode"),
            "localBoardFreshnessUtc": current_price_meta.get("priceFreshnessUtc"),
        }
        seed_guidance = build_seed_guidance_for_crop(farmer, top_pick["slug"])

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
            "surveyNumber": getattr(farmer, "survey_number", None),
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
        "marketAdvice": market_advice,
        "cropBoard": crop_board,
        "fairness": build_fairness_summary(result),
        "accountability": build_accountability_trail(result),
        "capAlerts": build_cap_alerts(result),
        "seedGuidance": seed_guidance,
        "sourceContext": {
            "price": current_price_meta,
            "liveMarket": market_advice and {
                "mode": market_advice.get("mode"),
                "sourceLabel": market_advice.get("sourceLabel"),
                "marketFreshnessUtc": market_advice.get("freshnessUtc"),
            } or current_live_market_meta,
            "liveSpot": current_live_spot_meta,
            "assumptions": {
                "profitModel": "Current outcome uses the latest live crop spot when available; downside still uses conservative floor-price season modeling.",
                "soilSource": (
                    soil_context.get("source")
                    if soil_context
                    else "manual_profile_input"
                ),
                "soilSourceLabel": (
                    f"Survey-linked soil from {soil_context.get('source')}."
                    if soil_context
                    else "Manual soil input."
                ),
                "baselineSource": "District caps prefer official safe caps and use adaptive reference caps when explicit crop caps are missing.",
            },
        },
    }


def build_mandal_snapshot(
    price_rows: list[dict[str, Any]] | None = None,
    price_meta: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    tracker = DistrictCapTracker()
    current_price_rows, current_price_meta = (
        (price_rows, price_meta)
        if price_rows is not None and price_meta is not None
        else load_current_price_rows(prefer_live=False)
    )
    current_live_spot_board, current_live_spot_meta = load_live_spot_board()
    season_entries = tracker.get_entries(CURRENT_SEASON)
    entries_by_mandal: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in season_entries:
        mandal = str(entry.get("mandal") or "").strip().lower()
        if mandal:
            entries_by_mandal[mandal].append(entry)

    def build_signal_profile(entries: list[dict[str, Any]], *, fallback_mandal: str, signal_source: str) -> dict[str, Any] | None:
        if len(entries) < 3:
            return None

        def most_common(key: str, fallback: str | None = None) -> str | None:
            values = [str(item.get(key) or "").strip().lower() for item in entries if item.get(key)]
            if not values:
                return fallback
            return Counter(values).most_common(1)[0][0]

        acreage_values = [float(item.get("acres") or 0) for item in entries if float(item.get("acres") or 0) > 0]
        if not acreage_values:
            return None

        top_recommended_slugs = [
            crop_slug
            for crop_slug, _count in Counter(
                str(item.get("primary_crop") or "").strip().lower()
                for item in entries
                if item.get("primary_crop")
            ).most_common(3)
            if crop_slug
        ]

        return {
            "acres": round(float(median(acreage_values)), 1),
            "soil_zone": most_common("soil_zone", MANDALS[fallback_mandal].get("soil_zone")),
            "water_source": most_common("water_source", MANDALS[fallback_mandal].get("water")),
            "primary_crop_slugs": top_recommended_slugs or list(MANDALS[fallback_mandal].get("primary_crops", [])),
            "primary_crops": [slug_to_label(crop) for crop in (top_recommended_slugs or list(MANDALS[fallback_mandal].get("primary_crops", [])))],
            "sample_size": len(entries),
            "signal_source": signal_source,
        }

    def build_mandal_twin(mandal_slug: str) -> dict[str, Any] | None:
        direct_entries = entries_by_mandal.get(mandal_slug, [])
        direct_profile = build_signal_profile(
            direct_entries,
            fallback_mandal=mandal_slug,
            signal_source="live_mandal_twin",
        )
        if direct_profile:
            return direct_profile

        mandal = MANDALS[mandal_slug]
        soil_zone = mandal.get("soil_zone")
        water_source = mandal.get("water")

        def gather_profile(*, signal_source: str, slug_filter) -> dict[str, Any] | None:
            matched_slugs = sorted(
                {
                    other_slug
                    for other_slug, group_entries in entries_by_mandal.items()
                    if group_entries and other_slug != mandal_slug and slug_filter(other_slug)
                }
            )
            matched_entries = [
                entry
                for other_slug in matched_slugs
                for entry in entries_by_mandal.get(other_slug, [])
            ]
            profile = build_signal_profile(
                matched_entries,
                fallback_mandal=mandal_slug,
                signal_source=signal_source,
            )
            if not profile:
                return None
            profile["clusterMandals"] = [slug_to_label(other_slug) for other_slug in matched_slugs]
            return profile

        cluster_profile = gather_profile(
            signal_source="cluster_twin",
            slug_filter=lambda other_slug: (
                MANDALS.get(other_slug, {}).get("soil_zone") == soil_zone
                and MANDALS.get(other_slug, {}).get("water") == water_source
            ),
        )
        if cluster_profile:
            return cluster_profile

        soil_profile = gather_profile(
            signal_source="soil_twin",
            slug_filter=lambda other_slug: MANDALS.get(other_slug, {}).get("soil_zone") == soil_zone,
        )
        if soil_profile:
            return soil_profile

        water_profile = gather_profile(
            signal_source="water_twin",
            slug_filter=lambda other_slug: MANDALS.get(other_slug, {}).get("water") == water_source,
        )
        if water_profile:
            return water_profile
        return None

    mandal_rows = []

    for mandal_slug, mandal in sorted(MANDALS.items()):
        mandal_twin = build_mandal_twin(mandal_slug)
        if mandal_twin:
            acres = mandal_twin["acres"]
            soil_zone = mandal_twin["soil_zone"]
            water_source = mandal_twin["water_source"]
            primary_crops = mandal_twin["primary_crop_slugs"]
            primary_crop_labels = mandal_twin["primary_crops"]
            signal_source = mandal_twin["signal_source"]
            if signal_source == "cluster_twin":
                cluster_names = ", ".join(mandal_twin.get("clusterMandals", [])[:3])
                snapshot_assumption = (
                    f"Cluster twin built from {mandal_twin['sample_size']} recent signals across similar "
                    f"{slug_to_label(soil_zone)} / {slug_to_label(water_source)} mandals"
                    + (f" like {cluster_names}." if cluster_names else ".")
                )
            elif signal_source == "soil_twin":
                cluster_names = ", ".join(mandal_twin.get("clusterMandals", [])[:3])
                snapshot_assumption = (
                    f"Soil twin built from {mandal_twin['sample_size']} recent signals across "
                    f"{slug_to_label(soil_zone)} mandals"
                    + (f" like {cluster_names}." if cluster_names else ".")
                )
            elif signal_source == "water_twin":
                cluster_names = ", ".join(mandal_twin.get("clusterMandals", [])[:3])
                snapshot_assumption = (
                    f"Water twin built from {mandal_twin['sample_size']} recent signals across "
                    f"{slug_to_label(water_source)} mandals"
                    + (f" like {cluster_names}." if cluster_names else ".")
                )
            else:
                snapshot_assumption = (
                    f"Live mandal twin built from {mandal_twin['sample_size']} recent farmer recommendations. "
                    f"Median acreage {acres} with dominant {slug_to_label(soil_zone)} soil and "
                    f"{slug_to_label(water_source)} water."
                )
            signal_sample_size = mandal_twin["sample_size"]
        else:
            acres = 5
            soil_zone = mandal.get("soil_zone")
            water_source = mandal.get("water")
            primary_crops = mandal.get("primary_crops", [])
            primary_crop_labels = [slug_to_label(crop) for crop in primary_crops]
            snapshot_assumption = (
                "Representative 5-acre fallback using default mandal soil and water, "
                "live district pressure, and current mandi context with no loan burden."
            )
            signal_source = "representative_fallback"
            signal_sample_size = 0

        farmer = FarmerProfile(
            mandal=mandal_slug,
            acres=acres,
            soil_zone=soil_zone,
            water_source=water_source,
            loan_burden_rs=0,
            last_crops=primary_crops[:1],
            farmer_id=f"website-{mandal_slug}",
        )
        analysis = build_dashboard_analysis(
            farmer,
            price_rows=current_price_rows,
            price_meta=current_price_meta,
            live_market_board={},
            live_market_meta={
                "mode": "disabled",
                "sourceLabel": "Live market board disabled for district atlas snapshots.",
                "marketFreshnessUtc": None,
            },
            live_spot_board=current_live_spot_board,
            live_spot_meta=current_live_spot_meta,
            prefer_live_trade_rows=False,
        )
        top_pick = analysis.get("topPick")
        second_pick = analysis.get("secondPick")
        market_advice = analysis.get("marketAdvice") or {}
        best_market = market_advice.get("bestOption") or {}

        nearest_mandi = mandal.get("nearest_mandis", [{}])[0]
        mandal_rows.append(
            {
                "slug": mandal_slug,
                "name": slug_to_label(mandal_slug),
                "soilZone": soil_zone,
                "waterSource": water_source,
                "villages": mandal.get("villages"),
                "snapshotAcres": acres,
                "signalSource": signal_source,
                "signalSampleSize": signal_sample_size,
                "primaryCrops": primary_crop_labels,
                "nearestMandi": nearest_mandi.get("name"),
                "nearestMandiDistanceKm": nearest_mandi.get("distance_km"),
                "bestMandi": best_market.get("mandiName") or nearest_mandi.get("name"),
                "bestMandiNetPerQtlRs": best_market.get("netPerQtlRs"),
                "topPick": crop_meta(top_pick["slug"]) if top_pick else None,
                "secondPick": crop_meta(second_pick["slug"]) if second_pick else None,
                "topPickExpectedProfit": top_pick["expectedProfit"] if top_pick else None,
                "topPickWorstProfit": top_pick["worstProfit"] if top_pick else None,
                "topPickPriceCurrent": top_pick["priceCurrent"] if top_pick else None,
                "topPickCompetitionPctFilled": top_pick["competitionPctFilled"] if top_pick else None,
                "topPickCompetitionStatusLabel": (
                    STATUS_LABELS.get(top_pick.get("competitionStatus"), "open lane")
                    if top_pick
                    else None
                ),
                "secondPickCompetitionPctFilled": second_pick["competitionPctFilled"] if second_pick else None,
                "secondPickCompetitionStatusLabel": (
                    STATUS_LABELS.get(second_pick.get("competitionStatus"), "open lane")
                    if second_pick
                    else None
                ),
                "competitionStatus": top_pick.get("competitionStatus", "LOW") if top_pick else "LOW",
                "notes": mandal.get("notes", ""),
                "snapshotAssumption": snapshot_assumption,
            }
        )

    return mandal_rows


def build_demo_scenarios(
    price_rows: list[dict[str, Any]] | None = None,
    price_meta: dict[str, Any] | None = None,
    live_market_board: dict[str, list[dict[str, Any]]] | None = None,
    live_market_meta: dict[str, Any] | None = None,
    live_spot_board: dict[str, dict[str, Any]] | None = None,
    live_spot_meta: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
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
        farmer = FarmerProfile(farmer_id=f"website-demo-{index}", **scenario["profile"])
        analysis = build_dashboard_analysis(
            farmer,
            price_rows=price_rows,
            price_meta=price_meta,
            live_market_board=live_market_board,
            live_market_meta=live_market_meta,
            live_spot_board=live_spot_board,
            live_spot_meta=live_spot_meta,
            prefer_live_trade_rows=False,
        )
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
            {"speaker": "bot", "text": analysis["teluguReply"]},
        ]
        rendered.append(
            {
                "id": scenario["id"],
                "title": scenario["title"],
                "profile": {
                    "mandal": slug_to_label(analysis["profile"]["mandal"]),
                    "acres": analysis["profile"]["acres"],
                    "soilZone": analysis["profile"]["soilLabel"],
                    "waterSource": analysis["profile"]["waterLabel"],
                    "loanBurden": analysis["profile"]["loanBurdenRs"],
                    "lastCrops": analysis["profile"]["lastCropLabels"],
                },
                "topPick": analysis["topPick"],
                "secondPick": analysis["secondPick"],
                "rejected": analysis["rejected"],
                "filterTrace": analysis["filterTrace"],
                "teluguReply": analysis["teluguReply"],
                "conversation": transcript,
                "marketAdvice": analysis["marketAdvice"],
            }
        )
    return rendered


def build_summary(
    *,
    crop_caps: list[dict[str, Any]],
    mandals: list[dict[str, Any]],
    price_rows: list[dict[str, Any]],
    weather_daily: list[dict[str, Any]],
    price_meta: dict[str, Any],
    weather_meta: dict[str, Any],
    live_spot_meta: dict[str, Any],
    live_market_meta: dict[str, Any],
) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat()
    return {
        "generatedAtUtc": generated_at,
        "currentSeason": CURRENT_SEASON,
        "mandalCount": len(MANDALS),
        "mandiCount": len(MANDIS),
        "cropCount": len(CROPS),
        "activeRecommendationCrops": len([crop for crop in CROPS.values() if crop.get("active_for_recommendation", True)]),
        "mandalTopPickCount": len([item for item in mandals if item.get("topPick")]),
        "oversuppliedCropCount": len([item for item in crop_caps if item["status"] in {"OVERSUPPLY", "REJECT", "APPROACHING"}]),
        "openOpportunityCropCount": len([item for item in crop_caps if item["status"] == "LOW"]),
        "priceRowCount": len(price_rows),
        "weatherDayCount": len(weather_daily),
        "priceSourceLabel": price_meta.get("sourceLabel"),
        "priceMode": price_meta.get("mode"),
        "priceFreshnessUtc": price_meta.get("priceFreshnessUtc"),
        "liveMarketMode": live_market_meta.get("mode"),
        "liveMarketFreshnessUtc": live_market_meta.get("marketFreshnessUtc"),
        "liveMarketCropCount": live_market_meta.get("cropCount"),
        "liveSpotMode": live_spot_meta.get("mode"),
        "liveSpotFreshnessUtc": live_spot_meta.get("spotFreshnessUtc"),
        "liveSpotCropCount": live_spot_meta.get("cropCount"),
        "weatherSourceLabel": weather_meta.get("sourceLabel"),
        "weatherMode": weather_meta.get("mode"),
        "weatherFreshnessUtc": weather_meta.get("weatherFreshnessUtc"),
    }


def build_site_context() -> dict[str, Any]:
    price_rows, price_meta = load_current_price_rows(prefer_live=False)
    live_market_board, live_market_meta = load_live_market_board(prefer_live=False)
    live_spot_board, live_spot_meta = load_live_spot_board()
    weather_daily, weather_meta = load_weather_daily_rows()
    crop_caps = build_crop_caps()
    mandals = build_mandal_snapshot(price_rows=price_rows, price_meta=price_meta)
    demo_scenarios = build_demo_scenarios(
        price_rows=price_rows,
        price_meta=price_meta,
        live_market_board=live_market_board,
        live_market_meta=live_market_meta,
        live_spot_board=live_spot_board,
        live_spot_meta=live_spot_meta,
    )
    summary = build_summary(
        crop_caps=crop_caps,
        mandals=mandals,
        price_rows=price_rows,
        weather_daily=weather_daily,
        price_meta=price_meta,
        weather_meta=weather_meta,
        live_spot_meta=live_spot_meta,
        live_market_meta=live_market_meta,
    )

    return {
        "summary": summary,
        "proofCards": build_home_proof_cards(),
        "cropCaps": crop_caps,
        "mandals": mandals,
        "priceRows": price_rows,
        "weatherDaily": weather_daily,
        "demoScenarios": demo_scenarios,
        "liveContext": {
            "price": price_meta,
            "liveMarket": live_market_meta,
            "liveMarketBoard": live_market_board,
            "liveSpot": live_spot_meta,
            "liveSpotBoard": live_spot_board,
            "weather": weather_meta,
        },
    }


def build_markets_context() -> dict[str, Any]:
    live_market_board, live_market_meta = load_live_market_board(prefer_live=True)
    live_spot_board, live_spot_meta = load_live_spot_board()
    weather_daily, weather_meta = load_weather_daily_rows()
    return {
        "liveMarket": live_market_meta,
        "liveMarketBoard": live_market_board,
        "liveSpot": live_spot_meta,
        "liveSpotBoard": live_spot_board,
        "weather": weather_meta,
        "weatherDaily": weather_daily,
    }
