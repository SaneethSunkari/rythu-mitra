"""Weather + crop-stage proactive disease alert evaluation."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from data.nizamabad_district import CROPS, WEATHER_PROFILE
from engine.season_calendar import SeasonCalendar
from engine.weather_pipeline import LOCAL_DAILY_CACHE_PATH, LOCAL_HOURLY_CACHE_PATH, WeatherPipeline


def _coerce_date(value: str | date | datetime) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _load_weather_rows(path_str: str) -> list[dict[str, Any]]:
    path = Path(path_str)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    pipeline = WeatherPipeline()
    payload = pipeline.fetch_forecast()
    if "hourly" in path.name:
        return pipeline.normalize_hourly_rows(payload)
    return pipeline.normalize_daily_rows(payload)


class ProactiveMonitor:
    """Evaluate upcoming disease pressure before the farmer reports symptoms."""

    def __init__(self, weather_pipeline: WeatherPipeline | None = None) -> None:
        self.weather_pipeline = weather_pipeline or WeatherPipeline()
        self.calendar = SeasonCalendar()

    def evaluate(
        self,
        farmer_id: str | None = None,
        *,
        crop_name: str | None = None,
        sowing_date: str | date | datetime | None = None,
        weather_hourly_rows: list[dict[str, Any]] | None = None,
        weather_daily_rows: list[dict[str, Any]] | None = None,
        today: str | date | datetime | None = None,
    ) -> list[dict]:
        del farmer_id  # persistent farmer lookup is not wired yet

        if not crop_name or not sowing_date:
            return []

        crop_key = crop_name.strip().lower().replace(" ", "_")
        if crop_key not in CROPS:
            return []

        today_date = _coerce_date(today or date.today())
        sowing = _coerce_date(sowing_date)
        day_from_sowing = max((today_date - sowing).days, 0)

        hourly_rows = weather_hourly_rows or _load_weather_rows(LOCAL_HOURLY_CACHE_PATH)
        daily_rows = weather_daily_rows or _load_weather_rows(LOCAL_DAILY_CACHE_PATH)

        alerts: list[dict] = []
        month_key = today_date.strftime("%B").lower()
        calendar_risks = WEATHER_PROFILE.get("disease_risk_calendar", {}).get(month_key, [])

        if crop_key == "paddy":
            humid_hours = [
                row for row in hourly_rows[:48]
                if (row.get("relative_humidity_2m_pct") or 0) >= 90
                and (row.get("cloud_cover_pct") or 0) >= 70
            ]
            if day_from_sowing >= 6 and len(humid_hours) >= 6:
                alerts.append({
                    "severity": "high",
                    "crop": crop_key,
                    "type": "proactive_disease_alert",
                    "disease": "blast",
                    "title": "Paddy blast risk is rising",
                    "message": "Humidity + cloud cover pattern matches early blast pressure. Preventive spray window is open now.",
                    "recommended_action": "Tricyclazole 75WP @ 1g per pump this week.",
                    "source_signals": {
                        "day_from_sowing": day_from_sowing,
                        "calendar_match": "paddy_blast_risk_HIGH" in calendar_risks or "paddy_blast_risk_medium" in calendar_risks,
                        "humid_hours": len(humid_hours),
                    },
                })

        if crop_key == "turmeric":
            wet_days = [
                row for row in daily_rows[:5]
                if (row.get("precipitation_sum_mm") or 0) >= 10
            ]
            if day_from_sowing >= 30 and wet_days:
                alerts.append({
                    "severity": "high",
                    "crop": crop_key,
                    "type": "proactive_disease_alert",
                    "disease": "rhizome_rot",
                    "title": "Turmeric rhizome rot risk is rising",
                    "message": "Recent wet spell + crop stage match rhizome rot pressure.",
                    "recommended_action": "Improve drainage and keep Metalaxyl + Mancozeb drench ready.",
                    "source_signals": {
                        "day_from_sowing": day_from_sowing,
                        "calendar_match": "turmeric_rhizome_rot" in " ".join(calendar_risks),
                        "wet_days": len(wet_days),
                    },
                })

        if crop_key == "maize":
            mild_wet_days = [
                row for row in daily_rows[:5]
                if (row.get("precipitation_probability_max_pct") or 0) >= 20
            ]
            if 10 <= day_from_sowing <= 50 and mild_wet_days:
                alerts.append({
                    "severity": "medium",
                    "crop": crop_key,
                    "type": "proactive_disease_alert",
                    "disease": "fall_army_worm",
                    "title": "Maize pest window is opening",
                    "message": "This stage is vulnerable to fall army worm. Field scouting should happen before visible spread.",
                    "recommended_action": "Inspect whorls and keep Emamectin Benzoate ready if fresh damage is seen.",
                    "source_signals": {
                        "day_from_sowing": day_from_sowing,
                        "calendar_match": "maize_fall_army_worm" in calendar_risks,
                        "watch_days": len(mild_wet_days),
                    },
                })

        next_monitor = None
        calendar_payload = self.calendar.build(crop_key, sowing)
        for event in calendar_payload["events"]:
            if event["type"] == "monitoring" and event["day_from_sowing"] >= day_from_sowing:
                next_monitor = event
                break

        if next_monitor:
            alerts.append({
                "severity": "info",
                "crop": crop_key,
                "type": "monitoring_reminder",
                "disease": None,
                "title": "Upcoming crop-stage monitoring check",
                "message": next_monitor["title"],
                "recommended_action": "Share a fresh field photo around this window.",
                "source_signals": {
                    "stage": next_monitor.get("stage"),
                    "scheduled_date": next_monitor["date"],
                },
            })

        return alerts
