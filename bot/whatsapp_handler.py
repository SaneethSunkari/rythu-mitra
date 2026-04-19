"""FastAPI WhatsApp webhook with progressive profiling and basic routing."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.parse import parse_qs
from xml.sax.saxutils import escape

import requests
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from twilio.rest import Client

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.farmer_profile import FarmerProfileManager
from bot.intent_classifier import classify_intent
from bot.telugu_voice import (
    get_generated_audio_path,
    save_generated_audio,
    synthesize_telugu_reply,
    transcribe_voice_note,
)
from data.nizamabad_district import SCHEMES
from engine.district_cap import DistrictCapTracker
from engine.crop_engine import (
    FarmerProfile as EngineFarmerProfile,
    generate_telugu_response,
    recommend,
)
from engine.weather_pipeline import WeatherPipeline


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


_load_local_env()

app = FastAPI(title="Rythu Mitra")
profile_manager = FarmerProfileManager()
district_cap_tracker = DistrictCapTracker()


@app.get("/")
async def root() -> dict:
    """Friendly root route for browser checks on Railway."""

    return {
        "status": "ok",
        "service": "rythu-mitra",
        "message": "Rythu Mitra webhook is live.",
        "health_url": "/health",
        "whatsapp_webhook": "/whatsapp",
    }


@app.get("/health")
async def health() -> dict:
    """Simple health route for local and Railway checks."""

    return {"status": "ok", "service": "rythu-mitra"}


@app.get("/media/{filename}")
async def media_file(filename: str) -> FileResponse:
    """Serve generated audio files for Twilio media fetches."""

    path = get_generated_audio_path(filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found.")
    return FileResponse(path, media_type="audio/wav", filename=path.name)


@app.post("/whatsapp")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks) -> Response:
    """Twilio webhook entrypoint."""

    raw_body = (await request.body()).decode("utf-8", errors="replace")
    parsed = parse_qs(raw_body, keep_blank_values=True)

    def first(key: str, default: str = "") -> str:
        values = parsed.get(key)
        if not values:
            return default
        return str(values[0])

    from_number = first("From").strip()
    message_text = first("Body").strip()
    num_media = int(first("NumMedia", "0") or 0)
    media_type = first("MediaContentType0").strip().lower()
    media_url = first("MediaUrl0").strip()
    public_base_url = (
        os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
        or str(request.base_url).rstrip("/")
    )

    if not from_number:
        return _twiml_message("Phone number kanapadaledu. Malli try cheyyandi.")

    if num_media > 0:
        if media_type.startswith("audio/"):
            try:
                audio_bytes = _download_twilio_media(media_url)
                transcript_result = transcribe_voice_note(
                    audio_bytes,
                    filename=_filename_from_media_url(media_url, media_type),
                    mime_type=media_type or "audio/ogg",
                )
                message_text = transcript_result["transcript"]
            except Exception:
                reply = (
                    "Mee voice note clear ga artham kaaledu naanna. "
                    "Malli konchem slow ga pampandi lekapothe text lo cheppandi."
                )
                _maybe_schedule_voice_reply(
                    background_tasks,
                    to_number=from_number,
                    reply_text=reply,
                    public_base_url=public_base_url,
                )
                return _twiml_message(reply)
        if media_type.startswith("image/"):
            return _twiml_message(
                "Photo diagnosis module inkem konchem pending lo undi. "
                "Ippatiki symptoms text lo cheppandi, urgent aithe KVK: 08462-226360."
            )

    reply = _process_farmer_text(from_number, message_text)
    _maybe_schedule_voice_reply(
        background_tasks,
        to_number=from_number,
        reply_text=reply,
        public_base_url=public_base_url,
    )
    return _twiml_message(reply)


def _process_farmer_text(from_number: str, message_text: str) -> str:
    conversation = profile_manager.handle_message(from_number, message_text)
    profile = conversation["profile"]

    if not profile.profile_complete:
        return conversation["reply"]

    if conversation.get("just_completed"):
        engine_farmer = EngineFarmerProfile(
            mandal=profile.mandal,
            acres=profile.acres,
            soil_zone=profile.soil_type,
            water_source=profile.water_source,
            loan_burden_rs=profile.loan_burden_rs,
            last_crops=profile.last_three_crops,
            farmer_id=profile.phone_number,
        )
        result = recommend(engine_farmer)
        _log_recommendation(engine_farmer, result)
        return generate_telugu_response(result)

    intent = classify_intent(message_text)

    if intent == "weather_question":
        return _weather_reply()

    if intent == "scheme_match" or intent == "loan_help":
        return _scheme_reply()

    if intent == "disease_detection":
        return (
            "Photo diagnosis module ippudu connect chesthunnanu. "
            "Clear leaf/photo pampandi ani taruvatha direct check chesthanu. "
            "Urgent aithe Nizamabad KVK: 08462-226360."
        )

    engine_farmer = EngineFarmerProfile(
        mandal=profile.mandal,
        acres=profile.acres,
        soil_zone=profile.soil_type,
        water_source=profile.water_source,
        loan_burden_rs=profile.loan_burden_rs,
        last_crops=profile.last_three_crops,
        farmer_id=profile.phone_number,
    )
    result = recommend(engine_farmer)
    _log_recommendation(engine_farmer, result)
    return generate_telugu_response(result)


def _weather_reply() -> str:
    try:
        summary = WeatherPipeline().run(persist=False)
        location = summary["location"]["name"]
        return (
            f"{location} forecast chusanu. "
            f"Next {summary['daily_rows_prepared']} rojula daily forecast ready undi, "
            f"hourly rain check kuda undi. "
            "Drying alerts and proactive disease warnings next ga connect chesthanu."
        )
    except Exception:
        return (
            "Weather fetch ippudu fail ayyindi. "
            "Konchem taruvatha malli adugandi, lekapothe local varsham situation cheppandi."
        )


def _scheme_reply() -> str:
    waiver = SCHEMES["crop_loan_waiver_2024"]
    kcc = SCHEMES["kisan_credit_card"]
    bandhu = SCHEMES["rythu_bandhu"]
    return (
        "Mee situation ki useful schemes ivvi:\n"
        f"1. {bandhu['telugu_name']} - {bandhu['amount']}\n"
        f"2. {waiver['telugu_name']} - {waiver['amount']}\n"
        f"3. {kcc['telugu_name']} - {kcc['interest_rate']}\n"
        "Avasaram aithe nenu eligible options short ga separate ga chepthanu."
    )


def _twiml_message(message: str) -> Response:
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<Response><Message>{escape(message)}</Message></Response>"
    )
    return Response(content=xml, media_type="application/xml")


def _download_twilio_media(media_url: str) -> bytes:
    if not media_url:
        raise ValueError("Missing MediaUrl0 for incoming audio.")

    sid = os.getenv("TWILIO_ACCOUNT_SID") or os.getenv("TWILIO_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN") or os.getenv("TWILIO_TOKEN")

    auth = (sid, token) if sid and token else None
    response = requests.get(media_url, auth=auth, timeout=45)
    response.raise_for_status()
    return response.content


def _filename_from_media_url(media_url: str, media_type: str) -> str:
    suffix = ".ogg"
    if "wav" in media_type:
        suffix = ".wav"
    elif "mpeg" in media_type or "mp3" in media_type:
        suffix = ".mp3"
    elif "webm" in media_type:
        suffix = ".webm"

    stem = Path(media_url.split("?", 1)[0]).name or "voice_note"
    if "." not in stem:
        stem = f"{stem}{suffix}"
    return stem


def _maybe_schedule_voice_reply(
    background_tasks: BackgroundTasks,
    *,
    to_number: str,
    reply_text: str,
    public_base_url: str,
) -> None:
    if not reply_text.strip():
        return
    background_tasks.add_task(
        _prepare_and_send_voice_reply,
        reply_text,
        to_number,
        public_base_url,
    )


def _prepare_and_send_voice_reply(reply_text: str, to_number: str, public_base_url: str) -> None:
    try:
        audio_result = synthesize_telugu_reply(reply_text)
        audio_path = save_generated_audio(
            audio_result["audio_bytes"],
            extension=audio_result["extension"],
        )
    except Exception:
        return

    if not _is_public_url(public_base_url):
        return

    try:
        twilio_number = os.getenv("TWILIO_WHATSAPP_NUMBER", "").strip()
        account_sid = os.getenv("TWILIO_ACCOUNT_SID") or os.getenv("TWILIO_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN") or os.getenv("TWILIO_TOKEN")
        if not twilio_number or not account_sid or not auth_token:
            return

        media_url = f"{public_base_url}/media/{audio_path.name}"
        client = Client(account_sid, auth_token)
        client.messages.create(
            from_=f"whatsapp:{twilio_number}",
            to=to_number,
            media_url=[media_url],
        )
    except Exception:
        return


def _is_public_url(url: str) -> bool:
    lower = url.lower()
    if not lower.startswith("http"):
        return False
    return all(host not in lower for host in ("localhost", "127.0.0.1", "testserver"))


def _log_recommendation(farmer: EngineFarmerProfile, result: dict) -> dict | None:
    top = result.get("top_pick")
    if not top:
        return None

    second = result.get("second_pick")
    return district_cap_tracker.record_recommendation(
        season=result["season"],
        farmer_key=farmer.build_farmer_key(),
        farmer_id=farmer.farmer_id,
        survey_number=farmer.survey_number,
        mandal=farmer.mandal,
        soil_zone=farmer.soil_zone,
        water_source=farmer.water_source,
        acres=farmer.acres,
        primary_crop=top["crop"],
        secondary_crop=second["crop"] if second else None,
        source="whatsapp",
    )


if __name__ == "__main__":
    example = profile_manager.handle_message("whatsapp:+911234567890", "nandipet 10 acres")
    print(json.dumps({"reply": example["reply"]}, ensure_ascii=False, indent=2))
