"""Sarvam Telugu STT/TTS helpers for WhatsApp voice flow."""

from __future__ import annotations

import base64
import os
import re
import uuid
from pathlib import Path
from typing import Any

import requests


SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"
SARVAM_TRANSLITERATE_URL = "https://api.sarvam.ai/transliterate"
DEFAULT_STT_MODEL = "saaras:v3"
DEFAULT_STT_MODE = "translit"
DEFAULT_STT_LANGUAGE_CODE = "te-IN"
DEFAULT_TTS_MODEL = "bulbul:v3"
DEFAULT_TTS_SPEAKER = "manan"
DEFAULT_TTS_PACE = 0.9
DEFAULT_TTS_SAMPLE_RATE = 24000
GENERATED_AUDIO_DIR = Path("data/generated_audio")
MIME_EXTENSION_MAP = {
    "wav": "wav",
    "x-wav": "wav",
    "wave": "wav",
    "ogg": "ogg",
    "opus": "opus",
    "mpeg": "mp3",
    "mp3": "mp3",
    "aac": "aac",
    "x-aac": "aac",
    "webm": "webm",
    "mp4": "mp4",
    "x-m4a": "m4a",
    "m4a": "m4a",
}


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


def _sarvam_headers() -> dict[str, str]:
    _load_local_env()
    api_key = os.getenv("SARVAM_API_KEY") or os.getenv("SARVAM_KEY")
    if not api_key:
        raise RuntimeError("Sarvam API key missing.")
    return {"api-subscription-key": api_key}


def _normalize_text_for_speech(text: str) -> str:
    cleaned = text.replace("₹", "Rs ").replace("—", "-")
    cleaned = re.sub(r"\(([A-Z_ ]+)\)", "", cleaned)
    cleaned = cleaned.replace("BEST CHOICE", "Best choice")
    cleaned = cleaned.replace("SECOND OPTION", "Second option")
    cleaned = re.sub(r"\n+", ". ", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned


def transliterate_for_telugu_speech(text: str) -> str:
    """
    Convert the romanized Telugu reply into Telugu script before TTS.

    Sarvam transliteration supports English-to-Telugu script conversion and
    spoken-form numerals, which improves pronunciation for amounts and dates.
    """

    cleaned = _normalize_text_for_speech(text)
    if not cleaned:
        return cleaned
    if len(cleaned) > 1000:
        return cleaned

    payload = {
        "input": cleaned,
        "source_language_code": "en-IN",
        "target_language_code": "te-IN",
        "spoken_form": True,
        "spoken_form_numerals_language": "native",
    }
    response = requests.post(
        SARVAM_TRANSLITERATE_URL,
        headers={
            **_sarvam_headers(),
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=45,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("transliterated_text") or cleaned


def _normalized_mime_candidates(filename: str, mime_type: str | None) -> list[str | None]:
    candidates: list[str | None] = []

    def add(value: str | None) -> None:
        if value not in candidates:
            candidates.append(value)

    cleaned = (mime_type or "").split(";", 1)[0].strip().lower()
    if cleaned:
        add(cleaned)
        if "/" in cleaned:
            subtype = cleaned.split("/", 1)[1].strip()
            add(subtype)
            mapped = MIME_EXTENSION_MAP.get(subtype)
            if mapped:
                add(mapped)
            if subtype == "ogg":
                add("opus")
            if subtype == "opus":
                add("ogg")

    suffix = Path(filename).suffix.lower().lstrip(".")
    if suffix:
        add(suffix)
        mapped = MIME_EXTENSION_MAP.get(suffix)
        if mapped:
            add(mapped)

    add(None)
    return candidates


def _mode_candidates(requested_mode: str | None) -> list[str]:
    preferred = requested_mode or os.getenv("SARVAM_STT_MODE", DEFAULT_STT_MODE)
    modes = []
    for mode in (preferred, "translit", "transcribe", "codemix"):
        if mode and mode not in modes:
            modes.append(mode)
    return modes


def transcribe_voice_note(
    audio_bytes: bytes,
    *,
    filename: str = "voice_note.ogg",
    mime_type: str = "audio/ogg",
    language_code: str = DEFAULT_STT_LANGUAGE_CODE,
    model: str | None = None,
    mode: str | None = None,
) -> dict[str, Any]:
    """Convert a Telugu voice note into romanized text for the engine."""

    last_error: Exception | None = None
    last_empty_response: dict[str, Any] | None = None
    resolved_model = model or os.getenv("SARVAM_STT_MODEL", DEFAULT_STT_MODEL)

    for candidate_mode in _mode_candidates(mode):
        payload = {
            "model": resolved_model,
            "mode": candidate_mode,
            "language_code": language_code,
        }

        for candidate_mime in _normalized_mime_candidates(filename, mime_type):
            file_tuple: tuple[Any, ...]
            if candidate_mime:
                file_tuple = (filename, audio_bytes, candidate_mime)
            else:
                file_tuple = (filename, audio_bytes)

            try:
                response = requests.post(
                    SARVAM_STT_URL,
                    headers=_sarvam_headers(),
                    data=payload,
                    files={"file": file_tuple},
                    timeout=60,
                )
                response.raise_for_status()
                data = response.json()
                transcript = (data.get("transcript") or "").strip()
                if transcript:
                    return {
                        "request_id": data.get("request_id"),
                        "transcript": transcript,
                        "language_code": data.get("language_code"),
                        "language_probability": data.get("language_probability"),
                        "mode_used": candidate_mode,
                        "mime_type_used": candidate_mime,
                        "raw": data,
                    }
                last_empty_response = data
            except Exception as exc:
                last_error = exc

    if last_empty_response is not None:
        raise RuntimeError("Sarvam STT returned an empty transcript.")
    if last_error is not None:
        raise last_error
    raise RuntimeError("Sarvam STT failed without a specific error.")


def synthesize_telugu_reply(
    text: str,
    *,
    speaker: str | None = None,
    pace: float | None = None,
    target_language_code: str = "te-IN",
    model: str | None = None,
) -> dict[str, Any]:
    """Convert the engine output into a Telugu audio reply."""

    requested_speaker = (speaker or os.getenv("SARVAM_TTS_SPEAKER", DEFAULT_TTS_SPEAKER)).strip().lower()
    if requested_speaker == "maan":
        requested_speaker = "manan"

    script_text = transliterate_for_telugu_speech(text)
    payload = {
        "text": script_text,
        "target_language_code": target_language_code,
        "speaker": requested_speaker,
        "pace": pace if pace is not None else float(os.getenv("SARVAM_TTS_PACE", str(DEFAULT_TTS_PACE))),
        "speech_sample_rate": int(os.getenv("SARVAM_TTS_SAMPLE_RATE", str(DEFAULT_TTS_SAMPLE_RATE))),
        "model": model or os.getenv("SARVAM_TTS_MODEL", DEFAULT_TTS_MODEL),
    }

    response = requests.post(
        SARVAM_TTS_URL,
        headers={
            **_sarvam_headers(),
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    audios = data.get("audios") or []
    if not audios:
        raise RuntimeError("Sarvam TTS returned no audio payload.")

    audio_bytes = base64.b64decode(audios[0])
    return {
        "request_id": data.get("request_id"),
        "audio_bytes": audio_bytes,
        "content_type": "audio/wav",
        "extension": "wav",
        "speaker": requested_speaker,
        "script_text": script_text,
        "raw": data,
    }


def save_generated_audio(
    audio_bytes: bytes,
    *,
    extension: str = "wav",
    prefix: str = "reply",
) -> Path:
    """Persist a generated audio reply so Twilio can fetch it by URL."""

    GENERATED_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{prefix}_{uuid.uuid4().hex}.{extension.lstrip('.')}"
    path = GENERATED_AUDIO_DIR / filename
    path.write_bytes(audio_bytes)
    return path


def get_generated_audio_path(filename: str) -> Path:
    safe_name = Path(filename).name
    return GENERATED_AUDIO_DIR / safe_name
