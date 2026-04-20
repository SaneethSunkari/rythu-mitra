"""Verify season calendar, scheduled alerts, drying alerts, and disease inference."""

from __future__ import annotations

import io
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bot.whatsapp_handler as whatsapp_handler
from bot.crop_cycle_service import CropCycleService
from bot.drying_alerts import DryingAlertService
from bot.proactive_monitor import ProactiveMonitor
from bot.whatsapp_handler import app
from disease.inference import diagnose_disease_image
from engine.season_calendar import SeasonCalendar


def _make_image_bytes(size: tuple[int, int] = (256, 256), *, patterned: bool = True) -> bytes:
    from PIL import Image, ImageDraw

    image = Image.new("RGB", size, color=(120, 160, 90))
    if patterned:
        draw = ImageDraw.Draw(image)
        for index in range(0, size[0], 16):
            draw.line((index, 0, size[0] - index // 2, size[1]), fill=(40, 90, 30), width=3)
        draw.ellipse((70, 70, 180, 180), outline=(200, 200, 80), width=4)

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def run_calendar_checks() -> dict:
    calendar = SeasonCalendar().build("maize", "2026-06-20")
    event_titles = [event["title"] for event in calendar["events"]]
    assert "Harvest window opens" in event_titles
    assert any("Monitoring check" in title for title in event_titles)
    assert any(event["type"] == "fertilizer" for event in calendar["events"])
    return {"events": len(calendar["events"])}


def run_cycle_service_checks() -> dict:
    with tempfile.TemporaryDirectory() as temp_dir:
        service = CropCycleService(store_path=Path(temp_dir) / "crop_cycles.json")
        payload = service.set_sowing(
            "whatsapp:+910000000001",
            crop_name="maize",
            sowing_date="2026-06-20",
        )
        preview = service.preview_alerts(
            "whatsapp:+910000000001",
            now=datetime(2026, 7, 10, 8, 0, 0),
        )
        due = service.collect_due_alerts(now=datetime(2026, 7, 10, 8, 0, 0))

    assert payload["calendar"]["crop"] == "maize"
    assert preview["upcoming_events"]
    assert any(item["alert_type"] == "season_calendar" for item in due)
    return {"due_alerts": len(due)}


def run_proactive_monitor_checks() -> dict:
    monitor = ProactiveMonitor()
    hourly_rows = [
        {
            "forecast_time": f"2026-08-20T{hour:02d}:00",
            "relative_humidity_2m_pct": 95,
            "cloud_cover_pct": 82,
            "precipitation_probability_pct": 48,
        }
        for hour in range(48)
    ]
    daily_rows = [
        {
            "forecast_date": "2026-08-20",
            "precipitation_sum_mm": 18,
            "precipitation_probability_max_pct": 76,
        }
    ]
    alerts = monitor.evaluate(
        crop_name="paddy",
        sowing_date="2026-08-10",
        weather_hourly_rows=hourly_rows,
        weather_daily_rows=daily_rows,
        today="2026-08-20",
    )
    assert any(alert["type"] == "proactive_disease_alert" for alert in alerts)
    assert any(alert["type"] == "monitoring_reminder" for alert in alerts)
    return {"alerts": len(alerts)}


def run_drying_checks() -> dict:
    service = DryingAlertService()
    hourly_rows = [
        {
            "forecast_time": "2026-10-20T06:00:00",
            "precipitation_probability_pct": 20,
        },
        {
            "forecast_time": "2026-10-20T07:00:00",
            "precipitation_probability_pct": 64,
        },
        {
            "forecast_time": "2026-10-20T08:00:00",
            "precipitation_probability_pct": 72,
        },
        {
            "forecast_time": "2026-10-20T09:00:00",
            "precipitation_probability_pct": 50,
        },
    ]
    daily_rows = [
        {
            "forecast_date": "2026-10-20",
            "precipitation_probability_max_pct": 78,
            "precipitation_sum_mm": 13,
        }
    ]
    alerts = service.evaluate(
        drying_start="2026-10-19",
        now="2026-10-20T06:30:00",
        hourly_rows=hourly_rows,
        daily_rows=daily_rows,
    )
    night_alerts = service.evaluate(
        drying_start="2026-10-19",
        now="2026-10-20T18:30:00",
        hourly_rows=hourly_rows,
        daily_rows=daily_rows,
    )
    alert_types = {alert["type"] for alert in alerts}
    night_types = {alert["type"] for alert in night_alerts}
    assert "drying_rain_alert" in alert_types
    assert "drying_day_summary" in alert_types
    assert "drying_three_hour_watch" in alert_types
    assert "drying_night_summary" in night_types
    return {"alerts": len(alerts), "night_alerts": len(night_alerts)}


def run_disease_inference_checks() -> dict:
    blurry_bytes = _make_image_bytes(size=(96, 96), patterned=False)
    poor_quality = diagnose_disease_image(blurry_bytes, crop_hint="paddy")
    assert poor_quality["tier"] == "poor_quality"

    class FakeModel:
        def predict(self, image_bytes: bytes, *, crop_hint: str | None = None) -> dict:
            del image_bytes, crop_hint
            return {
                "status": "predicted",
                "confidence": 0.92,
                "predicted_label": "paddy_blast",
                "quality": {"usable": True},
            }

    definitive = diagnose_disease_image(_make_image_bytes(), crop_hint="paddy", model=FakeModel())
    assert definitive["tier"] == "definitive"

    class FakeCaveatModel:
        def predict(self, image_bytes: bytes, *, crop_hint: str | None = None) -> dict:
            del image_bytes, crop_hint
            return {
                "status": "predicted",
                "confidence": 0.66,
                "predicted_label": "maize_fall_army_worm",
                "quality": {"usable": True},
            }

    caveat = diagnose_disease_image(_make_image_bytes(), crop_hint="maize", model=FakeCaveatModel())
    assert caveat["tier"] == "caveat"
    return {
        "poor_quality": poor_quality["tier"],
        "definitive": definitive["tier"],
        "caveat": caveat["tier"],
    }


def run_image_webhook_check() -> dict:
    original_download = whatsapp_handler._download_twilio_media
    original_diagnose = whatsapp_handler.diagnose_disease_image
    original_schedule = whatsapp_handler._maybe_schedule_voice_reply
    phone = "whatsapp:+919900000456"

    try:
        whatsapp_handler._download_twilio_media = lambda url: (_make_image_bytes(), "image/jpeg")
        whatsapp_handler.diagnose_disease_image = lambda image_bytes, crop_hint=None: {
            "reply_text": "Naanna, photo batti caveat reply vachhindi."
        }
        whatsapp_handler._maybe_schedule_voice_reply = lambda *args, **kwargs: None

        with TestClient(app) as client:
            response = client.post(
                "/whatsapp",
                data={
                    "From": phone,
                    "Body": "paddy photo",
                    "NumMedia": "1",
                    "MediaUrl0": "https://example.com/fake.jpg",
                    "MediaContentType0": "image/jpeg",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
    finally:
        whatsapp_handler._download_twilio_media = original_download
        whatsapp_handler.diagnose_disease_image = original_diagnose
        whatsapp_handler._maybe_schedule_voice_reply = original_schedule

    assert "caveat reply" in response.text
    return {"status": "ok"}


def main() -> None:
    summary = {
        "calendar": run_calendar_checks(),
        "cycle_service": run_cycle_service_checks(),
        "proactive_monitor": run_proactive_monitor_checks(),
        "drying_alerts": run_drying_checks(),
        "disease_inference": run_disease_inference_checks(),
        "image_webhook": run_image_webhook_check(),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
