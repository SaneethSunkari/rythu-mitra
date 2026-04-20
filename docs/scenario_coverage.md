# Rythu Mitra Scenario Coverage

This document compares the provided scenario specification against the current repository state.

Source files:
- `docs/scenarios.pdf`
- `docs/rythu_mitra_33_scenarios_extracted.txt`

Important note: the PDF title says **33** scenarios, but the enumerated scenario IDs in the document add up to **40**.

## Snapshot

- Implemented: 26
- Partial: 14
- Not built: 0
- Declared in PDF title: 33
- Enumerated in PDF body: 40

## Status Legend

- **Implemented**: the repo supports the core scenario end-to-end locally today.
- **Partial**: the repo has meaningful foundations, but the full scenario UX or rules are incomplete.
- **Not built**: the scenario is still missing or only scaffolded.

## What Was Actually Tested

- `python3 scripts/test_system.py`
- `python3 scripts/test_agronomy_services.py`
- `python3 scripts/test_followup_scenarios.py`
- `python3 scripts/test_engine.py`
- `python3 scripts/test_whatsapp_voice.py`
- 36-mandal engine sweep without crashes
- FastAPI route checks for `/`, `/health`, `/dashboard`, and `/whatsapp`
- Price pipeline preparation and weather pipeline preparation

The matrix below is intentionally strict: it marks a scenario as implemented only when the repo already behaves like that scenario, not just because a related data file exists.

## Crop recommendation

| ID | Scenario | Status | Current repo reality | Evidence |
| --- | --- | --- | --- | --- |
| A1 | Farmer asks what to grow this season | Implemented | The 5-filter engine, Telugu response generation, and WhatsApp onboarding already run end-to-end for this core use case. | `engine/crop_engine.py`, `bot/farmer_profile.py`, `bot/whatsapp_handler.py`, `scripts/test_engine.py` |
| A2 | Farmer insists on growing what everyone else grows | Implemented | The bot now gives a dedicated pressure-and-floor-profit explanation when the farmer insists on an oversupplied crop, while still preserving farmer autonomy. | `engine/crop_engine.py`, `engine/district_cap.py`, `bot/scenario_logic.py` |
| A3 | Farmer felt another farmer's recommendation was unfair | Partial | The bot logs recommendations and tracks cap pressure, but it does not yet render the transparent side-by-side fairness explanation described in the spec. | `engine/district_cap.py`, `bot/whatsapp_handler.py` |
| A4 | Farmer trusted bot, switched crop, got lower price than old crop | Partial | The bot now has an accountability-style response for 'you told me and it went wrong', but it still does not reconstruct the original recommendation snapshot and realized market outcome in full detail. | `engine/district_cap.py`, `bot/scenario_logic.py` |

## Crop monitoring

| ID | Scenario | Status | Current repo reality | Evidence |
| --- | --- | --- | --- | --- |
| B1 | Farmer sends field photo (crop looks unhealthy) | Partial | The webhook now accepts image media, enforces photo-quality checks, and routes through a confidence-threshold diagnosis path. It is still conservative because trained weights are optional and low-confidence cases are intentionally sent to KVK. | `bot/whatsapp_handler.py`, `disease/model.py`, `disease/inference.py`, `scripts/test_agronomy_services.py` |
| B2 | Proactive disease alert (before farmer sees problem) | Implemented | The repo now evaluates weather plus crop stage for proactive disease pressure and can collect due reminders from saved crop-cycle state. | `bot/proactive_monitor.py`, `bot/crop_cycle_service.py`, `scripts/run_scheduled_alerts.py`, `scripts/test_agronomy_services.py` |
| B3 | Photo unclear / poor quality | Implemented | Poor-quality images are now explicitly rejected before diagnosis with a clearer-photo retry message, instead of guessing. | `disease/model.py`, `disease/inference.py`, `bot/whatsapp_handler.py`, `scripts/test_agronomy_services.py` |
| B4 | Crop monitoring reminder (crop-specific schedule) | Implemented | Season calendars now generate crop-stage monitoring and fertilizer reminders from sowing date, and due reminders can be collected from persisted crop-cycle state. | `engine/season_calendar.py`, `bot/crop_cycle_service.py`, `scripts/run_scheduled_alerts.py`, `scripts/test_agronomy_services.py` |

## Market & selling

| ID | Scenario | Status | Current repo reality | Evidence |
| --- | --- | --- | --- | --- |
| C1 | Farmer asks where to sell at best price | Partial | Price data pipelines exist, but the bot does not yet calculate transport-adjusted net price across mandis inside the WhatsApp flow. | `engine/price_pipeline.py`, `dashboard/src/components/MandiPrices.jsx` |
| C2 | Trader arrives at village, quotes low price | Partial | The underlying price data exists, but there is no dedicated compare-against-trader negotiation response yet. | `engine/price_pipeline.py` |
| C3 | Long-cycle crop: price prediction 6 months out | Implemented | The repo now has a dedicated long-cycle outlook service for crops like turmeric and dragon fruit that returns a probability range, confidence, and explicit buyer-confirmation guidance. | `engine/long_cycle_outlook.py`, `bot/scenario_logic.py`, `scripts/test_agronomy_services.py` |
| C4 | Farmer planted without buyer — harvest approaching, no buyer found | Partial | The bot now has a generic buyer-not-found escalation path that points the farmer toward FPO, e-NAM, and storage routes, but it does not yet have contact-level integrations. | `bot/scenario_logic.py` |

## Financial & loans

| ID | Scenario | Status | Current repo reality | Evidence |
| --- | --- | --- | --- | --- |
| D1 | Farmer shares loan details — very high interest rate | Implemented | The bot now converts monthly interest to annualized pressure, flags the 24% danger line used in the project, and points the farmer toward waiver and KCC options. | `data/nizamabad_district.py`, `bot/scenario_logic.py`, `bot/whatsapp_handler.py` |
| D2 | Farmer panicking about debt repayment deadline | Implemented | The bot now has a deadline-panic response that starts with calming language and then points to Rythu Bandhu, PM-KISAN, waiver, and restructure options. | `bot/scenario_logic.py` |
| D3 | Farmer asks about government schemes | Implemented | The bot now personalizes the scheme summary using acres and current loan burden, especially for Rythu Bandhu and the loan-waiver path. | `data/nizamabad_district.py`, `bot/scenario_logic.py`, `bot/whatsapp_handler.py` |
| D4 | Farmer considering selling land to repay debt | Implemented | The bot now has a dedicated 'do not sell land first' response that reroutes the farmer toward waiver, KCC, and restructure options before a land-sale decision. | `bot/scenario_logic.py` |

## Emotional & crisis

| ID | Scenario | Status | Current repo reality | Evidence |
| --- | --- | --- | --- | --- |
| E1 | Crop completely failed — farmer in deep distress | Implemented | The bot now acknowledges the distress and immediately pivots to documenting loss, agriculture-office follow-up, loan pressure relief, and KVK support. | `bot/scenario_logic.py` |
| E2 | Bot gave wrong recommendation — farmer lost money | Partial | The bot now has an accountability-style response and asks for actual yield/selling-rate context, but it still does not reconstruct the historical recommendation with stored evidence. | `bot/scenario_logic.py`, `engine/district_cap.py` |
| E3 | Farmer expresses extreme despair / suicidal ideation | Implemented | The bot now has an urgent crisis reply that tells the farmer not to stay alone and routes them to India's Tele-MANAS mental-health helplines. | `bot/scenario_logic.py` |

## Weather & environment

| ID | Scenario | Status | Current repo reality | Evidence |
| --- | --- | --- | --- | --- |
| F1 | Daily morning weather alert | Partial | The repo can now generate an on-demand morning weather snapshot, but it still does not proactively schedule and push daily alerts. | `engine/weather_pipeline.py`, `bot/scenario_logic.py` |
| F2 | Post-harvest drying alert — rain coming | Implemented | Drying alerts now evaluate hourly rain probability and emit urgent cover-now warnings when rain risk crosses the 60% / 3-hour threshold. | `bot/drying_alerts.py`, `bot/crop_cycle_service.py`, `scripts/run_scheduled_alerts.py`, `scripts/test_agronomy_services.py` |
| F3 | Evening full-night forecast during drying | Implemented | The drying alert service now emits a dedicated evening/night drying summary when the farmer is in drying phase. | `bot/drying_alerts.py`, `bot/crop_cycle_service.py`, `scripts/test_agronomy_services.py` |
| F4 | Monsoon delayed — farmer about to plant | Implemented | The bot now has a dedicated delayed-monsoon advisory that uses the short-term weather view and redirects the farmer away from high-water crops. | `engine/weather_pipeline.py` |

## Scale & district management

| ID | Scenario | Status | Current repo reality | Evidence |
| --- | --- | --- | --- | --- |
| G1 | Bot recommendation cap approaching for a crop | Partial | Cap pressure is computed and surfaced inside the engine, but there is no proactive alert when a cap is merely approaching. | `engine/crop_engine.py`, `engine/district_cap.py` |
| G2 | Bot has recommended same crop to 3,000 farmers — cap hit | Partial | The engine can stop recommending oversupplied crops, but there is no explicit high-scale explanation flow in the bot. | `engine/crop_engine.py`, `engine/district_cap.py` |

## Labour & operations

| ID | Scenario | Status | Current repo reality | Evidence |
| --- | --- | --- | --- | --- |
| H1 | Labour shortage at harvest | Partial | The bot now has a practical harvest-labour shortage reply, but it does not yet integrate with real labour pools or FPO networks. | `bot/scenario_logic.py` |
| H2 | Input cost has risen sharply | Implemented | The bot now has a dedicated input-cost pressure reply that surfaces lower-cost alternatives from the current recommendation set. | `engine/crop_engine.py`, `bot/scenario_logic.py` |

## Seeds & inputs

| ID | Scenario | Status | Current repo reality | Evidence |
| --- | --- | --- | --- | --- |
| I1 | Farmer asks which seed variety to buy | Partial | The bot now has a conservative seed-buying advisory, but it does not yet recommend named certified varieties from a maintained catalog. | `bot/scenario_logic.py` |
| I2 | Farmer bought wrong/counterfeit seeds | Implemented | The bot now tells the farmer to preserve the packet, bill, batch number, and photos, and escalate through the dealer and agriculture office. | `bot/scenario_logic.py` |
| I3 | Pesticide shop recommending unnecessary chemicals | Partial | The bot now explicitly warns the farmer not to buy extra chemicals blindly, but it still lacks the full diagnosis-linked exact-quantity enforcement envisioned in the spec. | `data/nizamabad_district.py`, `bot/scenario_logic.py` |

## Water & irrigation

| ID | Scenario | Status | Current repo reality | Evidence |
| --- | --- | --- | --- | --- |
| J1 | Canal water release timing alert | Implemented | The repo now has a canal-release ingest/evaluation service that reads a feed or local schedule, maps branch releases to mandals, and generates advance preparation alerts. | `bot/canal_alerts.py`, `bot/scenario_logic.py`, `data/canal_release_schedule.json`, `scripts/test_agronomy_services.py` |
| J2 | Drought conditions — crop water stress | Implemented | The bot now has a dedicated drought/water-stress reply that shifts the farmer toward lower-water crops and moisture-saving actions. | `engine/crop_engine.py`, `bot/scenario_logic.py` |

## Accessibility

| ID | Scenario | Status | Current repo reality | Evidence |
| --- | --- | --- | --- | --- |
| K1 | Farmer cannot type — voice only | Partial | Voice note transcription and voice reply paths exist and pass local smoke tests, but live reliability still depends on Twilio and Sarvam. | `bot/telugu_voice.py`, `bot/whatsapp_handler.py`, `scripts/test_whatsapp_voice.py` |
| K2 | Elderly farmer — describes crop problem in words, cannot send photo | Implemented | The bot now has a conservative text-only symptom triage path that gives caveated treatment guidance when the description matches a known crop pattern. | `bot/scenario_logic.py` |

## Inter-season

| ID | Scenario | Status | Current repo reality | Evidence |
| --- | --- | --- | --- | --- |
| L1 | Idle land between kharif and rabi — what to do | Implemented | The bot now has a dedicated idle-land advisory and recommends short-cycle inter-season options like green gram where they fit the local profile. | `data/nizamabad_district.py`, `engine/crop_engine.py`, `bot/scenario_logic.py` |
| L2 | End of season feedback collection | Implemented | The bot now has a structured end-of-season feedback prompt covering crop, yield, and realized selling rate/problem. | `bot/scenario_logic.py` |

## Special crops

| ID | Scenario | Status | Current repo reality | Evidence |
| --- | --- | --- | --- | --- |
| M1 | High-value crop (dragon fruit) — full 6-month monitoring | Implemented | Dragon fruit now has a dedicated 6-month specialty calendar with buyer activation from day 1 and stage-specific monitoring checkpoints. | `data/specialty_crops.py`, `engine/season_calendar.py`, `bot/scenario_logic.py`, `scripts/test_followup_scenarios.py` |
| M2 | Intercropping recommendation to maximise land use | Implemented | The bot now has a practical intercropping advisory path with simple crop-pair suggestions for risk spreading, though it is not yet fully engine-scored. | `engine/crop_engine.py`, `bot/scenario_logic.py` |

## Onboarding

| ID | Scenario | Status | Current repo reality | Evidence |
| --- | --- | --- | --- | --- |
| N1 | New farmer messages for the first time | Implemented | Progressive farmer profiling over 3-4 WhatsApp turns is working and already drives the engine. | `bot/farmer_profile.py`, `bot/whatsapp_handler.py` |
| N2 | Farmer refers another farmer | Implemented | The bot now has a referral handoff reply that tells the current farmer how another farmer can start their own onboarding flow. | `bot/scenario_logic.py` |

## Read This Correctly

The repo is already strong at the core crop-decision problem, onboarding, deployment, and dashboard visibility.
The big remaining gap is not structure; it is breadth. The 33-scenario spec includes disease, crisis handling, irrigation alerts, post-harvest logistics, and long-cycle monitoring that are intentionally broader than the current shipped surface.

