"""Long-cycle crop outlooks for 6-month planting decisions."""

from __future__ import annotations

import os
import sys
from statistics import mean, pstdev

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.nizamabad_district import CROPS
from data.specialty_crops import SPECIALTY_CROPS


def _weighted_average(values: list[float]) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return values[-1] * 0.6 + values[-2] * 0.4
    tail = values[-2:]
    head = values[:-2]
    return tail[-1] * 0.4 + tail[-2] * 0.3 + mean(head) * 0.3


class LongCycleOutlookService:
    """Generate conservative long-horizon price ranges and buyer guidance."""

    def build_outlook(self, crop_name: str, *, horizon_months: int = 6) -> dict:
        crop_slug = crop_name.strip().lower().replace(" ", "_")
        if crop_slug in SPECIALTY_CROPS:
            return self._specialty_outlook(crop_slug, horizon_months=horizon_months)
        if crop_slug in CROPS:
            return self._history_outlook(crop_slug, horizon_months=horizon_months)
        raise ValueError(f"Unsupported long-cycle crop: {crop_name}")

    def _specialty_outlook(self, crop_slug: str, *, horizon_months: int) -> dict:
        crop = SPECIALTY_CROPS[crop_slug]
        price = crop["price_outlook_per_kg"]
        return {
            "crop_slug": crop_slug,
            "crop_name": crop["display_name"],
            "telugu_name": crop["telugu_name"],
            "horizon_months": horizon_months,
            "unit": "kg",
            "floor_price": price["floor"],
            "avg_price": price["avg"],
            "ceiling_price": price["ceiling"],
            "confidence_pct": price["confidence_pct"],
            "buyer_confirmation_required": crop["buyer_confirmation_required"],
            "signals": crop["demand_signals"],
            "source_note": price["source_note"],
        }

    def _history_outlook(self, crop_slug: str, *, horizon_months: int) -> dict:
        crop = CROPS[crop_slug]
        history = crop.get("price_history_qtl", {})
        if not history:
            raise ValueError(f"No price history available for {crop_slug}")

        years = sorted(history)
        avg_series = [history[year]["avg"] for year in years]
        floor_series = [history[year]["min"] for year in years]
        ceil_series = [history[year]["max"] for year in years]

        weighted_avg = _weighted_average(avg_series)
        volatility = pstdev(avg_series) if len(avg_series) > 1 else 0.0
        horizon_factor = max(horizon_months / 6, 1)
        floor = min(floor_series)
        ceiling = max(ceil_series)

        trend = 0.0
        if len(avg_series) >= 2 and avg_series[-2]:
            trend = (avg_series[-1] - avg_series[-2]) / avg_series[-2]

        adjusted_avg = weighted_avg * (1 + (trend * 0.35))
        adjusted_floor = max(floor, adjusted_avg - (volatility * 1.2 * horizon_factor))
        adjusted_ceiling = min(ceiling * 1.1, adjusted_avg + (volatility * 1.4 * horizon_factor))

        confidence = 65 if crop_slug == "turmeric" else 60

        return {
            "crop_slug": crop_slug,
            "crop_name": crop_slug.replace("_", " ").title(),
            "telugu_name": crop.get("telugu_name", crop_slug),
            "horizon_months": horizon_months,
            "unit": "quintal",
            "floor_price": round(adjusted_floor),
            "avg_price": round(adjusted_avg),
            "ceiling_price": round(adjusted_ceiling),
            "confidence_pct": confidence,
            "buyer_confirmation_required": True,
            "signals": [
                "district acreage and crowding risk still matter at harvest",
                "long-cycle planning needs buyer confirmation before planting",
                f"recent trend contribution: {round(trend * 100, 1)}%",
            ],
            "source_note": "Projected from the crop's multi-year district price history with extra uncertainty widening for 6-month decisions.",
        }


def render_long_cycle_reply(outlook: dict) -> str:
    unit = outlook["unit"]
    currency_unit = f"/{unit}"
    signals = "; ".join(outlook.get("signals", [])[:3])
    line = (
        f"Naanna, {outlook['crop_name']} ki {outlook['horizon_months']} months horizon lo "
        f"price range approx ₹{outlook['floor_price']:,} - ₹{outlook['ceiling_price']:,}{currency_unit}. "
        f"Middle case around ₹{outlook['avg_price']:,}{currency_unit}. "
        f"Nenu approx {outlook['confidence_pct']}% confidence tho chepthunna."
    )
    if outlook.get("buyer_confirmation_required"):
        line += " Buyer confirm chesaka matrame plant cheyyandi."
    if signals:
        line += f" Signals: {signals}."
    return line
