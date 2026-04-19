"""Simple intent classification for WhatsApp text messages."""

from __future__ import annotations

import re

INTENTS = (
    "crop_recommendation",
    "disease_detection",
    "loan_help",
    "scheme_match",
    "weather_question",
    "unknown",
)

INTENT_KEYWORDS = {
    "crop_recommendation": [
        "crop", "recommend", "suggest", "analysis", "analyse", "price range",
        "emi veyali", "emi vesali", "best crop", "which crop",
    ],
    "disease_detection": [
        "disease", "tegulu", "machha", "spot", "rot", "worm", "pest", "photo", "image",
    ],
    "loan_help": [
        "loan", "appu", "debt", "waiver", "kcc",
    ],
    "scheme_match": [
        "scheme", "bandhu", "pm kisan", "bima", "subsidy", "yojana",
    ],
    "weather_question": [
        "weather", "varsham", "rain", "forecast", "temperature", "climate",
    ],
}


def classify_intent(message_text: str) -> str:
    """Return the most likely intent for a WhatsApp message."""

    normalized = re.sub(r"\s+", " ", message_text.lower()).strip()

    for intent, keywords in INTENT_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return intent
    return "unknown"
