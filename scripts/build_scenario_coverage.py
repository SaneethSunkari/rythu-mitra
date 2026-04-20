"""Build a machine-readable and human-readable coverage map for the 33-scenario spec."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
JSON_PATH = DOCS_DIR / "scenario_coverage.json"
MARKDOWN_PATH = DOCS_DIR / "scenario_coverage.md"
DECLARED_SCENARIO_COUNT = 33


SCENARIOS = [
    {
        "id": "A1",
        "category": "Crop recommendation",
        "title": "Farmer asks what to grow this season",
        "status": "implemented",
        "current_repo_reality": (
            "The 5-filter engine, Telugu response generation, and WhatsApp onboarding already run end-to-end for this core use case."
        ),
        "evidence": [
            "engine/crop_engine.py",
            "bot/farmer_profile.py",
            "bot/whatsapp_handler.py",
            "scripts/test_engine.py",
        ],
    },
    {
        "id": "A2",
        "category": "Crop recommendation",
        "title": "Farmer insists on growing what everyone else grows",
        "status": "implemented",
        "current_repo_reality": (
            "The bot now gives a dedicated pressure-and-floor-profit explanation when the farmer insists on an oversupplied crop, while still preserving farmer autonomy."
        ),
        "evidence": ["engine/crop_engine.py", "engine/district_cap.py", "bot/scenario_logic.py"],
    },
    {
        "id": "A3",
        "category": "Crop recommendation",
        "title": "Farmer felt another farmer's recommendation was unfair",
        "status": "partial",
        "current_repo_reality": (
            "The bot logs recommendations and tracks cap pressure, but it does not yet render the transparent side-by-side fairness explanation described in the spec."
        ),
        "evidence": ["engine/district_cap.py", "bot/whatsapp_handler.py"],
    },
    {
        "id": "A4",
        "category": "Crop recommendation",
        "title": "Farmer trusted bot, switched crop, got lower price than old crop",
        "status": "partial",
        "current_repo_reality": (
            "The bot now has an accountability-style response for 'you told me and it went wrong', but it still does not reconstruct the original recommendation snapshot and realized market outcome in full detail."
        ),
        "evidence": ["engine/district_cap.py", "bot/scenario_logic.py"],
    },
    {
        "id": "B1",
        "category": "Crop monitoring",
        "title": "Farmer sends field photo (crop looks unhealthy)",
        "status": "partial",
        "current_repo_reality": (
            "The webhook now accepts image media, enforces photo-quality checks, and routes through a confidence-threshold diagnosis path. It is still conservative because trained weights are optional and low-confidence cases are intentionally sent to KVK."
        ),
        "evidence": ["bot/whatsapp_handler.py", "disease/model.py", "disease/inference.py", "scripts/test_agronomy_services.py"],
    },
    {
        "id": "B2",
        "category": "Crop monitoring",
        "title": "Proactive disease alert (before farmer sees problem)",
        "status": "implemented",
        "current_repo_reality": (
            "The repo now evaluates weather plus crop stage for proactive disease pressure and can collect due reminders from saved crop-cycle state."
        ),
        "evidence": ["bot/proactive_monitor.py", "bot/crop_cycle_service.py", "scripts/run_scheduled_alerts.py", "scripts/test_agronomy_services.py"],
    },
    {
        "id": "B3",
        "category": "Crop monitoring",
        "title": "Photo unclear / poor quality",
        "status": "implemented",
        "current_repo_reality": (
            "Poor-quality images are now explicitly rejected before diagnosis with a clearer-photo retry message, instead of guessing."
        ),
        "evidence": ["disease/model.py", "disease/inference.py", "bot/whatsapp_handler.py", "scripts/test_agronomy_services.py"],
    },
    {
        "id": "B4",
        "category": "Crop monitoring",
        "title": "Crop monitoring reminder (crop-specific schedule)",
        "status": "implemented",
        "current_repo_reality": (
            "Season calendars now generate crop-stage monitoring and fertilizer reminders from sowing date, and due reminders can be collected from persisted crop-cycle state."
        ),
        "evidence": ["engine/season_calendar.py", "bot/crop_cycle_service.py", "scripts/run_scheduled_alerts.py", "scripts/test_agronomy_services.py"],
    },
    {
        "id": "C1",
        "category": "Market & selling",
        "title": "Farmer asks where to sell at best price",
        "status": "partial",
        "current_repo_reality": (
            "Price data pipelines exist, but the bot does not yet calculate transport-adjusted net price across mandis inside the WhatsApp flow."
        ),
        "evidence": ["engine/price_pipeline.py", "dashboard/src/components/MandiPrices.jsx"],
    },
    {
        "id": "C2",
        "category": "Market & selling",
        "title": "Trader arrives at village, quotes low price",
        "status": "partial",
        "current_repo_reality": (
            "The underlying price data exists, but there is no dedicated compare-against-trader negotiation response yet."
        ),
        "evidence": ["engine/price_pipeline.py"],
    },
    {
        "id": "C3",
        "category": "Market & selling",
        "title": "Long-cycle crop: price prediction 6 months out",
        "status": "implemented",
        "current_repo_reality": (
            "The repo now has a dedicated long-cycle outlook service for crops like turmeric and dragon fruit that returns a probability range, confidence, and explicit buyer-confirmation guidance."
        ),
        "evidence": ["engine/long_cycle_outlook.py", "bot/scenario_logic.py", "scripts/test_agronomy_services.py"],
    },
    {
        "id": "C4",
        "category": "Market & selling",
        "title": "Farmer planted without buyer — harvest approaching, no buyer found",
        "status": "partial",
        "current_repo_reality": (
            "The bot now has a generic buyer-not-found escalation path that points the farmer toward FPO, e-NAM, and storage routes, but it does not yet have contact-level integrations."
        ),
        "evidence": ["bot/scenario_logic.py"],
    },
    {
        "id": "D1",
        "category": "Financial & loans",
        "title": "Farmer shares loan details — very high interest rate",
        "status": "implemented",
        "current_repo_reality": (
            "The bot now converts monthly interest to annualized pressure, flags the 24% danger line used in the project, and points the farmer toward waiver and KCC options."
        ),
        "evidence": ["data/nizamabad_district.py", "bot/scenario_logic.py", "bot/whatsapp_handler.py"],
    },
    {
        "id": "D2",
        "category": "Financial & loans",
        "title": "Farmer panicking about debt repayment deadline",
        "status": "implemented",
        "current_repo_reality": (
            "The bot now has a deadline-panic response that starts with calming language and then points to Rythu Bandhu, PM-KISAN, waiver, and restructure options."
        ),
        "evidence": ["bot/scenario_logic.py"],
    },
    {
        "id": "D3",
        "category": "Financial & loans",
        "title": "Farmer asks about government schemes",
        "status": "implemented",
        "current_repo_reality": (
            "The bot now personalizes the scheme summary using acres and current loan burden, especially for Rythu Bandhu and the loan-waiver path."
        ),
        "evidence": ["data/nizamabad_district.py", "bot/scenario_logic.py", "bot/whatsapp_handler.py"],
    },
    {
        "id": "D4",
        "category": "Financial & loans",
        "title": "Farmer considering selling land to repay debt",
        "status": "implemented",
        "current_repo_reality": (
            "The bot now has a dedicated 'do not sell land first' response that reroutes the farmer toward waiver, KCC, and restructure options before a land-sale decision."
        ),
        "evidence": ["bot/scenario_logic.py"],
    },
    {
        "id": "E1",
        "category": "Emotional & crisis",
        "title": "Crop completely failed — farmer in deep distress",
        "status": "implemented",
        "current_repo_reality": (
            "The bot now acknowledges the distress and immediately pivots to documenting loss, agriculture-office follow-up, loan pressure relief, and KVK support."
        ),
        "evidence": ["bot/scenario_logic.py"],
    },
    {
        "id": "E2",
        "category": "Emotional & crisis",
        "title": "Bot gave wrong recommendation — farmer lost money",
        "status": "partial",
        "current_repo_reality": (
            "The bot now has an accountability-style response and asks for actual yield/selling-rate context, but it still does not reconstruct the historical recommendation with stored evidence."
        ),
        "evidence": ["bot/scenario_logic.py", "engine/district_cap.py"],
    },
    {
        "id": "E3",
        "category": "Emotional & crisis",
        "title": "Farmer expresses extreme despair / suicidal ideation",
        "status": "implemented",
        "current_repo_reality": (
            "The bot now has an urgent crisis reply that tells the farmer not to stay alone and routes them to India's Tele-MANAS mental-health helplines."
        ),
        "evidence": ["bot/scenario_logic.py"],
    },
    {
        "id": "F1",
        "category": "Weather & environment",
        "title": "Daily morning weather alert",
        "status": "partial",
        "current_repo_reality": (
            "The repo can now generate an on-demand morning weather snapshot, but it still does not proactively schedule and push daily alerts."
        ),
        "evidence": ["engine/weather_pipeline.py", "bot/scenario_logic.py"],
    },
    {
        "id": "F2",
        "category": "Weather & environment",
        "title": "Post-harvest drying alert — rain coming",
        "status": "implemented",
        "current_repo_reality": (
            "Drying alerts now evaluate hourly rain probability and emit urgent cover-now warnings when rain risk crosses the 60% / 3-hour threshold."
        ),
        "evidence": ["bot/drying_alerts.py", "bot/crop_cycle_service.py", "scripts/run_scheduled_alerts.py", "scripts/test_agronomy_services.py"],
    },
    {
        "id": "F3",
        "category": "Weather & environment",
        "title": "Evening full-night forecast during drying",
        "status": "implemented",
        "current_repo_reality": (
            "The drying alert service now emits a dedicated evening/night drying summary when the farmer is in drying phase."
        ),
        "evidence": ["bot/drying_alerts.py", "bot/crop_cycle_service.py", "scripts/test_agronomy_services.py"],
    },
    {
        "id": "F4",
        "category": "Weather & environment",
        "title": "Monsoon delayed — farmer about to plant",
        "status": "implemented",
        "current_repo_reality": (
            "The bot now has a dedicated delayed-monsoon advisory that uses the short-term weather view and redirects the farmer away from high-water crops."
        ),
        "evidence": ["engine/weather_pipeline.py"],
    },
    {
        "id": "G1",
        "category": "Scale & district management",
        "title": "Bot recommendation cap approaching for a crop",
        "status": "partial",
        "current_repo_reality": (
            "Cap pressure is computed and surfaced inside the engine, but there is no proactive alert when a cap is merely approaching."
        ),
        "evidence": ["engine/crop_engine.py", "engine/district_cap.py"],
    },
    {
        "id": "G2",
        "category": "Scale & district management",
        "title": "Bot has recommended same crop to 3,000 farmers — cap hit",
        "status": "partial",
        "current_repo_reality": (
            "The engine can stop recommending oversupplied crops, but there is no explicit high-scale explanation flow in the bot."
        ),
        "evidence": ["engine/crop_engine.py", "engine/district_cap.py"],
    },
    {
        "id": "H1",
        "category": "Labour & operations",
        "title": "Labour shortage at harvest",
        "status": "partial",
        "current_repo_reality": (
            "The bot now has a practical harvest-labour shortage reply, but it does not yet integrate with real labour pools or FPO networks."
        ),
        "evidence": ["bot/scenario_logic.py"],
    },
    {
        "id": "H2",
        "category": "Labour & operations",
        "title": "Input cost has risen sharply",
        "status": "implemented",
        "current_repo_reality": (
            "The bot now has a dedicated input-cost pressure reply that surfaces lower-cost alternatives from the current recommendation set."
        ),
        "evidence": ["engine/crop_engine.py", "bot/scenario_logic.py"],
    },
    {
        "id": "I1",
        "category": "Seeds & inputs",
        "title": "Farmer asks which seed variety to buy",
        "status": "partial",
        "current_repo_reality": (
            "The bot now has a conservative seed-buying advisory, but it does not yet recommend named certified varieties from a maintained catalog."
        ),
        "evidence": ["bot/scenario_logic.py"],
    },
    {
        "id": "I2",
        "category": "Seeds & inputs",
        "title": "Farmer bought wrong/counterfeit seeds",
        "status": "implemented",
        "current_repo_reality": (
            "The bot now tells the farmer to preserve the packet, bill, batch number, and photos, and escalate through the dealer and agriculture office."
        ),
        "evidence": ["bot/scenario_logic.py"],
    },
    {
        "id": "I3",
        "category": "Seeds & inputs",
        "title": "Pesticide shop recommending unnecessary chemicals",
        "status": "partial",
        "current_repo_reality": (
            "The bot now explicitly warns the farmer not to buy extra chemicals blindly, but it still lacks the full diagnosis-linked exact-quantity enforcement envisioned in the spec."
        ),
        "evidence": ["data/nizamabad_district.py", "bot/scenario_logic.py"],
    },
    {
        "id": "J1",
        "category": "Water & irrigation",
        "title": "Canal water release timing alert",
        "status": "implemented",
        "current_repo_reality": (
            "The repo now has a canal-release ingest/evaluation service that reads a feed or local schedule, maps branch releases to mandals, and generates advance preparation alerts."
        ),
        "evidence": ["bot/canal_alerts.py", "bot/scenario_logic.py", "data/canal_release_schedule.json", "scripts/test_agronomy_services.py"],
    },
    {
        "id": "J2",
        "category": "Water & irrigation",
        "title": "Drought conditions — crop water stress",
        "status": "implemented",
        "current_repo_reality": (
            "The bot now has a dedicated drought/water-stress reply that shifts the farmer toward lower-water crops and moisture-saving actions."
        ),
        "evidence": ["engine/crop_engine.py", "bot/scenario_logic.py"],
    },
    {
        "id": "K1",
        "category": "Accessibility",
        "title": "Farmer cannot type — voice only",
        "status": "partial",
        "current_repo_reality": (
            "Voice note transcription and voice reply paths exist and pass local smoke tests, but live reliability still depends on Twilio and Sarvam."
        ),
        "evidence": ["bot/telugu_voice.py", "bot/whatsapp_handler.py", "scripts/test_whatsapp_voice.py"],
    },
    {
        "id": "K2",
        "category": "Accessibility",
        "title": "Elderly farmer — describes crop problem in words, cannot send photo",
        "status": "implemented",
        "current_repo_reality": (
            "The bot now has a conservative text-only symptom triage path that gives caveated treatment guidance when the description matches a known crop pattern."
        ),
        "evidence": ["bot/scenario_logic.py"],
    },
    {
        "id": "L1",
        "category": "Inter-season",
        "title": "Idle land between kharif and rabi — what to do",
        "status": "implemented",
        "current_repo_reality": (
            "The bot now has a dedicated idle-land advisory and recommends short-cycle inter-season options like green gram where they fit the local profile."
        ),
        "evidence": ["data/nizamabad_district.py", "engine/crop_engine.py", "bot/scenario_logic.py"],
    },
    {
        "id": "L2",
        "category": "Inter-season",
        "title": "End of season feedback collection",
        "status": "implemented",
        "current_repo_reality": (
            "The bot now has a structured end-of-season feedback prompt covering crop, yield, and realized selling rate/problem."
        ),
        "evidence": ["bot/scenario_logic.py"],
    },
    {
        "id": "M1",
        "category": "Special crops",
        "title": "High-value crop (dragon fruit) — full 6-month monitoring",
        "status": "implemented",
        "current_repo_reality": (
            "Dragon fruit now has a dedicated 6-month specialty calendar with buyer activation from day 1 and stage-specific monitoring checkpoints."
        ),
        "evidence": ["data/specialty_crops.py", "engine/season_calendar.py", "bot/scenario_logic.py", "scripts/test_followup_scenarios.py"],
    },
    {
        "id": "M2",
        "category": "Special crops",
        "title": "Intercropping recommendation to maximise land use",
        "status": "implemented",
        "current_repo_reality": (
            "The bot now has a practical intercropping advisory path with simple crop-pair suggestions for risk spreading, though it is not yet fully engine-scored."
        ),
        "evidence": ["engine/crop_engine.py", "bot/scenario_logic.py"],
    },
    {
        "id": "N1",
        "category": "Onboarding",
        "title": "New farmer messages for the first time",
        "status": "implemented",
        "current_repo_reality": (
            "Progressive farmer profiling over 3-4 WhatsApp turns is working and already drives the engine."
        ),
        "evidence": ["bot/farmer_profile.py", "bot/whatsapp_handler.py"],
    },
    {
        "id": "N2",
        "category": "Onboarding",
        "title": "Farmer refers another farmer",
        "status": "implemented",
        "current_repo_reality": (
            "The bot now has a referral handoff reply that tells the current farmer how another farmer can start their own onboarding flow."
        ),
        "evidence": ["bot/scenario_logic.py"],
    },
]


STATUS_LABELS = {
    "implemented": "Implemented",
    "partial": "Partial",
    "not_built": "Not built",
}


def build_markdown(scenarios: list[dict]) -> str:
    counts = Counter(item["status"] for item in scenarios)
    categories: list[str] = []
    for item in scenarios:
        if item["category"] not in categories:
            categories.append(item["category"])

    lines: list[str] = [
        "# Rythu Mitra Scenario Coverage",
        "",
        "This document compares the provided scenario specification against the current repository state.",
        "",
        "Source files:",
        "- `docs/scenarios.pdf`",
        "- `docs/rythu_mitra_33_scenarios_extracted.txt`",
        "",
        f"Important note: the PDF title says **{DECLARED_SCENARIO_COUNT}** scenarios, but the enumerated scenario IDs in the document add up to **{len(scenarios)}**.",
        "",
        "## Snapshot",
        "",
        f"- Implemented: {counts['implemented']}",
        f"- Partial: {counts['partial']}",
        f"- Not built: {counts['not_built']}",
        f"- Declared in PDF title: {DECLARED_SCENARIO_COUNT}",
        f"- Enumerated in PDF body: {len(scenarios)}",
        "",
        "## Status Legend",
        "",
        "- **Implemented**: the repo supports the core scenario end-to-end locally today.",
        "- **Partial**: the repo has meaningful foundations, but the full scenario UX or rules are incomplete.",
        "- **Not built**: the scenario is still missing or only scaffolded.",
        "",
        "## What Was Actually Tested",
        "",
        "- `python3 scripts/test_system.py`",
        "- `python3 scripts/test_agronomy_services.py`",
        "- `python3 scripts/test_followup_scenarios.py`",
        "- `python3 scripts/test_engine.py`",
        "- `python3 scripts/test_whatsapp_voice.py`",
        "- 36-mandal engine sweep without crashes",
        "- FastAPI route checks for `/`, `/health`, `/dashboard`, and `/whatsapp`",
        "- Price pipeline preparation and weather pipeline preparation",
        "",
        "The matrix below is intentionally strict: it marks a scenario as implemented only when the repo already behaves like that scenario, not just because a related data file exists.",
        "",
    ]

    for category in categories:
        lines.extend(
            [
                f"## {category}",
                "",
                "| ID | Scenario | Status | Current repo reality | Evidence |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for item in scenarios:
            if item["category"] != category:
                continue
            evidence = ", ".join(f"`{path}`" for path in item["evidence"]) if item["evidence"] else "—"
            lines.append(
                f"| {item['id']} | {item['title']} | {STATUS_LABELS[item['status']]} | {item['current_repo_reality']} | {evidence} |"
            )
        lines.append("")

    lines.extend(
        [
            "## Read This Correctly",
            "",
            "The repo is already strong at the core crop-decision problem, onboarding, deployment, and dashboard visibility.",
            "The big remaining gap is not structure; it is breadth. The 33-scenario spec includes disease, crisis handling, irrigation alerts, post-harvest logistics, and long-cycle monitoring that are intentionally broader than the current shipped surface.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    counts = Counter(item["status"] for item in SCENARIOS)

    payload = {
        "source_pdf": "docs/scenarios.pdf",
        "source_text": "docs/rythu_mitra_33_scenarios_extracted.txt",
        "summary": {
            "declared_in_pdf_title": DECLARED_SCENARIO_COUNT,
            "implemented": counts["implemented"],
            "partial": counts["partial"],
            "not_built": counts["not_built"],
            "enumerated_in_pdf_body": len(SCENARIOS),
        },
        "scenarios": SCENARIOS,
    }

    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MARKDOWN_PATH.write_text(build_markdown(SCENARIOS) + "\n", encoding="utf-8")

    print(f"Wrote {JSON_PATH}")
    print(f"Wrote {MARKDOWN_PATH}")
    print(json.dumps(payload["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
