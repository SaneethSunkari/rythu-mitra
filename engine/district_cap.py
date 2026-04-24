"""Per-season district recommendation log and cap tracker."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOG_PATH = ROOT / "data" / "recommendation_log.json"


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


class DistrictCapTracker:
    """Persist primary recommendations so cap logic survives restarts."""

    _entries_cache: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    _totals_cache: dict[tuple[str, str, str], dict[str, int]] = {}

    def __init__(
        self,
        log_path: str | Path = DEFAULT_LOG_PATH,
        *,
        supabase_url: str | None = None,
        supabase_key: str | None = None,
        table_name: str = "recommendation_log",
        timeout_seconds: int = 20,
    ) -> None:
        _load_local_env()
        self.log_path = Path(log_path)
        self.supabase_url = (supabase_url or os.getenv("SUPABASE_URL", "")).rstrip("/")
        self.supabase_key = _resolve_supabase_key(supabase_key)
        self.table_name = table_name
        self.timeout_seconds = timeout_seconds
        self._supabase_table_available: bool | None = None

    def _cache_scope(self) -> tuple[str, str]:
        backend = self.supabase_url or f"local:{self.log_path}"
        return backend, self.table_name

    def _entries_cache_key(self, season: str | None) -> tuple[str, str, str]:
        backend, table_name = self._cache_scope()
        return backend, table_name, season or "__all__"

    def _invalidate_caches(self, season: str | None = None) -> None:
        backend, table_name = self._cache_scope()
        seasons = [season, None] if season else [None]
        for season_key in seasons:
            cache_key = (backend, table_name, season_key or "__all__")
            self._entries_cache.pop(cache_key, None)
            self._totals_cache.pop(cache_key, None)

    def _load_payload(self) -> dict[str, Any]:
        if not self.log_path.exists():
            return {"entries": []}

        try:
            payload = json.loads(self.log_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"entries": []}

        if not isinstance(payload, dict):
            return {"entries": []}
        entries = payload.get("entries")
        if not isinstance(entries, list):
            payload["entries"] = []
        return payload

    def _save_payload(self, payload: dict[str, Any]) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _supabase_ready(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)

    def _supabase_headers(self, *, prefer: str | None = None) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
        }
        if prefer:
            headers["Prefer"] = prefer
        return headers

    def _supabase_entries(self, season: str | None = None) -> list[dict[str, Any]] | None:
        if not self._supabase_ready():
            return None
        if self._supabase_table_available is False:
            return None

        query_parts = [
            "select=season,farmer_key,farmer_id,survey_number,mandal,soil_zone,water_source,acres,primary_crop,secondary_crop,source,logged_at_utc",
            "order=logged_at_utc.desc",
        ]
        if season:
            query_parts.append(f"season=eq.{parse.quote(season, safe='_-')}")

        endpoint = f"{self.supabase_url}/rest/v1/{self.table_name}?{'&'.join(query_parts)}"
        req = request.Request(endpoint, headers=self._supabase_headers())

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
            self._supabase_table_available = True
        except error.HTTPError as exc:
            if exc.code == 404:
                self._supabase_table_available = False
            return None
        except (error.URLError, json.JSONDecodeError):
            return None

        if not isinstance(payload, list):
            return None
        return payload

    def _upsert_local_entry(self, new_entry: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        payload = self._load_payload()
        entries: list[dict[str, Any]] = payload.get("entries", [])

        replaced = False
        for idx, entry in enumerate(entries):
            if (
                entry.get("season") == new_entry.get("season")
                and entry.get("farmer_key") == new_entry.get("farmer_key")
            ):
                entries[idx] = new_entry
                replaced = True
                break

        if not replaced:
            entries.append(new_entry)

        payload["entries"] = entries
        self._save_payload(payload)
        return payload, replaced

    def _upsert_supabase_entry(self, new_entry: dict[str, Any]) -> dict[str, Any]:
        if not self._supabase_ready():
            return {
                "stored": False,
                "warning": "Supabase credentials missing; falling back to local tracker log.",
            }
        if self._supabase_table_available is False:
            return {
                "stored": False,
                "warning": "Supabase recommendation_log table missing; falling back to local tracker log.",
            }

        endpoint = f"{self.supabase_url}/rest/v1/{self.table_name}?on_conflict=season,farmer_key"
        payload = json.dumps([new_entry]).encode("utf-8")
        req = request.Request(
            endpoint,
            data=payload,
            method="POST",
            headers={
                **self._supabase_headers(prefer="resolution=merge-duplicates,return=representation"),
                "Content-Type": "application/json",
            },
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                response.read()
            self._supabase_table_available = True
            return {"stored": True}
        except error.HTTPError as exc:
            if exc.code == 404:
                self._supabase_table_available = False
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

    def get_entries(self, season: str | None = None) -> list[dict[str, Any]]:
        cache_key = self._entries_cache_key(season)
        cached = self._entries_cache.get(cache_key)
        if cached is not None:
            return cached

        supabase_entries = self._supabase_entries(season=season)
        if supabase_entries is not None:
            self._entries_cache[cache_key] = supabase_entries
            return supabase_entries

        payload = self._load_payload()
        entries = payload.get("entries", [])
        if season:
            entries = [entry for entry in entries if entry.get("season") == season]
        self._entries_cache[cache_key] = entries
        return entries

    def get_recommended_acres_by_crop(self, season: str) -> dict[str, int]:
        cache_key = self._entries_cache_key(season)
        cached = self._totals_cache.get(cache_key)
        if cached is not None:
            return cached

        totals: dict[str, float] = {}
        for entry in self.get_entries(season=season):
            crop = entry.get("primary_crop")
            acres = float(entry.get("acres") or 0)
            if not crop or acres <= 0:
                continue
            totals[crop] = totals.get(crop, 0.0) + acres
        rounded = {crop: int(round(acres)) for crop, acres in totals.items()}
        self._totals_cache[cache_key] = rounded
        return rounded

    def record_recommendation(
        self,
        *,
        season: str,
        farmer_key: str,
        acres: float,
        primary_crop: str | None,
        mandal: str,
        soil_zone: str,
        water_source: str,
        farmer_id: str | None = None,
        secondary_crop: str | None = None,
        source: str = "engine",
        survey_number: str | None = None,
    ) -> dict[str, Any]:
        if not primary_crop:
            return {"stored": False, "warning": "No primary crop to log."}

        new_entry = {
            "season": season,
            "farmer_key": farmer_key,
            "farmer_id": farmer_id,
            "survey_number": survey_number,
            "mandal": mandal,
            "soil_zone": soil_zone,
            "water_source": water_source,
            "acres": acres,
            "primary_crop": primary_crop,
            "secondary_crop": secondary_crop,
            "source": source,
            "logged_at_utc": datetime.now(timezone.utc).isoformat(),
        }

        remote_result = self._upsert_supabase_entry(new_entry)
        payload, replaced = self._upsert_local_entry(new_entry)
        self._invalidate_caches(season)
        season_entries = [entry for entry in payload.get("entries", []) if entry.get("season") == season]

        result = {
            "stored": bool(remote_result.get("stored")) or True,
            "updated_existing": replaced,
            "season_entries": len(season_entries),
            "totals_by_crop": self.get_recommended_acres_by_crop(season),
            "storage": "supabase" if remote_result.get("stored") else "local_fallback",
        }
        if not remote_result.get("stored") and remote_result.get("warning"):
            result["warning"] = remote_result["warning"]
            if remote_result.get("details"):
                result["details"] = remote_result["details"]
        return result

    def sync_local_to_supabase(self) -> dict[str, Any]:
        payload = self._load_payload()
        entries = payload.get("entries", [])
        if not entries:
            return {"status": "ok", "synced": 0, "failed": 0}
        if not self._supabase_ready():
            return {
                "status": "skipped",
                "synced": 0,
                "failed": len(entries),
                "warning": "Supabase credentials missing.",
            }

        synced = 0
        failures: list[dict[str, Any]] = []
        seasons_touched: set[str] = set()
        for entry in entries:
            result = self._upsert_supabase_entry(entry)
            if result.get("stored"):
                synced += 1
                if entry.get("season"):
                    seasons_touched.add(str(entry["season"]))
            else:
                failures.append(
                    {
                        "farmer_key": entry.get("farmer_key"),
                        "season": entry.get("season"),
                        "warning": result.get("warning"),
                    }
                )

        for season in seasons_touched:
            self._invalidate_caches(season)

        return {
            "status": "ok" if not failures else "partial",
            "synced": synced,
            "failed": len(failures),
            "failures": failures,
        }
