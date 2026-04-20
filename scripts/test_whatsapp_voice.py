"""Local smoke test for the WhatsApp voice-in -> voice-out flow."""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bot.whatsapp_handler as whatsapp_handler
from bot.telugu_voice import save_generated_audio


VOICE_STEPS = [
    "nandipet",
    "10 acres",
    "deep calcareous mixed water",
    "last crop paddy. loan two lakh undi",
]


def _extract_twiml_message(xml_text: str) -> str:
    start = xml_text.find("<Message>")
    end = xml_text.find("</Message>")
    if start == -1 or end == -1:
        return xml_text.strip()
    return xml_text[start + len("<Message>"):end].strip()


def main() -> None:
    media_store: dict[str, tuple[bytes, str]] = {}
    transcript_store: dict[str, str] = {}

    for index, text in enumerate(VOICE_STEPS, start=1):
        media_store[f"https://voice.test/{index}.wav"] = (
            b"voice-bytes",
            "audio/wav",
        )
        transcript_store[f"{index}.wav"] = text

    original_download = whatsapp_handler._download_twilio_media
    original_schedule = whatsapp_handler._maybe_schedule_voice_reply
    original_transcribe = whatsapp_handler.transcribe_voice_note
    whatsapp_handler._download_twilio_media = media_store.__getitem__

    def _local_voice_reply(_background_tasks, *, reply_text: str, public_base_url: str, to_number: str) -> None:
        del reply_text, public_base_url, to_number
        save_generated_audio(b"fake-audio-reply", extension="mp3")

    def _mock_transcribe(_audio_bytes: bytes, *, filename: str, mime_type: str) -> dict:
        return {
            "transcript": transcript_store[filename],
            "mime_type_used": mime_type,
            "mode_used": "mock",
        }

    whatsapp_handler._maybe_schedule_voice_reply = _local_voice_reply
    whatsapp_handler.transcribe_voice_note = _mock_transcribe

    phone_number = f"whatsapp:+9199{uuid.uuid4().int % 100000000:08d}"
    reply_dir = Path("data/generated_audio")
    reply_dir.mkdir(parents=True, exist_ok=True)
    before_files = set(reply_dir.glob("reply_*.wav")) | set(reply_dir.glob("reply_*.mp3"))

    try:
        client = TestClient(whatsapp_handler.app)

        final_reply = ""
        for index in range(1, len(VOICE_STEPS) + 1):
            response = client.post(
                "/whatsapp",
                data={
                    "From": phone_number,
                    "Body": "",
                    "NumMedia": "1",
                    "MediaUrl0": f"https://voice.test/{index}.wav",
                    "MediaContentType0": "audio/wav",
                },
            )
            if response.status_code != 200:
                raise RuntimeError(
                    f"Webhook failed on step {index} with status {response.status_code}: {response.text}"
                )
            final_reply = _extract_twiml_message(response.text)
            print(f"step_{index}: {final_reply[:180]}")

        after_files = set(reply_dir.glob("reply_*.wav")) | set(reply_dir.glob("reply_*.mp3"))
        new_files = sorted(after_files - before_files)

        if "maize" not in final_reply.lower():
            raise RuntimeError(f"Final recommendation did not mention maize: {final_reply}")
        if not new_files:
            raise RuntimeError("No Telugu reply audio file was generated.")

        print(f"generated_reply_files: {len(new_files)}")
        print(f"latest_reply_audio: {new_files[-1]}")
        print("voice_flow_status: ok")
    finally:
        whatsapp_handler._download_twilio_media = original_download
        whatsapp_handler._maybe_schedule_voice_reply = original_schedule
        whatsapp_handler.transcribe_voice_note = original_transcribe


if __name__ == "__main__":
    main()
