"""
Rythu Mitra — Daily Mandi Price Pipeline

Pulls live mandi prices from data.gov.in / Agmarknet when available.
Falls back to the hardcoded 5-year district crop history when the API is
unavailable, misconfigured, or returns no usable data.

Also supports bulk historical CSV import from data.gov.in exports so we can
backfill multi-year mandi history into Supabase.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.nizamabad_district import CROPS, MANDIS


DATA_GOV_RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
DATA_GOV_BASE_URL = "https://api.data.gov.in/resource"
SUPABASE_TABLE = "mandi_prices"
DEFAULT_HISTORY_CSV_PATH = "data/price_history.csv"
LOCAL_PRICE_CACHE_PATH = "data/cache/mandi_prices_latest.json"

SUPPORTED_MANDI_NAMES = tuple(MANDIS.keys())

MANDI_ALIASES = {
    "nizamabad": "Nizamabad",
    "nizamabad apmc": "Nizamabad",
    "armur": "Armur",
    "armoor": "Armur",
    "bodhan": "Bodhan",
    "kamareddy": "Kamareddy",
    "nandipet": "Nandipet",
    "balkonda": "Balkonda",
}

CROP_ALIASES = {
    "paddy": "paddy",
    "paddy dhan": "paddy",
    "paddydhan": "paddy",
    "paddydhan": "paddy",
    "turmeric": "turmeric",
    "maize": "maize",
    "soyabean": "soybean",
    "soybean": "soybean",
    "cotton": "cotton",
    "kapas": "cotton",
    "red gram": "red_gram",
    "redgram": "red_gram",
    "tur red gram whole": "red_gram",
    "arhar turredgram whole": "red_gram",
    "arhar tur red gram whole": "red_gram",
    "sunflower": "sunflower",
    "sunflower seed": "sunflower",
    "green gram": "green_gram",
    "greengram": "green_gram",
    "moong whole": "green_gram",
    "moong": "green_gram",
    "sugarcane": "sugarcane",
}


def _load_local_env(env_path: str = ".env") -> None:
    """Load key=value pairs from .env without needing external packages."""

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
    normalized = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    return re.sub(r"\s+", " ", normalized)


def _slugify(value: str) -> str:
    return _normalize_text(value).replace(" ", "_")


def _pick(record: dict[str, Any], *keys: str) -> Any:
    normalized = {_normalize_text(key): value for key, value in record.items()}
    for key in keys:
        value = normalized.get(_normalize_text(key))
        if value not in (None, ""):
            return value
    return None


def _as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = str(value).replace(",", "").strip()
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _as_int(value: Any) -> int | None:
    parsed = _as_float(value)
    if parsed is None:
        return None
    return int(round(parsed))


def _parse_price_date(value: Any) -> str:
    """Return ISO date string with a safe fallback to today's date."""

    if value in (None, ""):
        return date.today().isoformat()

    text = str(value).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return date.today().isoformat()


def _parse_historical_date(record: dict[str, Any]) -> str:
    explicit = _pick(
        record,
        "Arrival Date",
        "Arrival_Date",
        "Price Date",
        "Date",
        "Reported Date",
    )
    if explicit not in (None, ""):
        return _parse_price_date(explicit)

    year = _pick(record, "Year", "year", "Crop Year")
    if year not in (None, ""):
        digits = re.sub(r"[^0-9]", "", str(year))
        if len(digits) >= 4:
            return f"{digits[:4]}-01-01"

    return date.today().isoformat()


def _map_mandi_name(value: Any) -> str | None:
    normalized = _normalize_text(str(value or ""))
    if not normalized:
        return None

    if normalized in MANDI_ALIASES:
        return MANDI_ALIASES[normalized]

    for alias, mandi_name in MANDI_ALIASES.items():
        if alias in normalized:
            return mandi_name
    return None


def _map_crop_name(value: Any) -> str | None:
    normalized = _normalize_text(str(value or ""))
    if not normalized:
        return None

    if normalized in CROP_ALIASES:
        return CROP_ALIASES[normalized]

    compact = normalized.replace(" ", "")
    for alias, crop_slug in CROP_ALIASES.items():
        if alias.replace(" ", "") == compact:
            return crop_slug
    return None


class PricePipeline:
    """Live mandi sync with a district-history fallback."""

    def __init__(
        self,
        api_key: str | None = None,
        supabase_url: str | None = None,
        supabase_key: str | None = None,
        resource_id: str = DATA_GOV_RESOURCE_ID,
        supabase_table: str = SUPABASE_TABLE,
        timeout_seconds: int = 20,
    ) -> None:
        _load_local_env()

        self.api_key = api_key or os.getenv("DATA_GOV_API_KEY", "")
        self.supabase_url = (supabase_url or os.getenv("SUPABASE_URL", "")).rstrip("/")
        self.supabase_key = _resolve_supabase_key(supabase_key)
        self.resource_id = resource_id
        self.supabase_table = supabase_table
        self.timeout_seconds = timeout_seconds
        self.local_cache_path = Path(LOCAL_PRICE_CACHE_PATH)

    def _store_rows_locally(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        self.local_cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.local_cache_path.write_text(
            json.dumps(rows, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return {
            "stored_local": len(rows),
            "local_cache_path": str(self.local_cache_path),
        }

    def _build_query_urls(self) -> list[str]:
        if not self.api_key:
            return []

        query_variants = [
            {"filters[State]": "Telangana", "filters[District]": "Nizamabad"},
            {"filters[state]": "Telangana", "filters[district]": "Nizamabad"},
            {"filters[State Name]": "Telangana", "filters[District Name]": "Nizamabad"},
        ]

        urls = []
        for extra_filters in query_variants:
            params = {
                "api-key": self.api_key,
                "format": "json",
                "limit": 1000,
                "offset": 0,
            }
            params.update(extra_filters)
            urls.append(f"{DATA_GOV_BASE_URL}/{self.resource_id}?{parse.urlencode(params)}")
        return urls

    def _fetch_json(self, url: str) -> dict[str, Any]:
        req = request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "rythu-mitra/0.1",
            },
        )
        with request.urlopen(req, timeout=self.timeout_seconds) as response:
            body = response.read().decode("utf-8")
        return json.loads(body)

    def fetch_live_rows(self) -> tuple[list[dict[str, Any]], list[str]]:
        """
        Fetch and normalize live mandi price rows from data.gov.in.

        Returns a tuple of (rows, notes). Rows may be empty if the API is
        unavailable or returns unusable data.
        """

        if not self.api_key:
            return [], ["DATA_GOV_API_KEY missing; using fallback price history."]

        notes: list[str] = []
        for url in self._build_query_urls():
            try:
                payload = self._fetch_json(url)
            except error.HTTPError as exc:
                notes.append(f"data.gov.in HTTP {exc.code}; trying next query variant.")
                continue
            except error.URLError as exc:
                notes.append(f"data.gov.in request failed: {exc.reason}.")
                continue
            except json.JSONDecodeError:
                notes.append("data.gov.in returned non-JSON content.")
                continue

            records = payload.get("records") or []
            normalized_rows = self._normalize_live_records(records)
            if normalized_rows:
                return normalized_rows, notes

            count = payload.get("count")
            notes.append(f"data.gov.in returned {count or 0} records, none matched supported mandis/crops.")

        return [], notes or ["data.gov.in returned no usable rows."]

    def _normalize_live_records(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str, str]] = set()

        for record in records:
            mandi_name = _map_mandi_name(_pick(record, "Market", "Market Name"))
            crop_slug = _map_crop_name(_pick(record, "Commodity", "Commodity Name"))

            if not mandi_name or not crop_slug:
                continue
            if crop_slug not in MANDIS[mandi_name]["crops_traded"]:
                continue

            min_price = _as_int(_pick(record, "Min Price", "Min_Price"))
            max_price = _as_int(_pick(record, "Max Price", "Max_Price"))
            modal_price = _as_int(_pick(record, "Modal Price", "Modal_Price"))
            if min_price is None and max_price is None and modal_price is None:
                continue

            price_date = _parse_price_date(_pick(record, "Arrival Date", "Arrival_Date", "Price Date"))
            variety = _pick(record, "Variety")
            key = (price_date, _slugify(mandi_name), crop_slug, str(variety or ""))
            if key in seen:
                continue
            seen.add(key)

            rows.append({
                "price_date": price_date,
                "state": _pick(record, "State") or "Telangana",
                "district": _pick(record, "District") or "Nizamabad",
                "mandi_name": mandi_name,
                "mandi_slug": _slugify(mandi_name),
                "crop_name": crop_slug,
                "crop_slug": crop_slug,
                "variety": variety,
                "min_price_rs_per_qtl": min_price,
                "max_price_rs_per_qtl": max_price,
                "modal_price_rs_per_qtl": modal_price,
                "source": "data_gov_in",
                "source_resource": self.resource_id,
                "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
                "raw_record": record,
            })

        return rows

    def _read_csv_records(self, csv_path: str) -> list[dict[str, Any]]:
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"Historical CSV not found: {csv_path}")

        sample = path.read_text(encoding="utf-8-sig", errors="replace")[:4096]
        dialect = csv.excel
        try:
            dialect = csv.Sniffer().sniff(sample)
        except csv.Error:
            pass

        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            reader = csv.DictReader(handle, dialect=dialect)
            return [dict(row) for row in reader if row]

    def normalize_historical_csv_records(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str, str]] = set()

        for record in records:
            mandi_name = _map_mandi_name(_pick(record, "Market", "Market Name", "Mandi", "Mandi Name"))
            crop_slug = _map_crop_name(_pick(record, "Commodity", "Commodity Name", "Crop", "Crop Name"))

            if not mandi_name or not crop_slug:
                continue
            if crop_slug not in MANDIS[mandi_name]["crops_traded"]:
                continue

            min_price = _as_int(_pick(record, "Min Price", "Min_Price", "Min"))
            max_price = _as_int(_pick(record, "Max Price", "Max_Price", "Max"))
            modal_price = _as_int(_pick(record, "Modal Price", "Modal_Price", "Modal"))
            if min_price is None and max_price is None and modal_price is None:
                continue

            price_date = _parse_historical_date(record)
            variety = _pick(record, "Variety") or "historical_csv"
            key = (price_date, _slugify(mandi_name), crop_slug, str(variety))
            if key in seen:
                continue
            seen.add(key)

            rows.append({
                "price_date": price_date,
                "state": _pick(record, "State", "State Name") or "Telangana",
                "district": _pick(record, "District", "District Name") or "Nizamabad",
                "mandi_name": mandi_name,
                "mandi_slug": _slugify(mandi_name),
                "crop_name": crop_slug,
                "crop_slug": crop_slug,
                "variety": variety,
                "min_price_rs_per_qtl": min_price,
                "max_price_rs_per_qtl": max_price,
                "modal_price_rs_per_qtl": modal_price,
                "source": "historical_csv",
                "source_resource": "data.gov.in CSV import",
                "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
                "raw_record": record,
            })

        return rows

    def build_fallback_rows(
        self,
        missing_pairs: set[tuple[str, str]] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Create synthetic current-day rows from the hardcoded district history.

        If `missing_pairs` is provided, only those (mandi_slug, crop_slug) pairs
        are backfilled. Otherwise the full supported mandi/crop set is emitted.
        """

        today = date.today().isoformat()
        rows: list[dict[str, Any]] = []

        for mandi_name, mandi_data in MANDIS.items():
            mandi_slug = _slugify(mandi_name)
            for crop_slug in mandi_data["crops_traded"]:
                pair = (mandi_slug, crop_slug)
                if missing_pairs is not None and pair not in missing_pairs:
                    continue

                crop_data = CROPS.get(crop_slug)
                if not crop_data:
                    continue

                if crop_slug == "sugarcane":
                    floor = avg_price = ceiling = crop_data["price_qtl"]
                    history_years: list[int] = []
                else:
                    history = crop_data.get("price_history_qtl", {})
                    if not history:
                        continue
                    years = sorted(history)
                    history_years = years
                    floor = min(item["min"] for item in history.values())
                    ceiling = max(item["max"] for item in history.values())
                    avg_price = history[years[-1]]["avg"]

                rows.append({
                    "price_date": today,
                    "state": "Telangana",
                    "district": "Nizamabad",
                    "mandi_name": mandi_name,
                    "mandi_slug": mandi_slug,
                    "crop_name": crop_slug,
                    "crop_slug": crop_slug,
                    "variety": "district_fallback",
                    "min_price_rs_per_qtl": floor,
                    "max_price_rs_per_qtl": ceiling,
                    "modal_price_rs_per_qtl": avg_price,
                    "source": "historical_fallback",
                    "source_resource": "data.nizamabad_district.CROPS",
                    "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
                    "raw_record": {
                        "fallback": True,
                        "history_years": history_years,
                        "note": "Synthetic current-day row generated from hardcoded district price history.",
                    },
                })

        return rows

    def build_hardcoded_history_export_rows(self) -> list[dict[str, Any]]:
        """
        Expand in-code crop history into a CSV-friendly row set.

        This is a bootstrap artifact for the project when a downloaded
        data.gov.in CSV is not yet present locally.
        """

        rows: list[dict[str, Any]] = []
        for mandi_name, mandi_data in MANDIS.items():
            for crop_slug in mandi_data["crops_traded"]:
                crop_data = CROPS.get(crop_slug, {})
                history = crop_data.get("price_history_qtl", {})
                for year, prices in sorted(history.items()):
                    rows.append({
                        "Price Date": f"{year}-01-01",
                        "State": "Telangana",
                        "District": "Nizamabad",
                        "Market": mandi_name,
                        "Commodity": crop_slug,
                        "Variety": "hardcoded_history_export",
                        "Min Price": prices.get("min"),
                        "Max Price": prices.get("max"),
                        "Modal Price": prices.get("avg"),
                    })
        return rows

    def export_default_history_csv(self, csv_path: str = DEFAULT_HISTORY_CSV_PATH) -> dict[str, Any]:
        """Write a canonical historical CSV derived from the project's crop history."""

        rows = self.build_hardcoded_history_export_rows()
        path = Path(csv_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "Price Date",
            "State",
            "District",
            "Market",
            "Commodity",
            "Variety",
            "Min Price",
            "Max Price",
            "Modal Price",
        ]

        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        return {
            "status": "ok",
            "csv_path": csv_path,
            "rows_written": len(rows),
            "note": "Generated from hardcoded crop price history in data.nizamabad_district.CROPS.",
        }

    def _expected_pairs(self) -> set[tuple[str, str]]:
        pairs: set[tuple[str, str]] = set()
        for mandi_name, mandi_data in MANDIS.items():
            mandi_slug = _slugify(mandi_name)
            for crop_slug in mandi_data["crops_traded"]:
                pairs.add((mandi_slug, crop_slug))
        return pairs

    def store_rows(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Persist rows to Supabase over REST.

        Assumes a table like `mandi_prices` exists. The call is made resiliently
        so the pipeline still returns rows even if Supabase storage fails.
        """

        if not rows:
            return {"stored": 0, "warning": "No rows to store."}
        if not self.supabase_url or not self.supabase_key:
            local = self._store_rows_locally(rows)
            return {
                "stored": 0,
                "warning": "Supabase credentials missing; rows stored locally instead.",
                **local,
            }

        endpoint = (
            f"{self.supabase_url}/rest/v1/{self.supabase_table}"
            f"?on_conflict=price_date,mandi_slug,crop_slug,source,variety"
        )
        payload = json.dumps(rows).encode("utf-8")
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
                body = response.read().decode("utf-8")
            stored_rows = json.loads(body) if body else []
            return {"stored": len(stored_rows) or len(rows)}
        except error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            local = self._store_rows_locally(rows)
            return {
                "stored": 0,
                "warning": f"Supabase store failed with HTTP {exc.code}.",
                "details": error_body,
                **local,
            }
        except error.URLError as exc:
            local = self._store_rows_locally(rows)
            return {
                "stored": 0,
                "warning": f"Supabase request failed: {exc.reason}.",
                **local,
            }

    def run(self, persist: bool = True) -> dict[str, Any]:
        """Fetch live rows, backfill missing pairs from fallback, and store."""

        live_rows, notes = self.fetch_live_rows()
        expected_pairs = self._expected_pairs()
        live_pairs = {(row["mandi_slug"], row["crop_slug"]) for row in live_rows}
        missing_pairs = expected_pairs - live_pairs

        if live_rows:
            fallback_rows = self.build_fallback_rows(missing_pairs=missing_pairs)
            mode = "live_with_fallback_fill" if fallback_rows else "live"
            rows = live_rows + fallback_rows
        else:
            rows = self.build_fallback_rows()
            fallback_rows = rows
            mode = "fallback"

        storage = self.store_rows(rows) if persist else {"stored": 0, "warning": "Persist disabled."}

        return {
            "status": "ok" if rows else "no_data",
            "mode": mode,
            "resource_id": self.resource_id,
            "supported_mandis": list(SUPPORTED_MANDI_NAMES),
            "live_rows": len(live_rows),
            "fallback_rows": len(fallback_rows),
            "rows_prepared": len(rows),
            "rows_stored": storage.get("stored", 0),
            "storage_warning": storage.get("warning"),
            "storage_details": storage.get("details"),
            "rows_stored_locally": storage.get("stored_local", 0),
            "local_cache_path": storage.get("local_cache_path"),
            "notes": notes,
        }

    def load_historical_csv(self, csv_path: str = DEFAULT_HISTORY_CSV_PATH, persist: bool = True) -> dict[str, Any]:
        """Parse a downloaded Agmarknet/data.gov.in CSV and store supported rows."""

        try:
            records = self._read_csv_records(csv_path)
        except FileNotFoundError as exc:
            if csv_path == DEFAULT_HISTORY_CSV_PATH:
                generated = self.export_default_history_csv(csv_path=csv_path)
                records = self._read_csv_records(csv_path)
            else:
                return {
                    "status": "missing_file",
                    "csv_path": csv_path,
                    "rows_prepared": 0,
                    "rows_stored": 0,
                    "warning": str(exc),
                }
        else:
            generated = None

        rows = self.normalize_historical_csv_records(records)
        storage = self.store_rows(rows) if persist else {"stored": 0, "warning": "Persist disabled."}

        covered_pairs = sorted({(row["mandi_slug"], row["crop_slug"]) for row in rows})
        return {
            "status": "ok" if rows else "no_data",
            "csv_path": csv_path,
            "records_read": len(records),
            "rows_prepared": len(rows),
            "rows_stored": storage.get("stored", 0),
            "storage_warning": storage.get("warning"),
            "storage_details": storage.get("details"),
            "rows_stored_locally": storage.get("stored_local", 0),
            "local_cache_path": storage.get("local_cache_path"),
            "covered_pairs": covered_pairs,
            "generated_csv": generated,
        }


def _build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rythu Mitra mandi price pipeline")
    parser.add_argument(
        "--historical-csv",
        default="",
        help="Path to a downloaded historical Agmarknet/data.gov.in CSV file.",
    )
    parser.add_argument(
        "--export-default-history-csv",
        action="store_true",
        help="Generate data/price_history.csv from the project's hardcoded crop history.",
    )
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Prepare rows without writing to Supabase.",
    )
    return parser


if __name__ == "__main__":
    args = _build_cli().parse_args()
    pipeline = PricePipeline()
    if args.export_default_history_csv:
        summary = pipeline.export_default_history_csv(
            csv_path=args.historical_csv or DEFAULT_HISTORY_CSV_PATH
        )
    elif args.historical_csv:
        summary = pipeline.load_historical_csv(
            csv_path=args.historical_csv,
            persist=not args.no_persist,
        )
    else:
        summary = pipeline.run(persist=not args.no_persist)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
