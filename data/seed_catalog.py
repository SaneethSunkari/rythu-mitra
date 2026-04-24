"""Structured seed and variety guidance used by the bot and website."""

from __future__ import annotations


SEED_VARIETY_CATALOG = {
    "paddy": [
        {
            "name": "MTU 1010",
            "fit": "reliable grain market and broad Telangana familiarity",
            "duration_days": 135,
            "seed_rate_kg_per_acre": "12-15",
            "source": "PJTSAU rice quality and Telangana extension references",
            "notes": "Use only certified seed lots; better for farmers who want predictable paddy marketing.",
        },
        {
            "name": "JGL 24423",
            "fit": "state seed-distribution and local Telangana adaptation",
            "duration_days": 125,
            "seed_rate_kg_per_acre": "12-15",
            "source": "PJTSAU quality-seed exercise and rice extension references",
            "notes": "Useful where the farmer wants a Telangana-adapted option instead of a trader-pushed packet.",
        },
    ],
    "maize": [
        {
            "name": "DHM 117",
            "fit": "widely marketed Telangana maize hybrid",
            "duration_days": 105,
            "seed_rate_kg_per_acre": "8-10",
            "source": "PJTSAU maize hybrid commercialization references",
            "notes": "Buy only sealed branded packets with lot and germination label.",
        },
        {
            "name": "DHM 121",
            "fit": "strong grain hybrid for Northern Telangana",
            "duration_days": 105,
            "seed_rate_kg_per_acre": "8-10",
            "source": "PJTSAU maize hybrid commercialization references",
            "notes": "Better when the farmer wants a proven Telangana maize line instead of loose dealer seed.",
        },
        {
            "name": "DHM 206 (Telangana Makka-3)",
            "fit": "newer PJTSAU hybrid with strong grain potential",
            "duration_days": 105,
            "seed_rate_kg_per_acre": "8-10",
            "source": "PJTSAU 2024 DHM 206 commercialization note",
            "notes": "Prefer when a certified packet is available from an authorized outlet.",
        },
    ],
    "soybean": [
        {
            "name": "JS 335",
            "fit": "widely used soybean option for rainfed belt",
            "duration_days": 95,
            "seed_rate_kg_per_acre": "25-30",
            "source": "AICRP soybean and Telangana field usage references",
            "notes": "Good only if germination and treatment details are printed clearly on the bag.",
        },
        {
            "name": "MAUS 71",
            "fit": "balanced soybean option for black and mixed soils",
            "duration_days": 95,
            "seed_rate_kg_per_acre": "25-30",
            "source": "AICRP soybean field recommendations used in Telangana belt",
            "notes": "Use when the farmer wants a conservative, familiar soybean packet.",
        },
    ],
    "cotton": [
        {
            "name": "Certified Bt hybrid from Telangana-approved label",
            "fit": "only for black-cotton mandals where cotton is actually suitable",
            "duration_days": 160,
            "seed_rate_kg_per_acre": "0.6-0.8",
            "source": "Telangana extension practice for hybrid cotton packets",
            "notes": "Do not trust loose packets or handwritten dealer labels. Packet, lot number, and company seal are mandatory.",
        },
    ],
    "red_gram": [
        {
            "name": "WRGE 93",
            "fit": "Telangana pulse seed-distribution and short-duration preference",
            "duration_days": 150,
            "seed_rate_kg_per_acre": "4-5",
            "source": "PJTSAU seed-kit and pulse extension references",
            "notes": "Useful where the farmer wants a cleaner short-duration redgram line.",
        },
        {
            "name": "Asha (ICPL 87119)",
            "fit": "widely known redgram option with stable farmer familiarity",
            "duration_days": 165,
            "seed_rate_kg_per_acre": "4-5",
            "source": "PJTSAU and pulse extension usage references",
            "notes": "Works better when the farmer is comfortable with a longer pulse duration.",
        },
    ],
    "green_gram": [
        {
            "name": "MGG 385",
            "fit": "short-duration green gram for gap-filling and idle-land windows",
            "duration_days": 65,
            "seed_rate_kg_per_acre": "8-10",
            "source": "PJTSAU quality-seed exercise references",
            "notes": "Good for quick between-season windows when water is limited.",
        },
    ],
    "bengal_gram": [
        {
            "name": "NBeG 47",
            "fit": "widely accepted gram option in Telangana belt",
            "duration_days": 105,
            "seed_rate_kg_per_acre": "25-30",
            "source": "PJTSAU chickpea extension references",
            "notes": "Prefer only certified bags; avoid mixed lots from local traders.",
        },
    ],
    "black_gram": [
        {
            "name": "TBG 104",
            "fit": "black gram fit for short-duration pulse slot",
            "duration_days": 75,
            "seed_rate_kg_per_acre": "8-10",
            "source": "Telangana pulse extension references",
            "notes": "Use with treated seed only; ideal when the farmer wants a quick pulse crop.",
        },
    ],
    "groundnut": [
        {
            "name": "Kadiri 6",
            "fit": "groundnut option for dryland red-soil pockets",
            "duration_days": 110,
            "seed_rate_kg_per_acre": "55-65",
            "source": "South Indian groundnut extension references commonly used in Telangana",
            "notes": "Prefer pods from certified source, not open gunny-bag seed.",
        },
    ],
    "sesame": [
        {
            "name": "YLM 66",
            "fit": "sesame line used in Telangana dryland conditions",
            "duration_days": 90,
            "seed_rate_kg_per_acre": "1.5-2.0",
            "source": "Telangana oilseed extension references",
            "notes": "Low seed volume means packet authenticity matters a lot.",
        },
    ],
    "jowar": [
        {
            "name": "CSV 15",
            "fit": "conservative sorghum option for lower-risk dryland planning",
            "duration_days": 105,
            "seed_rate_kg_per_acre": "3-4",
            "source": "Sorghum extension references used in Telangana belt",
            "notes": "Useful when farmer priority is survivability over flashy returns.",
        },
    ],
    "turmeric": [
        {
            "name": "Prathibha",
            "fit": "long-duration turmeric line for established turmeric growers",
            "duration_days": 270,
            "seed_rate_kg_per_acre": "800-1000 kg rhizomes",
            "source": "Turmeric extension references used in Telangana belt",
            "notes": "Select only healthy, disease-free mother rhizomes from a trusted source.",
        },
    ],
}
