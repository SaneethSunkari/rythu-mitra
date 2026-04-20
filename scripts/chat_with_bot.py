"""Interactive local chat harness for the WhatsApp bot without Twilio."""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bot.whatsapp_handler as whatsapp_handler


def _extract_twiml_message(xml_text: str) -> str:
    start = xml_text.find("<Message>")
    end = xml_text.find("</Message>")
    if start == -1 or end == -1:
        return xml_text.strip()
    return xml_text[start + len("<Message>"):end].strip()


def _post_message(client: TestClient, phone: str, body: str) -> str:
    response = client.post(
        "/whatsapp",
        data={"From": phone, "Body": body, "NumMedia": "0"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    response.raise_for_status()
    return _extract_twiml_message(response.text)


def main() -> None:
    original_schedule = whatsapp_handler._maybe_schedule_voice_reply
    whatsapp_handler._maybe_schedule_voice_reply = lambda *args, **kwargs: None

    phone = f"whatsapp:+9199{uuid.uuid4().int % 100000000:08d}"
    print("Rythu Mitra local chat")
    print(f"Session phone: {phone}")
    print("Commands: /reset, /newphone, /quit")
    print("-" * 60)

    try:
        with TestClient(whatsapp_handler.app) as client:
            while True:
                try:
                    user_text = input("you> ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nbye")
                    break

                if not user_text:
                    continue

                if user_text == "/quit":
                    print("bye")
                    break

                if user_text == "/newphone":
                    phone = f"whatsapp:+9199{uuid.uuid4().int % 100000000:08d}"
                    print(f"bot> new session started with {phone}")
                    continue

                if user_text == "/reset":
                    reply = _post_message(client, phone, "reset")
                    print(f"bot> {reply}")
                    continue

                reply = _post_message(client, phone, user_text)
                print(f"bot> {reply}")
    finally:
        whatsapp_handler._maybe_schedule_voice_reply = original_schedule


if __name__ == "__main__":
    main()
