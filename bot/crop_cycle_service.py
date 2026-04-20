"""Persistent crop-cycle state for season calendars and alert evaluation."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.drying_alerts import DryingAlertService
from bot.proactive_monitor import ProactiveMonitor
from bot.farmer_profile import CROP_ALIASES, FarmerProfile as StoredFarmerProfile
from engine.season_calendar import SeasonCalendar


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STORE_PATH = ROOT / "data" / "crop_cycles.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_farming_date(
    value: str | date | datetime | None,
    *,
    reference_date: date | None = None,
) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = str(value).strip().lower()
    if not text:
        return None

    today = reference_date or date.today()
    if text == "today":
        return today
    if text == "yesterday":
        return today - timedelta(days=1)
    if text == "tomorrow":
        return today + timedelta(days=1)

    for fmt in (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d %b %Y",
        "%d %B %Y",
        "%b %d %Y",
        "%B %d %Y",
    ):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    month_only_formats = ("%d %b", "%d %B", "%b %d", "%B %d")
    for fmt in month_only_formats:
        try:
            parsed = datetime.strptime(text, fmt).date()
            return parsed.replace(year=today.year)
        except ValueError:
            continue

    return None


def normalize_cycle_crop(
    raw_crop: str | None,
    *,
    profile: StoredFarmerProfile | None = None,
) -> str | None:
    if raw_crop:
        normalized = raw_crop.strip().lower().replace("-", " ")
        aliases = sorted(CROP_ALIASES.items(), key=lambda item: len(item[0]), reverse=True)
        for alias, canonical in aliases:
            if alias in normalized:
                return canonical
        slug = normalized.replace(" ", "_")
        if slug:
            return slug

    if profile and profile.last_three_crops:
        return profile.last_three_crops[0]
    return None


@dataclass
class CropCycleState:
    phone_number: str
    crop_name: str | None = None
    sowing_date: str | None = None
    delay_days: int = 0
    drying_start: str | None = None
    last_harvest_date: str | None = None
    last_water_date: str | None = None
    sent_alert_keys: list[str] = field(default_factory=list)
    created_at_utc: str | None = None
    updated_at_utc: str | None = None

    def to_record(self) -> dict:
        record = asdict(self)
        if not record["created_at_utc"]:
            record["created_at_utc"] = _utc_now()
        record["updated_at_utc"] = _utc_now()
        return record


class CropCycleService:
    """Store crop-cycle milestones and evaluate due reminders."""

    def __init__(
        self,
        *,
        store_path: str | Path = DEFAULT_STORE_PATH,
        calendar: SeasonCalendar | None = None,
        proactive_monitor: ProactiveMonitor | None = None,
        drying_alert_service: DryingAlertService | None = None,
    ) -> None:
        self.store_path = Path(store_path)
        self.calendar = calendar or SeasonCalendar()
        self.proactive_monitor = proactive_monitor or ProactiveMonitor()
        self.drying_alert_service = drying_alert_service or DryingAlertService()

    def get_state(self, phone_number: str) -> CropCycleState:
        store = self._read_store()
        record = store.get(phone_number)
        if not record:
            return CropCycleState(phone_number=phone_number)
        return CropCycleState(**record)

    def save_state(self, state: CropCycleState) -> CropCycleState:
        store = self._read_store()
        store[state.phone_number] = state.to_record()
        self._write_store(store)
        return CropCycleState(**store[state.phone_number])

    def clear_state(self, phone_number: str) -> None:
        store = self._read_store()
        if phone_number in store:
            del store[phone_number]
            self._write_store(store)

    def set_sowing(
        self,
        phone_number: str,
        *,
        crop_name: str,
        sowing_date: str | date | datetime,
        delay_days: int = 0,
    ) -> dict:
        state = self.get_state(phone_number)
        parsed_date = parse_farming_date(sowing_date)
        if not parsed_date:
            raise ValueError("Could not parse sowing date.")

        state.crop_name = normalize_cycle_crop(crop_name) or crop_name
        state.sowing_date = parsed_date.isoformat()
        state.delay_days = int(delay_days)
        saved = self.save_state(state)

        return {
            "state": saved,
            "calendar": self.calendar.build(
                saved.crop_name or crop_name,
                saved.sowing_date,
                delay_days=saved.delay_days,
            ),
        }

    def set_drying_start(
        self,
        phone_number: str,
        *,
        drying_start: str | date | datetime | None = None,
        crop_name: str | None = None,
    ) -> CropCycleState:
        state = self.get_state(phone_number)
        parsed = parse_farming_date(drying_start or date.today())
        if not parsed:
            raise ValueError("Could not parse drying start date.")

        if crop_name:
            state.crop_name = normalize_cycle_crop(crop_name) or crop_name
        state.drying_start = parsed.isoformat()
        state.last_harvest_date = parsed.isoformat()
        return self.save_state(state)

    def set_last_water(
        self,
        phone_number: str,
        *,
        last_water_date: str | date | datetime,
    ) -> CropCycleState:
        state = self.get_state(phone_number)
        parsed = parse_farming_date(last_water_date)
        if not parsed:
            raise ValueError("Could not parse last water date.")
        state.last_water_date = parsed.isoformat()
        return self.save_state(state)

    def get_calendar(self, phone_number: str) -> dict | None:
        state = self.get_state(phone_number)
        if not state.crop_name or not state.sowing_date:
            return None
        return self.calendar.build(
            state.crop_name,
            state.sowing_date,
            delay_days=state.delay_days,
        )

    def preview_alerts(
        self,
        phone_number: str,
        *,
        now: str | date | datetime | None = None,
    ) -> dict:
        state = self.get_state(phone_number)
        calendar_payload = self.get_calendar(phone_number)
        current_time = parse_farming_date(now) if isinstance(now, str) else now
        if isinstance(current_time, date) and not isinstance(current_time, datetime):
            current_time = datetime.combine(current_time, datetime.min.time())
        if current_time is None:
            current_time = datetime.now()
        current_date = current_time.date()

        upcoming_events: list[dict] = []
        if calendar_payload:
            for event in calendar_payload["events"]:
                event_date = parse_farming_date(event["date"])
                if not event_date:
                    continue
                if event_date >= current_date:
                    upcoming_events.append(event)
                if len(upcoming_events) >= 5:
                    break

        proactive_alerts = []
        if state.crop_name and state.sowing_date:
            proactive_alerts = self.proactive_monitor.evaluate(
                state.phone_number,
                crop_name=state.crop_name,
                sowing_date=state.sowing_date,
                today=current_date,
            )

        drying_alerts = []
        if state.drying_start:
            drying_alerts = self.drying_alert_service.evaluate(
                state.phone_number,
                drying_start=state.drying_start,
                now=current_time,
            )

        return {
            "state": asdict(state),
            "calendar": calendar_payload,
            "upcoming_events": upcoming_events,
            "proactive_alerts": proactive_alerts,
            "drying_alerts": drying_alerts,
        }

    def collect_due_alerts(
        self,
        *,
        now: str | date | datetime | None = None,
        mark_sent: bool = True,
    ) -> list[dict]:
        current_time = parse_farming_date(now) if isinstance(now, str) else now
        if isinstance(current_time, date) and not isinstance(current_time, datetime):
            current_time = datetime.combine(current_time, datetime.min.time())
        if current_time is None:
            current_time = datetime.now()
        today = current_time.date()

        store = self._read_store()
        due: list[dict] = []

        for phone_number, record in store.items():
            state = CropCycleState(**record)
            preview = self.preview_alerts(phone_number, now=current_time)

            for event in preview["upcoming_events"]:
                if event["date"] != today.isoformat():
                    continue
                key = f"calendar:{event['date']}:{event['title']}"
                if key in state.sent_alert_keys:
                    continue
                due.append({
                    "phone_number": phone_number,
                    "alert_type": "season_calendar",
                    "title": event["title"],
                    "message": event["note"],
                    "state": asdict(state),
                    "key": key,
                })
                if mark_sent:
                    state.sent_alert_keys.append(key)

            for alert in preview["proactive_alerts"]:
                key = f"proactive:{today.isoformat()}:{alert['title']}"
                if key in state.sent_alert_keys:
                    continue
                due.append({
                    "phone_number": phone_number,
                    "alert_type": alert["type"],
                    "title": alert["title"],
                    "message": alert["message"],
                    "state": asdict(state),
                    "key": key,
                })
                if mark_sent:
                    state.sent_alert_keys.append(key)

            for alert in preview["drying_alerts"]:
                key = f"drying:{today.isoformat()}:{alert['type']}:{alert.get('forecast_time', '')}"
                if key in state.sent_alert_keys:
                    continue
                due.append({
                    "phone_number": phone_number,
                    "alert_type": alert["type"],
                    "title": alert["title"],
                    "message": alert["message"],
                    "state": asdict(state),
                    "key": key,
                })
                if mark_sent:
                    state.sent_alert_keys.append(key)

            if mark_sent:
                store[phone_number] = state.to_record()

        if mark_sent:
            self._write_store(store)

        return due

    def _read_store(self) -> dict[str, dict]:
        if not self.store_path.exists():
            return {}
        try:
            return json.loads(self.store_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _write_store(self, payload: dict[str, dict]) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
