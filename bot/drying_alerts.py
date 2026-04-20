"""Post-harvest drying weather alert evaluation."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from engine.weather_pipeline import LOCAL_DAILY_CACHE_PATH, LOCAL_HOURLY_CACHE_PATH, WeatherPipeline


def _coerce_datetime(value: str | date | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    return datetime.fromisoformat(str(value))


def _load_rows(path_str: str) -> list[dict[str, Any]]:
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


class DryingAlertService:
    """Evaluate drying-phase weather windows and urgent rain risk."""

    def __init__(self, weather_pipeline: WeatherPipeline | None = None) -> None:
        self.weather_pipeline = weather_pipeline or WeatherPipeline()

    def evaluate(
        self,
        farmer_id: str | None = None,
        *,
        drying_start: str | date | datetime | None = None,
        now: str | date | datetime | None = None,
        hourly_rows: list[dict[str, Any]] | None = None,
        daily_rows: list[dict[str, Any]] | None = None,
    ) -> list[dict]:
        del farmer_id, drying_start  # persistence is not wired yet

        current_time = _coerce_datetime(now or datetime.now())
        hourly = hourly_rows or _load_rows(LOCAL_HOURLY_CACHE_PATH)
        daily = daily_rows or _load_rows(LOCAL_DAILY_CACHE_PATH)

        alerts: list[dict] = []

        next_hours = []
        for row in hourly:
            forecast_time = datetime.fromisoformat(row["forecast_time"])
            if forecast_time >= current_time:
                next_hours.append({**row, "_forecast_dt": forecast_time})
            if len(next_hours) >= 12:
                break

        next_three = next_hours[:3]
        urgent_hits = [
            row for row in next_three
            if (row.get("precipitation_probability_pct") or 0) >= 60
        ]
        if urgent_hits:
            first = urgent_hits[0]
            alerts.append({
                "severity": "urgent",
                "type": "drying_rain_alert",
                "title": "Urgent drying alert",
                "message": "Rain probability crossed 60% within the next 3 hours. Drying crop should be covered immediately.",
                "recommended_action": "Cover or move the produce now. Do not wait for visible clouds.",
                "forecast_time": first["_forecast_dt"].isoformat(),
                "rain_probability_pct": first.get("precipitation_probability_pct"),
            })

        daytime_summary = None
        if 5 <= current_time.hour <= 9 and daily:
            today_row = daily[0]
            daytime_summary = {
                "severity": "info",
                "type": "drying_day_summary",
                "title": "Morning drying summary",
                "message": (
                    f"Today's max rain probability is {today_row.get('precipitation_probability_max_pct')}% "
                    f"with total rain {today_row.get('precipitation_sum_mm')} mm."
                ),
                "recommended_action": "Keep checking every 3 hours if produce is still drying in the open.",
            }
            alerts.append(daytime_summary)

        if 17 <= current_time.hour <= 20 and daily:
            tonight_row = daily[0]
            alerts.append({
                "severity": "info",
                "type": "drying_night_summary",
                "title": "Night drying summary",
                "message": (
                    f"Tonight's rain probability peaks around {tonight_row.get('precipitation_probability_max_pct')}%. "
                    "If produce is still outside, keep cover material ready."
                ),
                "recommended_action": "Night-time drying should only continue if rain risk stays low.",
            })

        rolling_watch = [
            {
                "forecast_time": row["_forecast_dt"].isoformat(),
                "rain_probability_pct": row.get("precipitation_probability_pct"),
            }
            for row in next_hours[:4]
        ]
        alerts.append({
            "severity": "info",
            "type": "drying_three_hour_watch",
            "title": "Rolling 3-hour rain watch",
            "message": "Short-window rain watch for drying management.",
            "recommended_action": "Use this as the 3-hour decision window for open drying.",
            "watch_points": rolling_watch,
        })

        return alerts
