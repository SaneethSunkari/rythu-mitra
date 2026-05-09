# Changelog

This changelog summarizes meaningful product and engineering progress. It is written as portfolio evidence, not as a package release log.

## Current

- Added portfolio documentation for iteration history, roadmap, and user/problem validation.
- Clarified production boundaries around field testing, automated refreshes, and disease-model readiness.
- Connected README evaluation paths to scenario coverage, system tests, and deployment notes.

## v0.4 - Public Product Surface

- Added a public React website served through the FastAPI/Railway deployment.
- Built three product surfaces: personalized analysis, district state, and live market/weather context.
- Added dashboard export logic so the website can run from generated district and market context.
- Kept `/dashboard` as a compatibility route while making `/` the canonical product entrypoint.

## v0.3 - WhatsApp And Telugu Voice Flow

- Added FastAPI webhook routing for Twilio WhatsApp.
- Added progressive farmer profiling so the bot can collect mandal, acreage, soil, water, recent crops, and loan context across turns.
- Integrated Telugu speech-to-text and text-to-speech paths for voice-note interaction.
- Added conservative fallbacks for external voice APIs so the bot can still return text when audio generation is unavailable.

## v0.2 - District-Aware Crop Engine

- Built the five-filter recommendation engine: soil, water/weather, district supply cap, price range, and floor-price survivability.
- Added district planting-pressure logic to avoid recommending the same crop to too many farmers.
- Added crop, mandi, soil, scheme, weather, and price-history data layers for Nizamabad district.
- Added smoke tests for the Nandipet scenario and broader scenario coverage.

## v0.1 - Problem Framing And Data Model

- Framed the project around a real farming-family crop decision problem in Nizamabad, Telangana.
- Modeled mandal-level crop suitability, water constraints, market pressure, and crop economics.
- Created the first command-line test path for deterministic crop recommendations.
