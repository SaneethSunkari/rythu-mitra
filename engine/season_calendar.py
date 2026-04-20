"""Crop-stage season calendar generation for reminders and alerts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from data.nizamabad_district import CROPS
from data.specialty_crops import SPECIALTY_CROPS


FERTILIZER_WINDOWS = {
    "paddy": [
        {"day": 0, "label": "Basal dose", "note": "Apply basal fertilizer at sowing/transplant stage."},
        {"day": 25, "label": "Tillering top dress", "note": "Top dress during active tillering."},
        {"day": 45, "label": "Panicle support", "note": "Support panicle initiation stage nutrition."},
    ],
    "maize": [
        {"day": 0, "label": "Basal dose", "note": "Apply starter fertilizer at sowing."},
        {"day": 20, "label": "Vegetative top dress", "note": "Top dress before rapid vegetative growth."},
        {"day": 40, "label": "Pre-tassel support", "note": "Support tasseling and early cob development."},
    ],
    "turmeric": [
        {"day": 0, "label": "Basal dose", "note": "Apply FYM and basal fertilizer during planting."},
        {"day": 60, "label": "Vegetative support", "note": "Top dress during active vegetative growth."},
        {"day": 120, "label": "Rhizome bulking support", "note": "Support rhizome bulking stage."},
    ],
    "cotton": [
        {"day": 0, "label": "Basal dose", "note": "Apply basal fertilizer at sowing."},
        {"day": 30, "label": "Square-stage support", "note": "Top dress before squaring."},
        {"day": 60, "label": "Flowering support", "note": "Support flowering and boll set."},
    ],
}


@dataclass(frozen=True)
class CalendarEvent:
    date: str
    day_from_sowing: int
    type: str
    title: str
    stage: str | None
    note: str


def _coerce_date(value: str | date | datetime) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


class SeasonCalendar:
    """Build stage-aware season reminders from crop metadata."""

    def build(
        self,
        crop_name: str,
        sowing_date: str | date | datetime,
        *,
        delay_days: int = 0,
    ) -> dict:
        crop_key = crop_name.strip().lower().replace(" ", "_")
        if crop_key in SPECIALTY_CROPS:
            return self._build_specialty_calendar(crop_key, sowing_date, delay_days=delay_days)
        if crop_key not in CROPS:
            raise ValueError(f"Unknown crop: {crop_name}")

        crop = CROPS[crop_key]
        start_date = _coerce_date(sowing_date) + timedelta(days=delay_days)
        grow_duration = int(crop.get("grow_duration_days", 0))
        harvest_start = start_date + timedelta(days=max(grow_duration - 7, 0))
        harvest_end = start_date + timedelta(days=grow_duration + 7)

        events: list[CalendarEvent] = [
            CalendarEvent(
                date=start_date.isoformat(),
                day_from_sowing=0,
                type="milestone",
                title="Sowing confirmed",
                stage="sowing",
                note="Season calendar starts from the confirmed sowing date.",
            )
        ]

        for item in FERTILIZER_WINDOWS.get(crop_key, []):
            event_date = start_date + timedelta(days=int(item["day"]))
            events.append(
                CalendarEvent(
                    date=event_date.isoformat(),
                    day_from_sowing=int(item["day"]),
                    type="fertilizer",
                    title=item["label"],
                    stage=None,
                    note=item["note"],
                )
            )

        for item in crop.get("monitoring_schedule", []):
            event_date = start_date + timedelta(days=int(item["day"]))
            events.append(
                CalendarEvent(
                    date=event_date.isoformat(),
                    day_from_sowing=int(item["day"]),
                    type="monitoring",
                    title=f"Monitoring check: {item['check']}",
                    stage=item.get("stage"),
                    note="Crop-specific monitoring reminder.",
                )
            )

        events.append(
            CalendarEvent(
                date=harvest_start.isoformat(),
                day_from_sowing=max(grow_duration - 7, 0),
                type="harvest_window",
                title="Harvest window opens",
                stage="harvest",
                note="Start checking moisture, buyers, and drying conditions.",
            )
        )
        events.append(
            CalendarEvent(
                date=harvest_end.isoformat(),
                day_from_sowing=grow_duration + 7,
                type="harvest_window",
                title="Harvest window closes",
                stage="harvest",
                note="Late harvest risk rises after this point.",
            )
        )

        events.sort(key=lambda event: (event.day_from_sowing, event.type, event.title))

        return {
            "crop": crop_key,
            "crop_telugu_name": crop.get("telugu_name", crop_key),
            "sowing_date": start_date.isoformat(),
            "delay_days": delay_days,
            "grow_duration_days": grow_duration,
            "harvest_window": {
                "start_date": harvest_start.isoformat(),
                "end_date": harvest_end.isoformat(),
            },
            "events": [event.__dict__ for event in events],
        }

    def _build_specialty_calendar(
        self,
        crop_key: str,
        sowing_date: str | date | datetime,
        *,
        delay_days: int = 0,
    ) -> dict:
        crop = SPECIALTY_CROPS[crop_key]
        start_date = _coerce_date(sowing_date) + timedelta(days=delay_days)
        grow_duration = int(crop.get("grow_duration_days", 180))
        harvest_start = start_date + timedelta(days=max(grow_duration - 7, 0))
        harvest_end = start_date + timedelta(days=grow_duration + 7)

        events: list[CalendarEvent] = [
            CalendarEvent(
                date=start_date.isoformat(),
                day_from_sowing=0,
                type="milestone",
                title="Sowing confirmed",
                stage="sowing",
                note="Specialty-crop calendar starts from the confirmed sowing date.",
            ),
            CalendarEvent(
                date=start_date.isoformat(),
                day_from_sowing=0,
                type="buyer_activation",
                title="Buyer search starts now",
                stage="buyer_search",
                note="High-value crop: buyer confirmation should start from day 1.",
            ),
        ]

        for item in crop.get("monitoring_schedule", []):
            event_date = start_date + timedelta(days=int(item["day"]))
            events.append(
                CalendarEvent(
                    date=event_date.isoformat(),
                    day_from_sowing=int(item["day"]),
                    type=item.get("type", "monitoring"),
                    title=item["title"],
                    stage=item.get("stage"),
                    note=item["note"],
                )
            )

        events.append(
            CalendarEvent(
                date=harvest_start.isoformat(),
                day_from_sowing=max(grow_duration - 7, 0),
                type="harvest_window",
                title="Harvest window opens",
                stage="harvest",
                note="Premium buyer coordination should already be active before this window.",
            )
        )
        events.append(
            CalendarEvent(
                date=harvest_end.isoformat(),
                day_from_sowing=grow_duration + 7,
                type="harvest_window",
                title="Harvest window closes",
                stage="harvest",
                note="Late harvest risk rises after this point.",
            )
        )

        events.sort(key=lambda event: (event.day_from_sowing, event.type, event.title))

        return {
            "crop": crop_key,
            "crop_telugu_name": crop.get("telugu_name", crop_key),
            "sowing_date": start_date.isoformat(),
            "delay_days": delay_days,
            "grow_duration_days": grow_duration,
            "harvest_window": {
                "start_date": harvest_start.isoformat(),
                "end_date": harvest_end.isoformat(),
            },
            "events": [event.__dict__ for event in events],
        }
