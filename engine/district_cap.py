"""Per-season district recommendation log and cap tracker."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOG_PATH = ROOT / "data" / "recommendation_log.json"


class DistrictCapTracker:
    """Persist primary recommendations so cap logic survives restarts."""

    def __init__(self, log_path: str | Path = DEFAULT_LOG_PATH) -> None:
        self.log_path = Path(log_path)

    def _load_payload(self) -> dict[str, Any]:
        if not self.log_path.exists():
            return {"entries": []}

        try:
            payload = json.loads(self.log_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"entries": []}

        if not isinstance(payload, dict):
            return {"entries": []}
        entries = payload.get("entries")
        if not isinstance(entries, list):
            payload["entries"] = []
        return payload

    def _save_payload(self, payload: dict[str, Any]) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def get_entries(self, season: str | None = None) -> list[dict[str, Any]]:
        payload = self._load_payload()
        entries = payload.get("entries", [])
        if not season:
            return entries
        return [entry for entry in entries if entry.get("season") == season]

    def get_recommended_acres_by_crop(self, season: str) -> dict[str, int]:
        totals: dict[str, float] = {}
        for entry in self.get_entries(season=season):
            crop = entry.get("primary_crop")
            acres = float(entry.get("acres") or 0)
            if not crop or acres <= 0:
                continue
            totals[crop] = totals.get(crop, 0.0) + acres
        return {crop: int(round(acres)) for crop, acres in totals.items()}

    def record_recommendation(
        self,
        *,
        season: str,
        farmer_key: str,
        acres: float,
        primary_crop: str | None,
        mandal: str,
        soil_zone: str,
        water_source: str,
        farmer_id: str | None = None,
        secondary_crop: str | None = None,
        source: str = "engine",
        survey_number: str | None = None,
    ) -> dict[str, Any]:
        payload = self._load_payload()
        entries: list[dict[str, Any]] = payload.get("entries", [])

        if not primary_crop:
            return {"stored": False, "warning": "No primary crop to log."}

        new_entry = {
            "season": season,
            "farmer_key": farmer_key,
            "farmer_id": farmer_id,
            "survey_number": survey_number,
            "mandal": mandal,
            "soil_zone": soil_zone,
            "water_source": water_source,
            "acres": acres,
            "primary_crop": primary_crop,
            "secondary_crop": secondary_crop,
            "source": source,
            "logged_at_utc": datetime.now(timezone.utc).isoformat(),
        }

        replaced = False
        for idx, entry in enumerate(entries):
            if entry.get("season") == season and entry.get("farmer_key") == farmer_key:
                entries[idx] = new_entry
                replaced = True
                break

        if not replaced:
            entries.append(new_entry)

        payload["entries"] = entries
        self._save_payload(payload)

        return {
            "stored": True,
            "updated_existing": replaced,
            "season_entries": len([entry for entry in entries if entry.get("season") == season]),
            "totals_by_crop": self.get_recommended_acres_by_crop(season),
        }
