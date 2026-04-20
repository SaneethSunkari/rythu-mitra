"""Evaluate due calendar, proactive, and drying alerts for all saved crop cycles."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot.crop_cycle_service import CropCycleService


def main() -> None:
    alerts = CropCycleService().collect_due_alerts()
    print(json.dumps({"due_alerts": alerts, "count": len(alerts)}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
