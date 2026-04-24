"""
Rythu Mitra — Supabase bootstrap + seed helper.

What this script does:
- applies the local SQL schema files when a direct Postgres connection string is available
- generates a canonical `data/price_history.csv` if it doesn't exist yet
- loads historical mandi price rows into Supabase
- runs the daily price pipeline
- runs the weather pipeline

Usage:
    python3 scripts/seed_supabase.py

Direct database connection:
- set DATABASE_URL or SUPABASE_DB_URL to allow automatic schema creation
- without a DB URL, REST writes still work only if the tables already exist
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import psycopg2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.price_pipeline import DEFAULT_HISTORY_CSV_PATH, PricePipeline
from engine.district_cap import DistrictCapTracker
from engine.weather_pipeline import WeatherPipeline


ROOT = Path(__file__).resolve().parent.parent
SQL_FILES = [
    ROOT / "scripts" / "create_mandi_prices_table.sql",
    ROOT / "scripts" / "create_weather_forecast_tables.sql",
    ROOT / "scripts" / "create_farmer_profiles_table.sql",
    ROOT / "scripts" / "create_recommendation_log_table.sql",
]


def load_local_env(env_path: Path | None = None) -> None:
    path = env_path or ROOT / ".env"
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


def get_database_url() -> str:
    return (
        os.getenv("DATABASE_URL", "").strip()
        or os.getenv("SUPABASE_DB_URL", "").strip()
    )


def apply_sql_files(database_url: str) -> dict[str, object]:
    applied_files: list[str] = []

    conn = psycopg2.connect(database_url)
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            for sql_file in SQL_FILES:
                sql = sql_file.read_text(encoding="utf-8")
                cur.execute(sql)
                applied_files.append(sql_file.name)
            cur.execute("NOTIFY pgrst, 'reload schema'")
    finally:
        conn.close()

    time.sleep(1)

    return {
        "status": "ok",
        "applied_files": applied_files,
        "postgrest_schema_reloaded": True,
    }


def main() -> None:
    load_local_env()

    database_url = get_database_url()
    if database_url:
        schema_result = apply_sql_files(database_url)
    else:
        schema_result = {
            "status": "skipped",
            "warning": "DATABASE_URL or SUPABASE_DB_URL not set; schema bootstrap skipped.",
        }

    price_pipeline = PricePipeline()
    history_csv_path = ROOT / DEFAULT_HISTORY_CSV_PATH

    if history_csv_path.exists():
        history_csv_result = {
            "status": "ok",
            "csv_path": str(history_csv_path),
            "note": "Existing historical CSV reused.",
        }
    else:
        history_csv_result = price_pipeline.export_default_history_csv(
            csv_path=str(history_csv_path)
        )

    historical_seed_result = price_pipeline.load_historical_csv(
        csv_path=str(history_csv_path),
        persist=True,
    )
    daily_price_result = price_pipeline.run(persist=True)
    weather_result = WeatherPipeline().run(persist=True)
    recommendation_log_sync = DistrictCapTracker().sync_local_to_supabase()

    summary = {
        "schema": schema_result,
        "history_csv": history_csv_result,
        "historical_seed": historical_seed_result,
        "daily_prices": daily_price_result,
        "weather": weather_result,
        "recommendation_log_sync": recommendation_log_sync,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
