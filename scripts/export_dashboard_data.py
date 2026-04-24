"""Export the website fallback JSON from the live backend payload contract."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.dashboard_payload import build_site_context


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = ROOT / "dashboard" / "src" / "data" / "dashboardData.json"


def main() -> None:
    payload = build_site_context()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Exported website fallback data to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
