"""FastAPI WhatsApp webhook with progressive profiling and basic routing."""

from __future__ import annotations

import json
import logging
import mimetypes
import os
import sys
from pathlib import Path
from urllib.parse import parse_qs
from xml.sax.saxutils import escape

import requests
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from twilio.rest import Client

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.crop_cycle_service import CropCycleService
from bot.farmer_profile import FarmerProfileManager
from bot.intent_classifier import classify_intent
from bot.scenario_logic import maybe_handle_followup
from bot.telugu_voice import (
    get_generated_audio_path,
    save_generated_audio,
    synthesize_telugu_reply,
    transcribe_voice_note,
)
from disease.inference import diagnose_disease_image
from data.nizamabad_district import CROPS, SCHEMES
from engine.dashboard_payload import (
    build_dashboard_analysis,
    build_markets_context,
    build_site_context,
)
from engine.district_cap import DistrictCapTracker
from engine.crop_engine import (
    FarmerProfile as EngineFarmerProfile,
    generate_telugu_response,
    recommend,
)
from engine.soil_lookup import lookup_survey_context
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
crop_cycle_service = CropCycleService()
logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent.parent
DASHBOARD_DIST_DIR = ROOT / "dashboard" / "dist"
DASHBOARD_INDEX = DASHBOARD_DIST_DIR / "index.html"
DASHBOARD_ASSETS_DIR = DASHBOARD_DIST_DIR / "assets"
DASHBOARD_ROOT_PUBLIC_FILES = {
    "googlec7fc4384607f1c4e.html": "text/html",
    "robots.txt": "text/plain",
    "sitemap.xml": "application/xml",
    "site.webmanifest": "application/manifest+json",
    "website-preview.svg": "image/svg+xml",
}


class DashboardAnalyzeRequest(BaseModel):
    mandal: str
    acres: float = Field(default=5, ge=0.5, le=1000)
    soilZone: str | None = None
    waterSource: str | None = None
    loanBurdenRs: int = Field(default=0, ge=0)
    lastCrops: list[str] = Field(default_factory=list)
    surveyNumber: str | None = None

if DASHBOARD_ASSETS_DIR.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=str(DASHBOARD_ASSETS_DIR)),
        name="assets",
    )
    app.mount(
        "/dashboard/assets",
        StaticFiles(directory=str(DASHBOARD_ASSETS_DIR)),
        name="dashboard-assets",
    )


@app.get("/", response_model=None)
async def root() -> Response:
    """Serve the public website from the root URL when the frontend build exists."""

    if DASHBOARD_INDEX.exists():
        return FileResponse(DASHBOARD_INDEX, media_type="text/html")

    return JSONResponse(
        {
        "status": "ok",
        "service": "rythu-mitra",
        "message": "Rythu Mitra website build not found yet.",
        "health_url": "/health",
        "whatsapp_webhook": "/whatsapp",
        "website_url": "/dashboard",
        }
    )


@app.get("/status")
async def status() -> dict:
    """JSON status route for browser or deployment checks."""

    return {
        "status": "ok",
        "service": "rythu-mitra",
        "health_url": "/health",
        "whatsapp_webhook": "/whatsapp",
        "website_url": "/",
        "dashboard_alias": "/dashboard",
    }


for public_filename, media_type in DASHBOARD_ROOT_PUBLIC_FILES.items():
    async def _serve_dashboard_public_file(
        filename: str = public_filename,
        resolved_media_type: str = media_type,
    ) -> FileResponse:
        path = DASHBOARD_DIST_DIR / filename
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"{filename} not found.")
        return FileResponse(path, media_type=resolved_media_type, filename=filename)

    app.add_api_route(f"/{public_filename}", _serve_dashboard_public_file, methods=["GET"])


@app.get("/health")
async def health() -> dict:
    """Simple health route for local and Railway checks."""

    return {"status": "ok", "service": "rythu-mitra"}


@app.post("/api/dashboard/analyze")
async def dashboard_analyze(payload: DashboardAnalyzeRequest) -> dict:
    """Run a live dashboard analysis against the real crop engine."""

    try:
        mandal = payload.mandal.strip().lower()
        soil_zone = payload.soilZone.strip().lower() if payload.soilZone else None
        water_source = payload.waterSource.strip().lower() if payload.waterSource else None
        survey_context = lookup_survey_context(mandal, payload.surveyNumber)
        default_soil = EngineFarmerProfile(mandal=mandal, acres=1).soil_zone
        default_water = EngineFarmerProfile(mandal=mandal, acres=1).water_source
        if survey_context:
            if not soil_zone or soil_zone == default_soil:
                soil_zone = survey_context.get("soilZone") or soil_zone
            if not water_source or water_source == default_water:
                water_source = survey_context.get("waterSource") or water_source
        last_crops = [
            item.strip().lower().replace(" ", "_")
            for item in payload.lastCrops
            if item and item.strip()
        ]
        farmer = EngineFarmerProfile(
            mandal=mandal,
            acres=float(payload.acres),
            soil_zone=soil_zone,
            water_source=water_source,
            loan_burden_rs=int(payload.loanBurdenRs),
            last_crops=last_crops,
            farmer_id="dashboard-live",
            survey_number=payload.surveyNumber,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return build_dashboard_analysis(farmer, soil_context=survey_context)


@app.get("/api/site/context")
async def site_context() -> dict:
    """Return live website payload with backend market/weather context."""

    return build_site_context()


@app.get("/api/markets/context")
async def markets_context() -> dict:
    """Return the heavy live market context only for the markets surface."""

    return build_markets_context()


@app.get("/dashboard")
@app.get("/dashboard/")
async def dashboard_index() -> FileResponse:
    """Serve the built dashboard shell when present."""

    if not DASHBOARD_INDEX.exists():
        raise HTTPException(status_code=404, detail="Dashboard build not found.")
    return FileResponse(DASHBOARD_INDEX, media_type="text/html")


@app.get("/dashboard/{path:path}")
async def dashboard_spa(path: str) -> FileResponse:
    """Fallback dashboard routes back to the SPA index for client-side navigation."""

    if not DASHBOARD_INDEX.exists():
        raise HTTPException(status_code=404, detail="Dashboard build not found.")

    requested_path = (DASHBOARD_DIST_DIR / path).resolve()
    if requested_path.is_file() and DASHBOARD_DIST_DIR in requested_path.parents:
        guessed_type, _ = mimetypes.guess_type(requested_path.name)
        return FileResponse(
            requested_path,
            media_type=guessed_type or "application/octet-stream",
            filename=requested_path.name,
        )

    return FileResponse(DASHBOARD_INDEX, media_type="text/html")


@app.get("/media/{filename}")
async def media_file(filename: str) -> FileResponse:
    """Serve generated audio files for Twilio media fetches."""

    path = get_generated_audio_path(filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found.")
    guessed_type, _ = mimetypes.guess_type(path.name)
    return FileResponse(path, media_type=guessed_type or "application/octet-stream", filename=path.name)


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
        if media_type.startswith("audio/") or media_type in {"application/ogg", "application/octet-stream"}:
            try:
                audio_bytes, downloaded_media_type = _download_twilio_media(media_url)
                transcript_result = transcribe_voice_note(
                    audio_bytes,
                    filename=_filename_from_media_url(media_url, media_type),
                    mime_type=downloaded_media_type or media_type or "audio/ogg",
                )
                message_text = transcript_result["transcript"]
            except Exception:
                logger.exception(
                    "Voice transcription failed for WhatsApp media. media_type=%s media_url_present=%s",
                    media_type,
                    bool(media_url),
                )
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
            try:
                image_bytes, _ = _download_twilio_media(media_url)
                profile = profile_manager.get_profile(from_number)
                cycle_state = crop_cycle_service.get_state(from_number)
                crop_hint = cycle_state.crop_name or (profile.last_three_crops[0] if profile.last_three_crops else None)
                diagnosis = diagnose_disease_image(image_bytes, crop_hint=crop_hint)
                reply = diagnosis["reply_text"]
            except Exception:
                logger.exception(
                    "Image diagnosis failed for WhatsApp media. media_type=%s media_url_present=%s",
                    media_type,
                    bool(media_url),
                )
                reply = (
                    "Photo process cheyyadam ippudu fail ayyindi naanna. "
                    "Malli clear daylight photo pampandi lekapothe KVK 08462-226360 ki chupinchandi."
                )
            _maybe_schedule_voice_reply(
                background_tasks,
                to_number=from_number,
                reply_text=reply,
                public_base_url=public_base_url,
            )
            return _twiml_message(reply)

    reply = _process_farmer_text(from_number, message_text)
    _maybe_schedule_voice_reply(
        background_tasks,
        to_number=from_number,
        reply_text=reply,
        public_base_url=public_base_url,
    )
    return _twiml_message(reply)


def _process_farmer_text(from_number: str, message_text: str) -> str:
    normalized = " ".join(message_text.lower().split())
    reset_requested = any(
        phrase in normalized
        for phrase in ("reset", "restart", "new profile", "change profile", "start over")
    )
    if reset_requested:
        profile_manager.reset_profile(from_number)
        crop_cycle_service.clear_state(from_number)
        return (
            "Sare naanna, old profile clear chesanu. "
            "Malli fresh ga start cheddam. Mundu mee mandal cheppandi."
        )

    existing_profile = profile_manager.get_profile(from_number)
    force_overwrite = (
        existing_profile.profile_complete
        and profile_manager.message_contains_profile_update_signal(message_text)
    )

    if existing_profile.profile_complete and not force_overwrite:
        followup_reply = maybe_handle_followup(existing_profile, message_text)
        if followup_reply:
            return followup_reply

        intent = classify_intent(message_text)

        if intent == "weather_question":
            return _weather_reply()

        if intent == "scheme_match" or intent == "loan_help":
            return _scheme_reply()

        if intent == "disease_detection":
            return (
                "Clear leaf/photo pampandi naanna. "
                "Photo quality bagunte confidence-threshold batti reply istanu. "
                "Urgent aithe Nizamabad KVK: 08462-226360."
            )

        if intent == "unknown":
            engine_farmer = EngineFarmerProfile(
                mandal=existing_profile.mandal,
                acres=existing_profile.acres,
                soil_zone=existing_profile.soil_type,
                water_source=existing_profile.water_source,
                loan_burden_rs=existing_profile.loan_burden_rs,
                last_crops=existing_profile.last_three_crops,
                farmer_id=existing_profile.phone_number,
            )
            result = recommend(engine_farmer)
            top = result.get("top_pick")
            top_name = CROPS[top["crop"]].get("telugu_name", top["crop"]) if top else "clear shortlist"
            return (
                "Mee profile already na daggara undi naanna. "
                f"Ippudu naa shortlist lo {top_name} undi. "
                "Meeru ila adagochu: 'paddy enduku vaddu', 'takkuva risk option cheppu', "
                "'vere crop suggest cheyyu', 'maize mariyu soybean lo yedi better', "
                "lekapothe kotha details cheppandi."
            )

        engine_farmer = EngineFarmerProfile(
            mandal=existing_profile.mandal,
            acres=existing_profile.acres,
            soil_zone=existing_profile.soil_type,
            water_source=existing_profile.water_source,
            loan_burden_rs=existing_profile.loan_burden_rs,
            last_crops=existing_profile.last_three_crops,
            farmer_id=existing_profile.phone_number,
        )
        result = recommend(engine_farmer)
        _log_recommendation(engine_farmer, result)
        return generate_telugu_response(result)

    conversation = profile_manager.handle_message(
        from_number,
        message_text,
        force_overwrite=force_overwrite,
    )
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

    if force_overwrite:
        followup_reply = maybe_handle_followup(profile, message_text)
        if followup_reply:
            return followup_reply

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
        return (
            "Mee profile update chesanu naanna. Kotha details batti malli analyse chesanu.\n\n"
            f"{generate_telugu_response(result)}"
        )

    intent = classify_intent(message_text)

    if intent == "weather_question":
        return _weather_reply()

    if intent == "scheme_match" or intent == "loan_help":
        return _scheme_reply()

    if intent == "disease_detection":
        return (
            "Clear leaf/photo pampandi naanna. "
            "Photo quality bagunte confidence-threshold batti reply istanu. "
            "Urgent aithe Nizamabad KVK: 08462-226360."
        )

    if intent == "unknown":
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
        top = result.get("top_pick")
        top_name = CROPS[top["crop"]].get("telugu_name", top["crop"]) if top else "clear shortlist"
        return (
            "Mee profile already na daggara undi naanna. "
            f"Ippudu naa shortlist lo {top_name} undi. "
            "Meeru ila adagochu: 'paddy enduku vaddu', 'takkuva risk option cheppu', "
            "'vere crop suggest cheyyu', 'maize mariyu soybean lo yedi better', "
            "lekapothe kotha details cheppandi."
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
            "Drying watch mariyu proactive disease warnings kuda evaluate cheyyachu."
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


def _download_twilio_media(media_url: str) -> tuple[bytes, str]:
    if not media_url:
        raise ValueError("Missing MediaUrl0 for incoming audio.")

    sid = _extract_account_sid_from_media_url(media_url) or os.getenv("TWILIO_ACCOUNT_SID") or os.getenv("TWILIO_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN") or os.getenv("TWILIO_TOKEN")

    auth = (sid, token) if sid and token else None
    response = requests.get(media_url, auth=auth, timeout=45)
    response.raise_for_status()
    return response.content, response.headers.get("Content-Type", "")


def _extract_account_sid_from_media_url(media_url: str) -> str:
    marker = "/Accounts/"
    if marker not in media_url:
        return ""
    tail = media_url.split(marker, 1)[1]
    sid = tail.split("/", 1)[0].strip()
    if sid.startswith("AC") and len(sid) == 34:
        return sid
    return ""


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
