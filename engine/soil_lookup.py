"""Survey-number soil lookup helpers for the decision studio and bot."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any
from urllib import error, parse, request

from data.nizamabad_district import MANDALS
from engine.district_cap import DistrictCapTracker


TGRAC_FIELD_LAYER_QUERY_URL = (
    "https://tgrac.telangana.gov.in/arcgis/rest/services/Agri2/"
    "Agriculture2_CropAnalysis_Layers/MapServer/1/query"
)


def normalize_survey_number(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r"\s+", "", str(value)).strip()
    return cleaned or None


def _map_tgrac_soil(raw_value: str | None) -> str | None:
    text = str(raw_value or "").strip().lower()
    if not text:
        return None
    if "non agriculture" in text:
        return None
    if "black" in text:
        return "black_cotton"
    if "calcareous" in text or "calci" in text or "lime" in text:
        return "deep_calcareous"
    if "red" in text or "chalka" in text or "loamy" in text:
        return "red_clayey"
    if "mixed" in text:
        return "mixed"
    return None


def _map_tgrac_water(raw_value: str | None) -> str | None:
    text = str(raw_value or "").strip().lower()
    if not text:
        return None
    if "canal" in text:
        return "canal"
    if "rain" in text:
        return "rainfed"
    if any(token in text for token in ("bore", "dugwell", "tubewell", "well")):
        return "borewell"
    return None


def lookup_known_survey_profile(mandal_slug: str, survey_number: str) -> dict[str, Any] | None:
    tracker = DistrictCapTracker()
    entries = tracker.get_entries()
    survey_matches = [
        entry
        for entry in entries
        if normalize_survey_number(entry.get("survey_number")) == survey_number
        and str(entry.get("mandal") or "").strip().lower() == mandal_slug
    ]
    if not survey_matches:
        return None

    def most_common(key: str) -> str | None:
        values = [
            str(item.get(key) or "").strip().lower()
            for item in survey_matches
            if item.get(key)
        ]
        if not values:
            return None
        return Counter(values).most_common(1)[0][0]

    soil_zone = most_common("soil_zone")
    water_source = most_common("water_source")
    if not soil_zone and not water_source:
        return None

    return {
        "soilZone": soil_zone,
        "waterSource": water_source,
        "source": "known_survey_profile",
        "confidence": "high",
        "sampleSize": len(survey_matches),
        "rawSoilType": None,
        "rawWaterSource": None,
    }


def lookup_tgrac_parcel_context(mandal_slug: str, survey_number: str) -> dict[str, Any] | None:
    mandal_name = MANDALS.get(mandal_slug, {}).get("display_name") or MANDALS.get(mandal_slug, {})
    if isinstance(mandal_name, dict):
        mandal_name = mandal_slug.replace("_", " ").title()

    where = f"Base_Survey_No='{survey_number}' AND M_Name='{mandal_name}'"
    params = parse.urlencode(
        {
            "where": where,
            "outFields": "Base_Survey_No,M_Name,V_Name,Soil_Type,Irrigation_L_1",
            "returnGeometry": "false",
            "f": "json",
            "resultRecordCount": 5,
        }
    )
    req = request.Request(
        f"{TGRAC_FIELD_LAYER_QUERY_URL}?{params}",
        headers={"Accept": "application/json", "User-Agent": "rythu-mitra/0.1"},
    )

    try:
        with request.urlopen(req, timeout=8) as response:
            import json

            payload = json.loads(response.read().decode("utf-8"))
    except (TimeoutError, error.URLError, error.HTTPError, ValueError):
        return None

    features = payload.get("features") or []
    if not features:
        return None

    soils = [
        _map_tgrac_soil((item.get("attributes") or {}).get("Soil_Type"))
        for item in features
    ]
    waters = [
        _map_tgrac_water((item.get("attributes") or {}).get("Irrigation_L_1"))
        for item in features
    ]
    mapped_soils = [item for item in soils if item]
    mapped_waters = [item for item in waters if item]
    if not mapped_soils and not mapped_waters:
        return None

    raw_first = (features[0].get("attributes") or {}) if features else {}
    return {
        "soilZone": Counter(mapped_soils).most_common(1)[0][0] if mapped_soils else None,
        "waterSource": Counter(mapped_waters).most_common(1)[0][0] if mapped_waters else None,
        "source": "tgrac_field_parcel_layer",
        "confidence": "medium",
        "sampleSize": len(features),
        "rawSoilType": raw_first.get("Soil_Type"),
        "rawWaterSource": raw_first.get("Irrigation_L_1"),
    }


def lookup_survey_context(mandal_slug: str, survey_number: str | None) -> dict[str, Any] | None:
    normalized = normalize_survey_number(survey_number)
    if not normalized:
        return None

    known = lookup_known_survey_profile(mandal_slug, normalized)
    if known:
        return {"surveyNumber": normalized, **known}

    tgrac = lookup_tgrac_parcel_context(mandal_slug, normalized)
    if tgrac:
        return {"surveyNumber": normalized, **tgrac}

    return None
