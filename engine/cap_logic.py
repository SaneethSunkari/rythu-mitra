"""Shared district-cap helpers used by the engine, bot, and website."""

from __future__ import annotations

from data.nizamabad_district import CROPS, MANDALS, MANDIS


REFERENCE_SAFE_CAP_MULTIPLIER = 1.5

STATUS_LABELS = {
    "REJECT": "already crowded",
    "OVERSUPPLY": "high caution",
    "APPROACHING": "approaching cap",
    "MEDIUM": "watch closely",
    "LOW": "open lane",
}

TELUGU_COMPETITION_LABELS = {
    "LOW": "takkuva mandhi vestunnaru — open lane undi",
    "MEDIUM": "moderate competition undi",
    "APPROACHING": "cap daggara ki vachesthondi — careful ga decide cheyyali",
    "OVERSUPPLY": "chala mandhi vestunnaru — risk ekkuva",
    "REJECT": "district already crowded — fresh entry risky",
}


def _adaptive_reference_multiplier(crop_slug: str) -> float:
    """Derive a crop-specific safe-cap multiplier from structural district fit.

    Some crops only have official reference acreage instead of an explicit safe cap.
    Instead of applying one fixed multiplier to every such crop, we widen or tighten
    the derived cap based on:
    - how many soil zones support the crop
    - how many seasons the crop can fit
    - how many district mandis actively trade it
    - how many mandals structurally fit the crop
    - whether the crop is low/medium/high water intensity
    """

    crop = CROPS.get(crop_slug, {})
    soil_breadth = len(crop.get("soil_compatible", []))
    season_breadth = len(crop.get("season", []))
    traded_mandi_count = sum(
        1 for mandi in MANDIS.values() if crop_slug in mandi.get("crops_traded", [])
    )
    mandal_fit_count = sum(
        1
        for mandal in MANDALS.values()
        if mandal.get("soil_zone") in crop.get("soil_compatible", [])
    )

    multiplier = 1.1
    multiplier += min(soil_breadth, 4) * 0.07
    multiplier += min(season_breadth, 2) * 0.08
    multiplier += min(traded_mandi_count, 5) * 0.05
    multiplier += min(mandal_fit_count, 20) * 0.012

    water_requirement = crop.get("water_requirement")
    if water_requirement == "low":
        multiplier += 0.12
    elif water_requirement == "medium":
        multiplier += 0.05
    elif water_requirement == "very_high":
        multiplier -= 0.08

    if crop.get("active_for_recommendation", True) is False:
        multiplier -= 0.12

    return max(1.25, min(multiplier, 2.15))


def get_effective_safe_cap(crop_slug: str) -> tuple[int | None, str]:
    """Return the safe-cap acreage and the basis used to derive it."""

    crop = CROPS.get(crop_slug, {})
    explicit = crop.get("safe_cap_acres")
    if explicit:
        return int(explicit), "official_safe_cap"

    reference = crop.get("district_acreage_reference_acres")
    if reference:
        multiplier = _adaptive_reference_multiplier(crop_slug)
        baseline_multiplier = max(multiplier, REFERENCE_SAFE_CAP_MULTIPLIER)
        modeled = max(1, int(round(float(reference) * baseline_multiplier)))
        return modeled, "adaptive_reference_cap"

    return None, "no_safe_cap"


def derive_pressure_status(
    total_acres: float,
    projected_total_acres: float,
    safe_cap_acres: int | None,
) -> tuple[str, float | None, float | None]:
    """Map total and projected acreage to a normalized pressure tier."""

    if not safe_cap_acres:
        return "LOW", None, None

    pct_filled = (total_acres / safe_cap_acres) * 100 if safe_cap_acres > 0 else 100.0
    projected_pct = (
        (projected_total_acres / safe_cap_acres) * 100 if safe_cap_acres > 0 else 100.0
    )

    if total_acres >= safe_cap_acres or projected_total_acres > safe_cap_acres:
        status = "REJECT"
    elif projected_pct >= 70:
        status = "OVERSUPPLY"
    elif projected_pct >= 55:
        status = "APPROACHING"
    elif projected_pct >= 40:
        status = "MEDIUM"
    else:
        status = "LOW"

    return status, round(pct_filled, 1), round(projected_pct, 1)
