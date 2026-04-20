"""Canal release ingest and alert evaluation."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.crop_cycle_service import CropCycleService, parse_farming_date
from data.specialty_crops import default_canal_release_entries


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CANAL_PATH = ROOT / "data" / "canal_release_schedule.json"


def _coerce_datetime(value: str | date | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time(), tzinfo=timezone.utc)
    text = str(value)
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        parsed = parse_farming_date(text)
        if not parsed:
            return None
        return datetime.combine(parsed, datetime.min.time(), tzinfo=timezone.utc)


@dataclass
class CanalRelease:
    system: str
    branch_slug: str
    branch_name: str
    release_time: str
    available_hours: int
    rotation_gap_days: int
    mandals: list[str]
    source: str
    source_note: str | None = None


class CanalAlertService:
    """Load canal release feed and create advance alerts."""

    def __init__(
        self,
        *,
        schedule_path: str | Path = DEFAULT_CANAL_PATH,
        feed_url: str | None = None,
        crop_cycle_service: CropCycleService | None = None,
    ) -> None:
        self.schedule_path = Path(schedule_path)
        self.feed_url = feed_url or os.getenv("CANAL_RELEASE_FEED_URL", "")
        self.crop_cycle_service = crop_cycle_service or CropCycleService()

    def load_releases(self) -> list[CanalRelease]:
        records: list[dict[str, Any]] = []
        if self.feed_url:
            try:
                with request.urlopen(self.feed_url, timeout=20) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                if isinstance(payload, list):
                    records = payload
            except (error.URLError, json.JSONDecodeError, ValueError):
                records = []

        if not records:
            if self.schedule_path.exists():
                try:
                    payload = json.loads(self.schedule_path.read_text(encoding="utf-8"))
                    records = payload if isinstance(payload, list) else []
                except json.JSONDecodeError:
                    records = []

        if not records:
            records = default_canal_release_entries()
            self.save_releases(records)
        else:
            parsed_times = [_coerce_datetime(record.get("release_time")) for record in records]
            all_seeded = all(record.get("source") == "scenario_seed" for record in records)
            if all_seeded and parsed_times and all((time_value is not None and time_value < datetime.now(timezone.utc)) for time_value in parsed_times):
                records = default_canal_release_entries()
                self.save_releases(records)

        releases = []
        for record in records:
            releases.append(
                CanalRelease(
                    system=record["system"],
                    branch_slug=record["branch_slug"],
                    branch_name=record["branch_name"],
                    release_time=record["release_time"],
                    available_hours=int(record["available_hours"]),
                    rotation_gap_days=int(record["rotation_gap_days"]),
                    mandals=list(record["mandals"]),
                    source=record.get("source", "manual"),
                    source_note=record.get("source_note"),
                )
            )
        return releases

    def save_releases(self, releases: list[dict[str, Any]]) -> None:
        self.schedule_path.parent.mkdir(parents=True, exist_ok=True)
        self.schedule_path.write_text(
            json.dumps(releases, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def set_release(self, entry: dict[str, Any]) -> None:
        records = [r.__dict__ for r in self.load_releases()]
        records = [record for record in records if record["branch_slug"] != entry["branch_slug"]]
        records.append(entry)
        self.save_releases(records)

    def evaluate_farmer_alerts(
        self,
        phone_number: str,
        mandal: str,
        *,
        now: str | date | datetime | None = None,
    ) -> list[dict]:
        current = _coerce_datetime(now) or datetime.now(timezone.utc)
        state = self.crop_cycle_service.get_state(phone_number)
        alerts: list[dict] = []

        for release in self.load_releases():
            if mandal not in release.mandals:
                continue

            release_time = _coerce_datetime(release.release_time)
            if not release_time:
                continue
            lead_hours = int((release_time - current).total_seconds() // 3600)
            if lead_hours < 0 or lead_hours > 24:
                continue

            crop_name = state.crop_name or "mee crop"
            last_water_gap = None
            if getattr(state, "last_water_date", None):
                water_date = parse_farming_date(state.last_water_date)
                if water_date:
                    last_water_gap = max((current.date() - water_date).days, 0)

            message = (
                f"Naanna, URGENT: {release.system} {release.branch_name} water release "
                f"{release_time.strftime('%b %d %I:%M %p')} ki undi. "
                f"Meeru branch lo approx {release.available_hours} gantalu water dorukutundi. "
                "Field preparation ippude cheyyandi."
            )
            if release.rotation_gap_days:
                message += f" Next rotation approx {release.rotation_gap_days} rojula tarvatha."
            if last_water_gap is not None:
                message += f" Last water nunchi {last_water_gap} rojulu ayyi unte stress risk perigedi."
            if crop_name:
                message += f" Current crop: {crop_name.replace('_', ' ')}."

            alerts.append({
                "type": "canal_release_alert",
                "severity": "urgent" if lead_hours <= 12 else "high",
                "branch_slug": release.branch_slug,
                "release_time": release.release_time,
                "lead_hours": lead_hours,
                "rotation_gap_days": release.rotation_gap_days,
                "message": message,
                "source": release.source,
            })

        return alerts
