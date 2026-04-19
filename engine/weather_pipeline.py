"""
Rythu Mitra — Weather Pipeline

Fetches Open-Meteo forecast data for Nizamabad and stores:
- hourly rain probability forecasts
- daily temperature forecasts

The response also includes a few extra weather fields that will be useful for
future disease-risk and drying-alert modules.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.nizamabad_district import WEATHER_PROFILE


OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"
HOURLY_TABLE = "weather_hourly_forecasts"
DAILY_TABLE = "weather_daily_forecasts"
DEFAULT_FORECAST_DAYS = 7
DEFAULT_TIMEZONE = "Asia/Kolkata"
LOCAL_HOURLY_CACHE_PATH = "data/cache/weather_hourly_forecasts.json"
LOCAL_DAILY_CACHE_PATH = "data/cache/weather_daily_forecasts.json"


def _load_local_env(env_path: str = ".env") -> None:
    path = Path(env_path)
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


class WeatherPipeline:
    """Open-Meteo fetch + Supabase persistence for Nizamabad forecasts."""

    def __init__(
        self,
        latitude: float | None = None,
        longitude: float | None = None,
        timezone_name: str = DEFAULT_TIMEZONE,
        forecast_days: int = DEFAULT_FORECAST_DAYS,
        base_url: str | None = None,
        supabase_url: str | None = None,
        supabase_key: str | None = None,
        timeout_seconds: int = 20,
    ) -> None:
        _load_local_env()

        coords = WEATHER_PROFILE.get("coords", {})
        self.latitude = latitude if latitude is not None else coords.get("lat", 18.6714)
        self.longitude = longitude if longitude is not None else coords.get("lon", 78.0942)
        self.timezone_name = timezone_name
        self.forecast_days = forecast_days
        self.base_url = (base_url or os.getenv("OPEN_METEO_BASE_URL") or OPEN_METEO_BASE_URL).rstrip("/")
        self.supabase_url = (supabase_url or os.getenv("SUPABASE_URL", "")).rstrip("/")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        self.timeout_seconds = timeout_seconds
        self.local_hourly_cache_path = Path(LOCAL_HOURLY_CACHE_PATH)
        self.local_daily_cache_path = Path(LOCAL_DAILY_CACHE_PATH)

    def _store_rows_locally(self, table_name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
        path = self.local_hourly_cache_path if table_name == HOURLY_TABLE else self.local_daily_cache_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
        return {
            "stored_local": len(rows),
            "local_cache_path": str(path),
        }

    def _build_url(self) -> str:
        params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timezone": self.timezone_name,
            "forecast_days": self.forecast_days,
            "hourly": ",".join([
                "precipitation_probability",
                "temperature_2m",
                "relative_humidity_2m",
                "cloud_cover",
                "rain",
                "showers",
                "weather_code",
            ]),
            "daily": ",".join([
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_probability_max",
                "precipitation_sum",
                "weather_code",
            ]),
        }
        return f"{self.base_url}?{parse.urlencode(params)}"

    def fetch_forecast(self) -> dict[str, Any]:
        req = request.Request(
            self._build_url(),
            headers={
                "Accept": "application/json",
                "User-Agent": "rythu-mitra/0.1",
            },
        )
        with request.urlopen(req, timeout=self.timeout_seconds) as response:
            payload = response.read().decode("utf-8")
        return json.loads(payload)

    def normalize_hourly_rows(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        hourly = payload.get("hourly", {})
        times = hourly.get("time", [])

        rows: list[dict[str, Any]] = []
        fetched_at = datetime.now(timezone.utc).isoformat()

        for idx, forecast_time in enumerate(times):
            rows.append({
                "location_name": "Nizamabad",
                "location_slug": "nizamabad",
                "forecast_time": forecast_time,
                "latitude": payload.get("latitude", self.latitude),
                "longitude": payload.get("longitude", self.longitude),
                "timezone": payload.get("timezone", self.timezone_name),
                "precipitation_probability_pct": self._value_at(hourly, "precipitation_probability", idx),
                "temperature_2m_c": self._value_at(hourly, "temperature_2m", idx),
                "relative_humidity_2m_pct": self._value_at(hourly, "relative_humidity_2m", idx),
                "cloud_cover_pct": self._value_at(hourly, "cloud_cover", idx),
                "rain_mm": self._value_at(hourly, "rain", idx),
                "showers_mm": self._value_at(hourly, "showers", idx),
                "weather_code": self._value_at(hourly, "weather_code", idx),
                "source": "open_meteo",
                "fetched_at_utc": fetched_at,
                "raw_record": {
                    "time": forecast_time,
                    "precipitation_probability": self._value_at(hourly, "precipitation_probability", idx),
                    "temperature_2m": self._value_at(hourly, "temperature_2m", idx),
                    "relative_humidity_2m": self._value_at(hourly, "relative_humidity_2m", idx),
                    "cloud_cover": self._value_at(hourly, "cloud_cover", idx),
                    "rain": self._value_at(hourly, "rain", idx),
                    "showers": self._value_at(hourly, "showers", idx),
                    "weather_code": self._value_at(hourly, "weather_code", idx),
                },
            })

        return rows

    def normalize_daily_rows(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        daily = payload.get("daily", {})
        dates = daily.get("time", [])

        rows: list[dict[str, Any]] = []
        fetched_at = datetime.now(timezone.utc).isoformat()

        for idx, forecast_date in enumerate(dates):
            rows.append({
                "location_name": "Nizamabad",
                "location_slug": "nizamabad",
                "forecast_date": forecast_date,
                "latitude": payload.get("latitude", self.latitude),
                "longitude": payload.get("longitude", self.longitude),
                "timezone": payload.get("timezone", self.timezone_name),
                "temperature_2m_max_c": self._value_at(daily, "temperature_2m_max", idx),
                "temperature_2m_min_c": self._value_at(daily, "temperature_2m_min", idx),
                "precipitation_probability_max_pct": self._value_at(daily, "precipitation_probability_max", idx),
                "precipitation_sum_mm": self._value_at(daily, "precipitation_sum", idx),
                "weather_code": self._value_at(daily, "weather_code", idx),
                "source": "open_meteo",
                "fetched_at_utc": fetched_at,
                "raw_record": {
                    "date": forecast_date,
                    "temperature_2m_max": self._value_at(daily, "temperature_2m_max", idx),
                    "temperature_2m_min": self._value_at(daily, "temperature_2m_min", idx),
                    "precipitation_probability_max": self._value_at(daily, "precipitation_probability_max", idx),
                    "precipitation_sum": self._value_at(daily, "precipitation_sum", idx),
                    "weather_code": self._value_at(daily, "weather_code", idx),
                },
            })

        return rows

    @staticmethod
    def _value_at(container: dict[str, list[Any]], key: str, idx: int) -> Any:
        values = container.get(key, [])
        if idx >= len(values):
            return None
        return values[idx]

    def store_rows(
        self,
        table_name: str,
        rows: list[dict[str, Any]],
        conflict_columns: str,
    ) -> dict[str, Any]:
        if not rows:
            return {"stored": 0, "warning": "No rows to store."}
        if not self.supabase_url or not self.supabase_key:
            local = self._store_rows_locally(table_name, rows)
            return {
                "stored": 0,
                "warning": "Supabase credentials missing; rows stored locally instead.",
                **local,
            }

        endpoint = f"{self.supabase_url}/rest/v1/{table_name}?on_conflict={conflict_columns}"
        payload = json.dumps(rows).encode("utf-8")
        req = request.Request(
            endpoint,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}",
                "Prefer": "resolution=merge-duplicates,return=representation",
            },
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
            stored_rows = json.loads(body) if body else []
            return {"stored": len(stored_rows) or len(rows)}
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            local = self._store_rows_locally(table_name, rows)
            return {
                "stored": 0,
                "warning": f"{table_name} store failed with HTTP {exc.code}.",
                "details": details,
                **local,
            }
        except error.URLError as exc:
            local = self._store_rows_locally(table_name, rows)
            return {
                "stored": 0,
                "warning": f"{table_name} request failed: {exc.reason}.",
                **local,
            }

    def run(self, persist: bool = True) -> dict[str, Any]:
        payload = self.fetch_forecast()
        hourly_rows = self.normalize_hourly_rows(payload)
        daily_rows = self.normalize_daily_rows(payload)

        if persist:
            hourly_store = self.store_rows(
                HOURLY_TABLE,
                hourly_rows,
                "forecast_time,location_slug,source",
            )
            daily_store = self.store_rows(
                DAILY_TABLE,
                daily_rows,
                "forecast_date,location_slug,source",
            )
        else:
            hourly_store = {"stored": 0, "warning": "Persist disabled."}
            daily_store = {"stored": 0, "warning": "Persist disabled."}

        return {
            "status": "ok",
            "source": "open_meteo",
            "location": {
                "name": "Nizamabad",
                "latitude": payload.get("latitude", self.latitude),
                "longitude": payload.get("longitude", self.longitude),
                "timezone": payload.get("timezone", self.timezone_name),
            },
            "hourly_rows_prepared": len(hourly_rows),
            "daily_rows_prepared": len(daily_rows),
            "hourly_rows_stored": hourly_store.get("stored", 0),
            "daily_rows_stored": daily_store.get("stored", 0),
            "hourly_rows_stored_locally": hourly_store.get("stored_local", 0),
            "daily_rows_stored_locally": daily_store.get("stored_local", 0),
            "hourly_storage_warning": hourly_store.get("warning"),
            "daily_storage_warning": daily_store.get("warning"),
            "hourly_storage_details": hourly_store.get("details"),
            "daily_storage_details": daily_store.get("details"),
            "hourly_local_cache_path": hourly_store.get("local_cache_path"),
            "daily_local_cache_path": daily_store.get("local_cache_path"),
        }


def _build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rythu Mitra weather pipeline")
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Fetch forecast without writing to Supabase.",
    )
    parser.add_argument(
        "--forecast-days",
        type=int,
        default=DEFAULT_FORECAST_DAYS,
        help="Number of forecast days to request from Open-Meteo.",
    )
    return parser


if __name__ == "__main__":
    args = _build_cli().parse_args()
    summary = WeatherPipeline(forecast_days=args.forecast_days).run(
        persist=not args.no_persist
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
