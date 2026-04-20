"""Specialty-crop monitoring and long-cycle market outlook baselines."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


SPECIALTY_CROPS = {
    "dragon_fruit": {
        "display_name": "Dragon Fruit",
        "telugu_name": "డ్రాగన్ ఫ్రూట్",
        "grow_duration_days": 180,
        "buyer_confirmation_required": True,
        "price_outlook_per_kg": {
            "floor": 60,
            "avg": 85,
            "ceiling": 120,
            "confidence_pct": 70,
            "source_note": "Scenario-approved specialty-market baseline until live buyer feed is connected.",
        },
        "demand_signals": [
            "hotel and premium retail demand tends to improve when national supply is tight",
            "Hyderabad premium-fruit buyers and exporters create upside in strong festival/hotel periods",
            "buyer confirmation before planting is mandatory because 6-month demand can swing sharply",
        ],
        "monitoring_schedule": [
            {"day": 30, "type": "monitoring", "stage": "root_establishment", "title": "Month 1 photo", "note": "Root establishment and post-planting stress check."},
            {"day": 60, "type": "monitoring", "stage": "root_establishment", "title": "Month 2 photo", "note": "Check survival, stem hydration, and support condition."},
            {"day": 90, "type": "monitoring", "stage": "cladode_growth", "title": "Month 3 growth check", "note": "Track cladode growth and support frame health."},
            {"day": 120, "type": "monitoring", "stage": "cladode_growth", "title": "Month 4 growth check", "note": "Every 2 weeks from here if canopy growth accelerates."},
            {"day": 150, "type": "flowering_watch", "stage": "flowering_prediction", "title": "Month 5 flowering watch", "note": "Temperature + humidity watch starts. Buyer search should already be active."},
            {"day": 180, "type": "harvest_window", "stage": "harvest", "title": "Month 6 buyer activation", "note": "Harvest timing and premium buyer activation window."},
        ],
    }
}


def default_canal_release_entries(now: datetime | None = None) -> list[dict]:
    """Seed a near-future SRSP release entry so the service has a usable template."""

    current = now or datetime.now(timezone.utc)
    release = (current + timedelta(days=1)).astimezone(timezone(timedelta(hours=5, minutes=30)))
    release = release.replace(hour=6, minute=0, second=0, microsecond=0)

    return [
        {
            "system": "SRSP",
            "branch_slug": "nandipet_branch",
            "branch_name": "Nandipet branch",
            "release_time": release.isoformat(),
            "available_hours": 8,
            "rotation_gap_days": 12,
            "mandals": ["nandipet", "balkonda", "bheemgal", "jakranpally"],
            "source": "scenario_seed",
            "source_note": "Seeded from the approved scenario so canal-alert logic can be exercised until a live official feed is attached.",
        }
    ]
