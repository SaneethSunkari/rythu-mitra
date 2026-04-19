"""Progressive farmer profile collection and persistence."""

from __future__ import annotations

import json
import os
import re
from difflib import SequenceMatcher
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

from data.nizamabad_district import CROPS, MANDALS


SOIL_ALIASES = {
    "black cotton": "black_cotton",
    "black": "black_cotton",
    "nalla": "black_cotton",
    "deep calcareous": "deep_calcareous",
    "calcareous": "deep_calcareous",
    "red clayey": "red_clayey",
    "red": "red_clayey",
    "erra": "red_clayey",
    "mixed": "mixed",
    "mishram": "mixed",
}

WATER_ALIASES = {
    "canal": "canal",
    "project": "canal",
    "rainfed": "rainfed",
    "varsham": "rainfed",
    "bore": "borewell",
    "borewell": "borewell",
    "mixed": "mixed",
}

CROP_ALIASES = {
    "paddy": "paddy",
    "paadi": "paddy",
    "vari": "paddy",
    "rice": "paddy",
    "turmeric": "turmeric",
    "pasupu": "turmeric",
    "maize": "maize",
    "corn": "maize",
    "mokkajonna": "maize",
    "soybean": "soybean",
    "soyabean": "soybean",
    "cotton": "cotton",
    "patthi": "cotton",
    "patti": "cotton",
    "red gram": "red_gram",
    "kandulu": "red_gram",
    "tur": "red_gram",
    "sunflower": "sunflower",
    "green gram": "green_gram",
    "pesalu": "green_gram",
    "sugarcane": "sugarcane",
    "cheruku": "sugarcane",
}

NUMBER_WORDS = {
    "zero": 0,
    "no": 0,
    "one": 1,
    "oka": 1,
    "okati": 1,
    "two": 2,
    "rendu": 2,
    "three": 3,
    "moodu": 3,
    "mudu": 3,
    "four": 4,
    "nalugu": 4,
    "naalugu": 4,
    "five": 5,
    "aidu": 5,
    "aydu": 5,
    "six": 6,
    "aaru": 6,
    "aru": 6,
    "seven": 7,
    "eedu": 7,
    "edu": 7,
    "eight": 8,
    "enimidi": 8,
    "enimidhi": 8,
    "nine": 9,
    "tommidi": 9,
    "thommidi": 9,
    "ten": 10,
    "padi": 10,
    "padhi": 10,
    "adi": 10,
    "adhi": 10,
    "eleven": 11,
    "padakondu": 11,
    "twelve": 12,
    "pannendu": 12,
    "thirteen": 13,
    "padamoodu": 13,
    "fourteen": 14,
    "padnalugu": 14,
    "fifteen": 15,
    "padihenu": 15,
    "sixteen": 16,
    "padaharu": 16,
    "seventeen": 17,
    "padihedu": 17,
    "eighteen": 18,
    "paddenimidi": 18,
    "nineteen": 19,
    "pantommidi": 19,
    "twenty": 20,
    "iravai": 20,
    "iruvai": 20,
    "thirty": 30,
    "muppai": 30,
    "forty": 40,
    "nalabhai": 40,
    "fifty": 50,
    "yaabhai": 50,
    "yabhai": 50,
    "sixty": 60,
    "aravai": 60,
    "seventy": 70,
    "debbai": 70,
    "eighty": 80,
    "enabhai": 80,
    "ninety": 90,
    "tombhai": 90,
    "thombhai": 90,
}

MULTIPLIER_WORDS = {
    "hundred": 100,
    "vanda": 100,
    "vandalu": 100,
    "vandala": 100,
    "thousand": 1000,
    "vela": 1000,
    "vela": 1000,
    "veyyi": 1000,
    "lakh": 100000,
    "lakhs": 100000,
    "laksh": 100000,
    "laksha": 100000,
    "lakshalu": 100000,
    "lakshala": 100000,
    "crore": 10000000,
    "crores": 10000000,
    "koti": 10000000,
    "kotlu": 10000000,
}

ACRE_UNITS = {"acre", "acres", "ekar", "ekara", "ekarlu", "ekaralu"}
LOAN_KEYWORDS = {"loan", "appu", "debt", "borrowing"}
ACRE_BLOCKLIST = {
    "loan",
    "appu",
    "laksh",
    "laksha",
    "lakh",
    "crop",
    "crops",
    "paddy",
    "paadi",
    "soil",
    "water",
    "mandal",
}
NUMBER_NOISE_WORDS = {
    "undi",
    "unna",
    "naanna",
    "nanna",
    "about",
    "around",
    "approx",
    "nearly",
    "only",
    "just",
    "ki",
    "ku",
    "meeku",
    "naa",
    "na",
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


def _resolve_supabase_key(explicit_key: str | None = None) -> str:
    if explicit_key:
        return explicit_key
    return (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        or os.getenv("SUPABASE_KEY", "")
        or os.getenv("SUPABASE_ANON_KEY", "")
    )


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    lowered = value.lower().strip()
    lowered = re.sub(r"[^a-z0-9\s.]", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def _tokenize_words(value: str) -> list[str]:
    return [token for token in value.split() if token]


def _parse_number_tokens(tokens: list[str]) -> int | None:
    total = 0
    current = 0
    seen = False

    for token in tokens:
        if token in NUMBER_NOISE_WORDS:
            continue

        if token.isdigit():
            current += int(token)
            seen = True
            continue

        if token in NUMBER_WORDS:
            current += NUMBER_WORDS[token]
            seen = True
            continue

        multiplier = MULTIPLIER_WORDS.get(token)
        if multiplier == 100:
            current = max(current, 1) * multiplier
            seen = True
            continue
        if multiplier and multiplier >= 1000:
            total += max(current, 1) * multiplier
            current = 0
            seen = True
            continue

        if seen:
            break

    if not seen:
        return None
    return total + current


def _parse_number_phrase(value: str) -> int | None:
    return _parse_number_tokens(_tokenize_words(value))


@dataclass
class FarmerProfile:
    phone_number: str
    mandal: str | None = None
    acres: float | None = None
    soil_type: str | None = None
    water_source: str | None = None
    last_three_crops: list[str] = field(default_factory=list)
    loan_situation: str | None = None
    loan_burden_rs: int = 0
    profile_stage: str = "mandal"
    profile_complete: bool = False
    created_at_utc: str | None = None
    updated_at_utc: str | None = None

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        if not self.created_at_utc:
            record["created_at_utc"] = datetime.now(timezone.utc).isoformat()
        record["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
        return record


class FarmerProfileManager:
    """Collect profile details across a few messages and persist them."""

    _memory_store: dict[str, FarmerProfile] = {}

    def __init__(
        self,
        supabase_url: str | None = None,
        supabase_key: str | None = None,
        table_name: str = "farmer_profiles",
        timeout_seconds: int = 20,
    ) -> None:
        _load_local_env()

        self.supabase_url = (supabase_url or os.getenv("SUPABASE_URL", "")).rstrip("/")
        self.supabase_key = _resolve_supabase_key(supabase_key)
        self.table_name = table_name
        self.timeout_seconds = timeout_seconds

    def get_profile(self, phone_number: str) -> FarmerProfile:
        if phone_number in self._memory_store:
            return self._memory_store[phone_number]

        profile = self._fetch_from_supabase(phone_number)
        if profile:
            self._memory_store[phone_number] = profile
            return profile

        profile = FarmerProfile(phone_number=phone_number)
        self._memory_store[phone_number] = profile
        return profile

    def save_profile(self, profile: FarmerProfile) -> dict[str, Any]:
        self._memory_store[profile.phone_number] = profile

        if not self.supabase_url or not self.supabase_key:
            return {"stored": False, "warning": "Supabase credentials missing; profile kept in memory."}

        endpoint = f"{self.supabase_url}/rest/v1/{self.table_name}?on_conflict=phone_number"
        payload = json.dumps([profile.to_record()]).encode("utf-8")
        req = request.Request(
            endpoint,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}",
                "Prefer": "resolution=merge-duplicates,return=representation",
            },
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                response.read()
            return {"stored": True}
        except error.HTTPError as exc:
            return {
                "stored": False,
                "warning": f"Supabase store failed with HTTP {exc.code}.",
                "details": exc.read().decode("utf-8", errors="replace"),
            }
        except error.URLError as exc:
            return {
                "stored": False,
                "warning": f"Supabase request failed: {exc.reason}.",
            }

    def handle_message(self, phone_number: str, message_text: str) -> dict[str, Any]:
        profile = self.get_profile(phone_number)
        was_complete = profile.profile_complete
        text = message_text.strip()

        if not text:
            reply = self.next_question(profile)
            save_result = self.save_profile(profile)
            return {
                "profile": profile,
                "reply": reply,
                "save_result": save_result,
                "just_completed": False,
            }

        self._fill_from_message(profile, text)
        profile.profile_stage = self._next_stage(profile)
        profile.profile_complete = profile.profile_stage == "complete"
        reply = self._build_reply(profile)
        save_result = self.save_profile(profile)

        return {
            "profile": profile,
            "reply": reply,
            "save_result": save_result,
            "just_completed": (not was_complete) and profile.profile_complete,
        }

    def next_question(self, profile: FarmerProfile) -> str:
        stage = self._next_stage(profile)

        if stage == "mandal":
            return (
                "Naanna, mundu mee mandal cheppandi. "
                "Udaharanaki: nandipet, armur, bodhan."
            )
        if stage == "acres":
            return (
                "Sare. Mee daggara entha bhoomi undi? "
                "Acres lo cheppandi. Udaharanaki: 10 acres."
            )
        if stage == "soil_and_water":
            return (
                "Mee bhoomi soil type mariyu neellu ela unnayo cheppandi. "
                "Udaharanaki: black cotton + borewell, red soil + rainfed, mixed + canal."
            )
        if stage == "history_and_loan":
            return (
                "Last 3 crops emi vesaru? Loan unda? "
                "Udaharanaki: paddy, turmeric, maize. Loan 2 lakh undi. "
                "Ledu ante 'no loan' ani cheppandi."
            )
        return "Mee profile complete ayyindi."

    def _build_reply(self, profile: FarmerProfile) -> str:
        stage = self._next_stage(profile)
        if stage == "complete":
            crops = ", ".join(profile.last_three_crops) if profile.last_three_crops else "cheppaledu"
            loan = profile.loan_situation or "cheppaledu"
            return (
                "Bagundi naanna. Mee details note chesanu.\n"
                f"Mandal: {profile.mandal}\n"
                f"Acres: {profile.acres}\n"
                f"Soil: {profile.soil_type}\n"
                f"Water: {profile.water_source}\n"
                f"Last crops: {crops}\n"
                f"Loan: {loan}\n\n"
                "Ippudu recommendation chepthanu."
            )
        return self.next_question(profile)

    def _fill_from_message(self, profile: FarmerProfile, text: str) -> None:
        normalized = _normalize_text(text)

        if not profile.mandal:
            mandal = self._extract_mandal(normalized)
            if mandal:
                profile.mandal = mandal

        if profile.acres is None:
            acres = self._extract_acres(normalized)
            if acres is not None:
                profile.acres = acres

        soil = self._extract_soil(normalized)
        if soil:
            profile.soil_type = soil

        water = self._extract_water(normalized)
        if water:
            profile.water_source = water

        crops = self._extract_crops(normalized)
        if crops:
            profile.last_three_crops = crops[:3]

        loan_amount = self._extract_loan_amount(normalized)
        if loan_amount is not None:
            profile.loan_burden_rs = loan_amount
            if loan_amount == 0:
                profile.loan_situation = "no loan"
            else:
                profile.loan_situation = f"₹{loan_amount:,} loan"
        elif not profile.loan_situation:
            if "no loan" in normalized or "loan ledu" in normalized or "ledu" == normalized:
                profile.loan_situation = "no loan"
                profile.loan_burden_rs = 0
            elif "loan" in normalized or "appu" in normalized:
                profile.loan_situation = text.strip()

    def _next_stage(self, profile: FarmerProfile) -> str:
        if not profile.mandal:
            return "mandal"
        if profile.acres is None:
            return "acres"
        if not profile.soil_type or not profile.water_source:
            return "soil_and_water"
        if not profile.last_three_crops or profile.loan_situation is None:
            return "history_and_loan"
        return "complete"

    def _fetch_from_supabase(self, phone_number: str) -> FarmerProfile | None:
        if not self.supabase_url or not self.supabase_key:
            return None

        endpoint = (
            f"{self.supabase_url}/rest/v1/{self.table_name}"
            f"?phone_number=eq.{phone_number}&select=*"
        )
        req = request.Request(
            endpoint,
            headers={
                "Accept": "application/json",
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}",
            },
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (error.HTTPError, error.URLError, json.JSONDecodeError):
            return None

        if not payload:
            return None

        row = payload[0]
        return FarmerProfile(
            phone_number=row["phone_number"],
            mandal=row.get("mandal"),
            acres=row.get("acres"),
            soil_type=row.get("soil_type"),
            water_source=row.get("water_source"),
            last_three_crops=row.get("last_three_crops") or [],
            loan_situation=row.get("loan_situation"),
            loan_burden_rs=row.get("loan_burden_rs") or 0,
            profile_stage=row.get("profile_stage") or "mandal",
            profile_complete=bool(row.get("profile_complete")),
            created_at_utc=row.get("created_at_utc"),
            updated_at_utc=row.get("updated_at_utc"),
        )

    def _extract_mandal(self, normalized_text: str) -> str | None:
        for mandal in MANDALS:
            key_text = mandal.replace("_", " ")
            if key_text in normalized_text or mandal in normalized_text.replace(" ", "_"):
                return mandal

        compact_text = normalized_text.replace(" ", "")
        for mandal in MANDALS:
            key_text = mandal.replace("_", " ")
            compact_key = key_text.replace(" ", "")
            if SequenceMatcher(None, compact_text, compact_key).ratio() >= 0.88:
                return mandal

            for token in _tokenize_words(normalized_text):
                if SequenceMatcher(None, token, compact_key).ratio() >= 0.88:
                    return mandal
        return None

    def _extract_acres(self, normalized_text: str) -> float | None:
        match = re.search(r"(\d+(?:\.\d+)?)\s*(acre|acres|ekar|ekarlu)?", normalized_text)
        if not match:
            tokens = _tokenize_words(normalized_text)

            for index, token in enumerate(tokens):
                if token not in ACRE_UNITS:
                    continue
                start = max(0, index - 5)
                parsed = _parse_number_tokens(tokens[start:index])
                if parsed is not None:
                    return float(parsed)

            compact_tokens = [token for token in tokens if token not in NUMBER_NOISE_WORDS]
            has_blocked_context = any(token in ACRE_BLOCKLIST for token in compact_tokens)
            if compact_tokens and not has_blocked_context and len(compact_tokens) <= 3:
                parsed = _parse_number_phrase(normalized_text)
                if parsed is not None and 0 < parsed <= 500:
                    return float(parsed)
            return None
        value = float(match.group(1))
        compact_text = normalized_text.strip()
        standalone_number = bool(re.fullmatch(r"\d+(?:\.\d+)?", compact_text))
        if match.group(2) or (standalone_number and 0 < value <= 500):
            return value
        return None

    def _extract_soil(self, normalized_text: str) -> str | None:
        for alias, canonical in SOIL_ALIASES.items():
            if alias in normalized_text:
                return canonical
        return None

    def _extract_water(self, normalized_text: str) -> str | None:
        for alias, canonical in WATER_ALIASES.items():
            if alias in normalized_text:
                return canonical
        return None

    def _extract_crops(self, normalized_text: str) -> list[str]:
        found: list[str] = []
        for alias, canonical in CROP_ALIASES.items():
            if alias in normalized_text and canonical not in found:
                found.append(canonical)
        return found

    def _extract_loan_amount(self, normalized_text: str) -> int | None:
        if "no loan" in normalized_text or "loan ledu" in normalized_text:
            return 0

        lakh_match = re.search(r"(\d+(?:\.\d+)?)\s*lakh", normalized_text)
        if lakh_match:
            return int(float(lakh_match.group(1)) * 100000)

        rs_match = re.search(r"(?:rs|rupees|rupee)?\s*(\d{4,8})", normalized_text)
        if rs_match and "loan" in normalized_text:
            return int(rs_match.group(1))

        if any(keyword in normalized_text for keyword in LOAN_KEYWORDS):
            parsed = _parse_number_phrase(normalized_text)
            if parsed is not None:
                return parsed

        return None


def is_profile_complete(profile: FarmerProfile) -> bool:
    return FarmerProfileManager()._next_stage(profile) == "complete"
