# Roadmap

Rythu Mitra is already useful as a portfolio-grade product demo. The roadmap below focuses on making it stronger as a field-ready decision support tool.

## Now

- Keep the crop engine deterministic and explainable.
- Preserve the district supply-pressure guardrail as a core product principle.
- Maintain scenario coverage for the main Nizamabad profiles in `docs/scenario_coverage.md`.
- Keep the website and WhatsApp webhook deployable from the same repo.

## Next

- Run structured field tests with 3-5 farmers or agriculture advisors.
- Record which recommendations users trust, reject, or want explained differently.
- Add a feedback log for recommendation outcomes and farmer objections.
- Automate the weather and mandi refresh path instead of relying on manual/cache updates.
- Add confidence labels to recommendations based on data freshness and signal quality.

## Later

- Add crop-cycle follow-up reminders after a farmer chooses a crop.
- Build a human-review queue for recommendations with weak or stale data.
- Add support for additional districts only after the Nizamabad data model is proven.
- Calibrate disease detection with real trained weights before presenting it as a reliable feature.
- Convert scenario examples into a small regression suite that runs in CI.

## Done Criteria For Production Readiness

- Field-test notes exist for at least 10 real recommendation sessions.
- Every external data source has freshness metadata in the UI and bot response.
- The bot can explain why a crop was rejected in farmer-friendly Telugu.
- High-risk recommendations have a conservative fallback or human-review path.
- Deployment, rollback, and environment setup are documented end to end.
