"""Exercise the new follow-up scenario flows on top of a completed farmer profile."""

from __future__ import annotations

import json
import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bot.whatsapp_handler as whatsapp_handler


def _message(client: TestClient, phone: str, body: str) -> str:
    response = client.post(
        "/whatsapp",
        data={"From": phone, "Body": body, "NumMedia": "0"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    response.raise_for_status()
    return response.text


def main() -> None:
    phone = "whatsapp:+919900001234"
    original_schedule = whatsapp_handler._maybe_schedule_voice_reply
    whatsapp_handler._maybe_schedule_voice_reply = lambda *args, **kwargs: None

    try:
        with TestClient(whatsapp_handler.app) as client:
            for body in (
                "reset",
                "nandipet",
                "10 acres",
                "deep calcareous mixed water",
                "last crop paddy, loan 2 lakh undi",
            ):
                _message(client, phone, body)

            cases = {
                "a2_insist_paddy": (
                    "andaru paddy vestunnaru naanu kuda veyyali",
                    ["Decision meeru cheyyandi", "safe cap"],
                ),
                "c1_best_market": (
                    "anna paddy ekkada ammalani",
                    ["Best reachable mandi", "net"],
                ),
                "c2_trader_offer": (
                    "trader 1750 istunnadu teesukovala",
                    ["Difference", "loss"],
                ),
                "d1_high_interest": (
                    "1.5 lakh loan undi 3% per month interest istunnanu",
                    ["36.0% annual", "7% annual"],
                ),
                "d3_schemes": (
                    "schemes enti",
                    ["రైతు బంధు", "కిసాన్ క్రెడిట్ కార్డ్"],
                ),
                "d2_deadline_panic": (
                    "repayment 15 days lo undi cheyyalekapotunnanu",
                    ["breathe", "Rythu Bandhu"],
                ),
                "f4_delayed_monsoon": (
                    "varsham late undi sowing delay",
                    ["varsham late", "Next 7 rojulu"],
                ),
                "f1_weather_preview": (
                    "morning weather alert pampu",
                    ["morning weather snapshot", "Next 7 rojula"],
                ),
                "j2_drought": (
                    "water stress undi neellu levu",
                    ["lower-water shortlist", "moisture"],
                ),
                "l1_idle_land": (
                    "idle land undi between season emi veyyali",
                    ["పెసలు", "short cycle"],
                ),
                "l2_feedback": (
                    "season ayipoyindi feedback",
                    ["Season close", "yield"],
                ),
                "h2_input_cost": (
                    "input cost perigindi fertilizer rate ekkuva",
                    ["low-cost safe options", "input approx"],
                ),
                "m2_intercropping": (
                    "intercropping cheyyala rendu crops",
                    ["intercropping pair", "risk spread"],
                ),
                "n2_referral": (
                    "friend ni refer cheyyali",
                    ["3-4 messages", "WhatsApp number"],
                ),
                "k2_text_symptoms": (
                    "paddy lo yellow spots vachhai",
                    ["బ్లాస్ట్", "KVK"],
                ),
                "d4_sell_land": (
                    "loan kosam land ammesata anukuntunna",
                    ["KCC", "final step"],
                ),
                "e1_crop_failed": (
                    "crop failed ayindi chala loss ayindi",
                    ["baadha", "KVK"],
                ),
                "e2_bot_wrong": (
                    "meeru cheppindi follow chesanu wrong ayindi",
                    ["own", "actual yield"],
                ),
                "e3_crisis": (
                    "jeevitham ayipoyindi sachipovali anipisthundi",
                    ["14416", "1800-89-14416"],
                ),
                "h1_labour_shortage": (
                    "harvest ki labour dorakadamledu",
                    ["harvest", "priority blocks"],
                ),
                "i1_seed_variety": (
                    "which seed variety konali",
                    ["certified seed", "packet photo"],
                ),
                "i2_counterfeit_seed": (
                    "fake seed dorikindi wrong seed anipisthundi",
                    ["batch number", "proof"],
                ),
                "i3_pesticide_upsell": (
                    "shop extra chemical konamani cheppadu",
                    ["extra chemical konakandi", "exact quantity"],
                ),
                "c4_buyer_not_found": (
                    "harvest ki vastundi buyer ledu",
                    ["FPO", "e-NAM"],
                ),
                "b4_calendar_setup": (
                    "maize sowing date 2026-06-20",
                    ["season calendar set", "Next important windows"],
                ),
                "f2_drying_watch": (
                    "start drying today",
                    ["drying watch active", "Start date"],
                ),
            }

            results: dict[str, str] = {}
            for case_name, (prompt, expected_parts) in cases.items():
                reply = _message(client, phone, prompt)
                results[case_name] = reply
                for part in expected_parts:
                    assert part in reply, f"{case_name}: expected {part!r} in reply:\n{reply}"

        print(json.dumps({"status": "ok", "cases": list(cases)}, ensure_ascii=False, indent=2))
    finally:
        whatsapp_handler._maybe_schedule_voice_reply = original_schedule


if __name__ == "__main__":
    main()
