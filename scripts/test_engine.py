"""Recommendation engine smoke tests for the core Nandipet scenario."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.crop_engine import FarmerProfile, generate_telugu_response, recommend


def main() -> None:
    farmer = FarmerProfile(
        mandal="nandipet",
        acres=10,
        soil_zone="deep_calcareous",
        water_source="mixed",
        loan_burden_rs=200000,
        last_crops=["paddy"],
        farmer_id="smoke-test-farmer",
    )

    result = recommend(farmer)
    ranked_crops = [item["crop"] for item in result["ranked"]]
    rejected_reasons = {item["crop"]: item["reason"] for item in result["rejected"]}
    telugu_reply = generate_telugu_response(result)

    assert result["top_pick"] is not None, "Expected at least one recommendation."
    assert result["top_pick"]["crop"] == "maize", f"Expected maize top pick, got {result['top_pick']['crop']}"
    assert result["second_pick"] is not None, "Expected a second option."
    assert result["second_pick"]["crop"] == "soybean", f"Expected soybean second pick, got {result['second_pick']['crop']}"
    assert "paddy" in rejected_reasons and "Supply cap" in rejected_reasons["paddy"], "Paddy should fail supply cap."
    assert "turmeric" in rejected_reasons and "Supply cap" in rejected_reasons["turmeric"], "Turmeric should fail supply cap."
    assert "cotton" in rejected_reasons and "local suitability" in rejected_reasons["cotton"], "Cotton should be rejected for Nandipet local suitability."
    assert "Naanu guarantee ivvaleddu" in telugu_reply, "Telugu response must include the no-guarantee line."

    print(
        json.dumps(
            {
                "status": "ok",
                "top_pick": result["top_pick"]["crop"],
                "second_pick": result["second_pick"]["crop"],
                "ranked_crops": ranked_crops,
                "rejected": rejected_reasons,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
