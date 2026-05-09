# User And Problem Validation

This file documents what the project is grounded in, what has been validated, and what is still unproven.

## Target User

The primary user is a small or mid-sized farmer in Nizamabad district, Telangana, making seasonal crop decisions under uncertainty.

The important constraints are practical:

- decisions happen before prices are known
- debt pressure changes the acceptable downside
- soil and water fit are local, not generic
- district oversupply can hurt everyone if many farmers choose the same crop
- WhatsApp voice notes are more realistic than a form-heavy web app for many users

## Source Of The Problem

The project is based on a real family farming problem rather than an invented startup scenario. The initial product question was:

```text
What should we plant this season if the recommendation has to respect soil, water, market pressure, and downside risk?
```

## Validation Done So Far

- Encoded a deterministic five-filter recommendation flow instead of relying only on a model or LLM.
- Tested the main Nandipet scenario where maize and soybean survive the filters while paddy, turmeric, and cotton are rejected.
- Built scenario coverage in `docs/scenario_coverage.md` so behavior can be reviewed outside the code.
- Added a WhatsApp and Telugu voice path because that matches the intended interaction channel.
- Added a public website so the decision logic can be evaluated visually by reviewers and non-technical users.

## What Is Not Claimed Yet

- This is not a certified agronomy advisory system.
- It has not yet been validated across many districts or crop seasons.
- It does not guarantee market prices or profits.
- Disease diagnosis is scaffolded and should be treated as experimental until trained and validated with real model weights.

## Next Validation Steps

1. Run 3-5 guided sessions with farmers or agriculture advisors.
2. Record confusing questions, rejected recommendations, and missing local context.
3. Compare recommendation outcomes against actual seasonal choices.
4. Add data freshness and confidence labels to every recommendation.
5. Convert the best field-test cases into regression scenarios.
