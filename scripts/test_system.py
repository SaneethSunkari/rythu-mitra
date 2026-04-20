"""Run the main local verification sweep for the current Rythu Mitra repo."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bot.whatsapp_handler as whatsapp_handler
from bot.whatsapp_handler import app
from data.nizamabad_district import MANDALS
from engine.crop_engine import FarmerProfile, recommend
from engine.price_pipeline import PricePipeline
from engine.weather_pipeline import WeatherPipeline


def run_engine_smoke() -> dict:
    farmer = FarmerProfile(
        mandal="nandipet",
        acres=10,
        water_source="mixed",
        loan_burden_rs=200000,
        last_crops=["paddy"],
        farmer_id="system-test-nandipet",
    )
    result = recommend(farmer)
    top = result["top_pick"]["crop"] if result["top_pick"] else None
    second = result["second_pick"]["crop"] if result["second_pick"] else None
    if top != "maize":
        raise AssertionError(f"Expected maize as top pick, got {top!r}")
    return {"top_pick": top, "second_pick": second}


def run_mandal_sweep() -> dict:
    tested = 0
    failures: list[dict] = []

    for mandal_slug, mandal_data in MANDALS.items():
        try:
            farmer = FarmerProfile(
                mandal=mandal_slug,
                acres=5,
                water_source=mandal_data["water"],
                farmer_id=f"mandal-sweep-{mandal_slug}",
            )
            recommend(farmer)
            tested += 1
        except Exception as exc:  # pragma: no cover - diagnostic path
            failures.append({"mandal": mandal_slug, "error": str(exc)})

    return {
        "tested": tested,
        "failures": failures,
    }


def run_route_checks() -> dict:
    with TestClient(app) as client:
        root = client.get("/")
        health = client.get("/health")
        dashboard = client.get("/dashboard")

    return {
        "root_status": root.status_code,
        "health_status": health.status_code,
        "dashboard_status": dashboard.status_code,
    }


def run_text_onboarding() -> dict:
    phone = "whatsapp:+919900000123"
    messages = [
        "reset",
        "nandipet",
        "10 acres",
        "deep calcareous mixed water",
        "last crop paddy, loan 2 lakh undi",
    ]
    replies: list[str] = []
    original_schedule = whatsapp_handler._maybe_schedule_voice_reply

    try:
        whatsapp_handler._maybe_schedule_voice_reply = lambda *args, **kwargs: None

        with TestClient(app) as client:
            for body in messages:
                response = client.post(
                    "/whatsapp",
                    data={"From": phone, "Body": body, "NumMedia": "0"},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                response.raise_for_status()
                replies.append(response.text)
    finally:
        whatsapp_handler._maybe_schedule_voice_reply = original_schedule

    final_reply = replies[-1]
    if "MAIZE" not in final_reply.upper():
        raise AssertionError("Expected final onboarding reply to contain maize recommendation.")

    return {"steps": len(messages), "final_contains_maize": True}


def run_price_weather_checks() -> dict:
    price_result = PricePipeline().run(persist=False)
    weather_result = WeatherPipeline().run(persist=False)
    return {
        "price_rows_prepared": price_result["rows_prepared"],
        "weather_hourly_rows_prepared": weather_result["hourly_rows_prepared"],
        "weather_daily_rows_prepared": weather_result["daily_rows_prepared"],
    }


def run_voice_smoke() -> dict:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "test_whatsapp_voice.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            "Voice smoke test failed.\n"
            f"stdout:\n{completed.stdout}\n\nstderr:\n{completed.stderr}"
        )
    return {"status": "ok"}


def run_followup_scenarios() -> dict:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "test_followup_scenarios.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            "Follow-up scenario test failed.\n"
            f"stdout:\n{completed.stdout}\n\nstderr:\n{completed.stderr}"
        )
    return {"status": "ok"}


def run_agronomy_services() -> dict:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "test_agronomy_services.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            "Agronomy service test failed.\n"
            f"stdout:\n{completed.stdout}\n\nstderr:\n{completed.stderr}"
        )
    return {"status": "ok"}


def main() -> None:
    summary = {
        "engine_smoke": run_engine_smoke(),
        "mandal_sweep": run_mandal_sweep(),
        "route_checks": run_route_checks(),
        "text_onboarding": run_text_onboarding(),
        "followup_scenarios": run_followup_scenarios(),
        "agronomy_services": run_agronomy_services(),
        "price_weather_checks": run_price_weather_checks(),
        "voice_smoke": run_voice_smoke(),
    }

    if summary["mandal_sweep"]["failures"]:
        raise AssertionError(json.dumps(summary["mandal_sweep"]["failures"], indent=2))

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
