"""Local smoke test for the WhatsApp voice-in -> voice-out flow."""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bot.whatsapp_handler as whatsapp_handler
from bot.telugu_voice import synthesize_telugu_reply


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
    media_store: dict[str, bytes] = {}

    for index, text in enumerate(VOICE_STEPS, start=1):
        audio = synthesize_telugu_reply(text, speaker="maan", pace=0.9)
        media_store[f"https://voice.test/{index}.wav"] = audio["audio_bytes"]

    original_download = whatsapp_handler._download_twilio_media
    whatsapp_handler._download_twilio_media = media_store.__getitem__

    phone_number = f"whatsapp:+9199{uuid.uuid4().int % 100000000:08d}"
    reply_dir = Path("data/generated_audio")
    reply_dir.mkdir(parents=True, exist_ok=True)
    before_files = set(reply_dir.glob("reply_*.wav"))

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

        after_files = set(reply_dir.glob("reply_*.wav"))
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


if __name__ == "__main__":
    main()
