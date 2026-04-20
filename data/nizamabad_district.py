"""
Nizamabad District - Ground Truth Database

Core recommendation crops are sourced from PJTSAU / Telangana Agriculture Dept
and district-level references already curated for this project.

Note:
- The mandal map in this project intentionally follows the founder's broader
  working geography around legacy/undivided Nizamabad coverage so field users
  like Kamareddy/Banswada-side farmers are still represented.
- 14 crop profiles are now recommendation-ready in the engine.
- 5 dryland supplementary crops were backfilled from official Telangana /
  PJTSAU sources and are protected by season filtering before recommendation.
- Castor remains inactive until its cost side is backfilled with the same level
  of source support as the rest of the matrix.
"""

# ── MANDALS (36 total) ─────────────────────────────────────────────────────────
# soil_zone: "black_cotton" | "deep_calcareous" | "red_clayey" | "mixed"
# water:     "canal" | "rainfed" | "mixed" | "borewell"
# canal source: Sri Ram Sagar Project (SRSP) covers eastern mandals

MANDALS = {
    "nandipet": {
        "soil_zone": "deep_calcareous",
        "water": "mixed",           # SRSP canal + rainfed
        "primary_crops": ["paddy", "turmeric", "maize", "soybean"],
        "unsuitable_crops": ["cotton"],
        "nearest_mandis": [
            {"name": "Nandipet", "distance_km": 10},
            {"name": "Armur", "distance_km": 22},
            {"name": "Nizamabad", "distance_km": 42},
        ],
        "villages": 47,
        "notes": "Annaram village is here. Godavari river border on east. Local deep calcareous tracts are not treated as cotton-suitable in this project.",
    },
    "nizamabad_rural": {
        "soil_zone": "mixed",
        "water": "mixed",
        "primary_crops": ["paddy", "maize", "turmeric", "vegetables"],
        "nearest_mandis": [
            {"name": "Nizamabad", "distance_km": 8},
        ],
        "villages": 38,
    },
    "bodhan": {
        "soil_zone": "black_cotton",
        "water": "canal",           # SRSP main canal
        "primary_crops": ["sugarcane", "paddy", "cotton", "soybean"],
        "nearest_mandis": [
            {"name": "Bodhan", "distance_km": 5},
            {"name": "Nizamabad", "distance_km": 35},
        ],
        "villages": 52,
        "notes": "Sugar mill present. Only mandal where sugarcane is viable.",
        "sugar_mill": True,
    },
    "armur": {
        "soil_zone": "deep_calcareous",
        "water": "mixed",
        "primary_crops": ["paddy", "maize", "turmeric", "soybean"],
        "nearest_mandis": [
            {"name": "Armur", "distance_km": 4},
            {"name": "Nizamabad", "distance_km": 30},
        ],
        "villages": 41,
    },
    "kamareddy": {
        "soil_zone": "red_clayey",
        "water": "rainfed",
        "primary_crops": ["maize", "soybean", "red_gram", "sunflower"],
        "nearest_mandis": [
            {"name": "Kamareddy", "distance_km": 3},
            {"name": "Nizamabad", "distance_km": 55},
        ],
        "villages": 60,
    },
    "banswada": {
        "soil_zone": "red_clayey",
        "water": "rainfed",
        "primary_crops": ["maize", "soybean", "red_gram"],
        "nearest_mandis": [
            {"name": "Banswada", "distance_km": 4},
            {"name": "Kamareddy", "distance_km": 18},
        ],
        "villages": 55,
    },
    "balkonda": {
        "soil_zone": "black_cotton",
        "water": "rainfed",
        "primary_crops": ["cotton", "soybean", "maize", "red_gram"],
        "nearest_mandis": [
            {"name": "Balkonda", "distance_km": 5},
            {"name": "Nizamabad", "distance_km": 45},
        ],
        "villages": 44,
        "notes": "Black cotton soil well-suited for cotton. Low local competition.",
    },
    "yellareddy": {
        "soil_zone": "mixed",
        "water": "mixed",
        "primary_crops": ["paddy", "maize", "turmeric"],
        "nearest_mandis": [
            {"name": "Yellareddy", "distance_km": 3},
            {"name": "Nizamabad", "distance_km": 50},
        ],
        "villages": 48,
    },
    "kotagiri": {
        "soil_zone": "deep_calcareous",
        "water": "mixed",
        "primary_crops": ["turmeric", "paddy", "maize"],
        "nearest_mandis": [
            {"name": "Nizamabad", "distance_km": 25},
            {"name": "Armur", "distance_km": 20},
        ],
        "villages": 35,
    },
    "varni": {
        "soil_zone": "black_cotton",
        "water": "rainfed",
        "primary_crops": ["cotton", "soybean", "red_gram"],
        "nearest_mandis": [
            {"name": "Nizamabad", "distance_km": 15},
        ],
        "villages": 30,
    },
    # remaining 26 mandals — representative data by zone
    "dichpally": {"soil_zone": "deep_calcareous", "water": "canal", "primary_crops": ["paddy", "turmeric", "maize"], "nearest_mandis": [{"name": "Nizamabad", "distance_km": 20}], "villages": 40},
    "navipet": {"soil_zone": "deep_calcareous", "water": "mixed", "primary_crops": ["paddy", "maize", "soybean"], "nearest_mandis": [{"name": "Nizamabad", "distance_km": 30}], "villages": 33},
    "mosra": {"soil_zone": "red_clayey", "water": "rainfed", "primary_crops": ["maize", "soybean", "red_gram"], "nearest_mandis": [{"name": "Kamareddy", "distance_km": 25}], "villages": 28},
    "tadwai": {"soil_zone": "red_clayey", "water": "rainfed", "primary_crops": ["maize", "soybean"], "nearest_mandis": [{"name": "Nizamabad", "distance_km": 60}], "villages": 22},
    "bheemgal": {"soil_zone": "red_clayey", "water": "rainfed", "primary_crops": ["maize", "red_gram", "sunflower"], "nearest_mandis": [{"name": "Kamareddy", "distance_km": 30}], "villages": 25},
    "kubeer": {"soil_zone": "black_cotton", "water": "rainfed", "primary_crops": ["cotton", "soybean"], "nearest_mandis": [{"name": "Balkonda", "distance_km": 15}], "villages": 20},
    "renjal": {"soil_zone": "deep_calcareous", "water": "mixed", "primary_crops": ["paddy", "turmeric"], "nearest_mandis": [{"name": "Armur", "distance_km": 15}], "villages": 32},
    "indalwai": {"soil_zone": "mixed", "water": "rainfed", "primary_crops": ["maize", "soybean", "paddy"], "nearest_mandis": [{"name": "Nizamabad", "distance_km": 35}], "villages": 29},
    "pitlam": {"soil_zone": "deep_calcareous", "water": "canal", "primary_crops": ["paddy", "turmeric", "maize"], "nearest_mandis": [{"name": "Armur", "distance_km": 18}], "villages": 38},
    "madnoor": {"soil_zone": "black_cotton", "water": "rainfed", "primary_crops": ["cotton", "soybean", "red_gram"], "nearest_mandis": [{"name": "Nizamabad", "distance_km": 40}], "villages": 35},
    "morthad": {"soil_zone": "red_clayey", "water": "rainfed", "primary_crops": ["maize", "soybean", "sunflower"], "nearest_mandis": [{"name": "Banswada", "distance_km": 20}], "villages": 27},
    "sarangapur": {"soil_zone": "mixed", "water": "mixed", "primary_crops": ["paddy", "maize", "soybean"], "nearest_mandis": [{"name": "Nizamabad", "distance_km": 25}], "villages": 31},
    "jakranpally": {"soil_zone": "deep_calcareous", "water": "mixed", "primary_crops": ["paddy", "turmeric", "maize"], "nearest_mandis": [{"name": "Armur", "distance_km": 25}], "villages": 36},
    "chandur": {"soil_zone": "black_cotton", "water": "rainfed", "primary_crops": ["cotton", "soybean", "red_gram"], "nearest_mandis": [{"name": "Bodhan", "distance_km": 20}], "villages": 24},
    "rudrur": {"soil_zone": "deep_calcareous", "water": "canal", "primary_crops": ["paddy", "turmeric", "sugarcane"], "nearest_mandis": [{"name": "Bodhan", "distance_km": 15}], "villages": 40, "sugar_mill": True},
    "sirkonda": {"soil_zone": "red_clayey", "water": "rainfed", "primary_crops": ["maize", "red_gram"], "nearest_mandis": [{"name": "Kamareddy", "distance_km": 20}], "villages": 18},
    "bichkunda": {"soil_zone": "red_clayey", "water": "rainfed", "primary_crops": ["red_gram", "maize", "soybean"], "nearest_mandis": [{"name": "Banswada", "distance_km": 28}, {"name": "Kamareddy", "distance_km": 42}], "villages": 34, "notes": "Dryland pulse and oilseed belt toward Karnataka/Maharashtra side."},
    "bhiknoor": {"soil_zone": "mixed", "water": "mixed", "primary_crops": ["maize", "soybean", "paddy"], "nearest_mandis": [{"name": "Kamareddy", "distance_km": 16}], "villages": 31},
    "birkoor": {"soil_zone": "red_clayey", "water": "rainfed", "primary_crops": ["maize", "soybean", "red_gram"], "nearest_mandis": [{"name": "Kamareddy", "distance_km": 20}, {"name": "Banswada", "distance_km": 18}], "villages": 29},
    "domakonda": {"soil_zone": "red_clayey", "water": "rainfed", "primary_crops": ["maize", "soybean", "sunflower"], "nearest_mandis": [{"name": "Kamareddy", "distance_km": 18}], "villages": 30},
    "gandhari": {"soil_zone": "black_cotton", "water": "rainfed", "primary_crops": ["cotton", "soybean", "red_gram"], "nearest_mandis": [{"name": "Banswada", "distance_km": 24}, {"name": "Kamareddy", "distance_km": 36}], "villages": 39},
    "jukkal": {"soil_zone": "black_cotton", "water": "rainfed", "primary_crops": ["cotton", "red_gram", "soybean"], "nearest_mandis": [{"name": "Banswada", "distance_km": 34}, {"name": "Kamareddy", "distance_km": 48}], "villages": 35},
    "lingampet": {"soil_zone": "mixed", "water": "rainfed", "primary_crops": ["maize", "red_gram", "sunflower"], "nearest_mandis": [{"name": "Kamareddy", "distance_km": 32}], "villages": 27},
    "machareddy": {"soil_zone": "red_clayey", "water": "rainfed", "primary_crops": ["maize", "soybean", "red_gram"], "nearest_mandis": [{"name": "Kamareddy", "distance_km": 14}], "villages": 33},
    "nagareddipet": {"soil_zone": "red_clayey", "water": "rainfed", "primary_crops": ["maize", "soybean", "sunflower"], "nearest_mandis": [{"name": "Kamareddy", "distance_km": 12}], "villages": 25},
    "nizamsagar": {"soil_zone": "deep_calcareous", "water": "mixed", "primary_crops": ["paddy", "maize", "soybean"], "nearest_mandis": [{"name": "Banswada", "distance_km": 22}, {"name": "Kamareddy", "distance_km": 30}], "villages": 29, "notes": "Tank command influence gives some irrigation support."},
}

# ── MANDIS (6 major markets) ───────────────────────────────────────────────────
MANDIS = {
    "Nizamabad": {
        "established": 1933,
        "location": "Shradhanand Gunj",
        "area_acres": 67,
        "registered_traders": 103,
        "e_nam": True,
        "coords": (18.6714, 78.0942),
        "crops_traded": ["turmeric", "paddy", "maize", "soybean", "red_gram", "sunflower", "cotton"],
    },
    "Armur": {
        "established": 1965,
        "coords": (18.7939, 78.2836),
        "crops_traded": ["paddy", "maize", "turmeric", "soybean"],
        "registered_traders": 42,
        "e_nam": True,
    },
    "Bodhan": {
        "established": 1958,
        "coords": (18.6647, 77.9008),
        "crops_traded": ["sugarcane", "paddy", "cotton", "soybean"],
        "registered_traders": 38,
        "e_nam": True,
    },
    "Kamareddy": {
        "established": 1971,
        "coords": (18.3200, 78.3400),
        "crops_traded": ["maize", "soybean", "red_gram", "sunflower", "cotton"],
        "registered_traders": 35,
        "e_nam": True,
    },
    "Nandipet": {
        "established": 1980,
        "coords": (18.6500, 78.2500),
        "crops_traded": ["paddy", "turmeric", "maize"],
        "registered_traders": 18,
        "e_nam": False,
        "notes": "Smaller local market. Farmers often prefer Armur or Nizamabad for better price.",
    },
    "Balkonda": {
        "established": 1975,
        "coords": (18.8800, 77.9800),
        "crops_traded": ["cotton", "soybean", "maize", "red_gram"],
        "registered_traders": 22,
        "e_nam": True,
    },
}

# ── CROP DATABASE ──────────────────────────────────────────────────────────────
# Prices: verified from Agmarknet / PJTSAU bulletins / Deccan Chronicle 2024-25
# Costs: PJTSAU cost of cultivation studies, North Telangana Zone
# Yields: PJTSAU district averages — NOT state averages (state inflated by delta)

CROPS = {
    "paddy": {
        "telugu_name": "వరి",
        "season": ["kharif"],       # Jun–Oct
        "soil_compatible": ["deep_calcareous", "black_cotton", "mixed"],
        "water_requirement": "high",    # >700mm or canal
        "input_cost_per_acre": 18000,   # seeds + fertilizer + pesticide + labor
        "yield_qtl_per_acre": {
            "canal_irrigated": {"min": 22, "avg": 26, "max": 31},
            "rainfed": {"min": 12, "avg": 16, "max": 20},
        },
        "price_history_qtl": {          # Nizamabad APMC, harvest month (Oct-Nov)
            2020: {"min": 1750, "max": 1950, "avg": 1840},
            2021: {"min": 1780, "max": 2050, "avg": 1910},
            2022: {"min": 1800, "max": 2100, "avg": 1940},
            2023: {"min": 1820, "max": 2150, "avg": 1970},
            2024: {"min": 1880, "max": 2389, "avg": 2050},  # MSP ₹2389 with ₹500 bonus
        },
        "msp_2024": 2389,
        "msp_procurement_reach_pct": 58,    # Only 58% of farmers actually received MSP
        "district_acreage_2024": 429000,    # acres under paddy, Nizamabad dist
        "safe_cap_acres": 400000,           # above this → oversupply
        "grow_duration_days": 120,
        "monitoring_schedule": [
            {"day": 10, "stage": "tillering", "check": "Brown spot, nitrogen deficiency"},
            {"day": 20, "stage": "tillering", "check": "Blast disease early signs"},
            {"day": 30, "stage": "tillering", "check": "BLB, sheath rot"},
            {"day": 40, "stage": "panicle_init", "check": "Neck blast, sheath blight"},
            {"day": 55, "stage": "flowering", "check": "Blast, false smut"},
            {"day": 70, "stage": "grain_fill", "check": "Brown plant hopper"},
            {"day": 90, "stage": "maturity", "check": "Grain discoloration"},
        ],
        "common_diseases": {
            "blast": {
                "telugu": "బ్లాస్ట్",
                "symptoms": "Round/diamond shaped spots on leaves, gray center brown border",
                "treatment": "Tricyclazole 75WP @ 1g per pump",
                "cost_per_acre": 120,
                "risk_conditions": "temp 25-28C + humidity >90% + cloudy 3+ days",
            },
            "brown_spot": {
                "telugu": "బ్రౌన్ స్పాట్",
                "symptoms": "Brown oval spots on leaves, nutrient deficient fields",
                "treatment": "Mancozeb 75WP @ 2.5g per pump + Ferrous Sulphate foliar",
                "cost_per_acre": 150,
            },
            "blb": {
                "telugu": "బాక్టీరియల్ లీఫ్ బ్లైట్",
                "symptoms": "Water-soaked leaf margins turning yellow then white",
                "treatment": "Copper Oxychloride 50WP @ 3g per pump",
                "cost_per_acre": 180,
            },
        },
    },

    "turmeric": {
        "telugu_name": "పసుపు",
        "season": ["kharif"],           # Jun–Mar (8-9 month crop)
        "soil_compatible": ["deep_calcareous", "red_clayey"],
        "water_requirement": "medium",
        "input_cost_per_acre": 55000,   # raw finger turmeric (NOT processed)
        "yield_qtl_per_acre": {
            "canal_irrigated": {"min": 20, "avg": 27, "max": 35},  # raw yield
            "rainfed": {"min": 15, "avg": 20, "max": 25},
        },
        "price_history_qtl": {          # Nizamabad APMC
            2020: {"min": 5800, "max": 7200, "avg": 6400},
            2021: {"min": 6200, "max": 8500, "avg": 7100},
            2022: {"min": 6500, "max": 9000, "avg": 7600},
            2023: {"min": 6000, "max": 8000, "avg": 6800},  # price crash year
            2024: {"min": 10200, "max": 14000, "avg": 11600},  # spike year
            2025: {"min": 9009, "max": 10200, "avg": 9600},  # current (cooling)
        },
        "district_acreage_2024": 92840,     # 9284 hectares × 2.47... but using acres directly: ~22941 acres PJTSAU
        "safe_cap_acres": 60000,            # above this → oversupply risk HIGH
        "grow_duration_days": 270,
        "monitoring_schedule": [
            {"day": 30, "stage": "establishment", "check": "Rhizome rot early signs, shoot borer"},
            {"day": 60, "stage": "vegetative", "check": "Leaf blotch, rhizome rot"},
            {"day": 90, "stage": "vegetative", "check": "Shoot borer damage"},
            {"day": 120, "stage": "vegetative", "check": "Leaf blotch, nutrient deficiency"},
            {"day": 150, "stage": "late_vegetative", "check": "Rhizome rot"},
            {"day": 180, "stage": "pre_harvest", "check": "Rhizome rot, nematodes"},
            {"day": 240, "stage": "maturity", "check": "Final rhizome health check"},
        ],
        "common_diseases": {
            "rhizome_rot": {
                "telugu": "దుంప కుళ్ళు",
                "symptoms": "Yellowing leaves, pseudostem collapse on gentle pull, rhizomes brown",
                "treatment": "Metalaxyl + Mancozeb drench @ 2.5g per liter, remove infected clumps",
                "cost_per_acre": 800,
                "storage_loss_pct": "50-80% if untreated",
                "note": "Studied specifically in Nizamabad district. Most destructive turmeric disease.",
            },
            "leaf_blotch": {
                "telugu": "ఆకు మచ్చ",
                "symptoms": "Brown spots with yellow halo on leaves",
                "treatment": "Mancozeb 75WP @ 2.5g per pump",
                "cost_per_acre": 200,
            },
        },
    },

    "maize": {
        "telugu_name": "మొక్కజొన్న",
        "season": ["kharif", "rabi"],
        "soil_compatible": ["red_clayey", "deep_calcareous", "mixed"],
        "water_requirement": "medium",
        "input_cost_per_acre": 12000,
        "yield_qtl_per_acre": {
            "canal_irrigated": {"min": 25, "avg": 32, "max": 40},
            "rainfed": {"min": 18, "avg": 24, "max": 30},
        },
        "price_history_qtl": {          # Nizamabad NCDEX spot / APMC
            2020: {"min": 1600, "max": 1900, "avg": 1740},
            2021: {"min": 1700, "max": 2100, "avg": 1880},
            2022: {"min": 1900, "max": 2400, "avg": 2150},
            2023: {"min": 2000, "max": 2600, "avg": 2300},
            2024: {"min": 1900, "max": 3000, "avg": 2380},  # Sep 2024 high ₹3000
        },
        "district_acreage_2024": 180000,
        "safe_cap_acres": 250000,
        "grow_duration_days": 90,
        "monitoring_schedule": [
            {"day": 15, "stage": "seedling", "check": "Fall army worm, damping off"},
            {"day": 30, "stage": "vegetative", "check": "Fall army worm damage in whorl"},
            {"day": 45, "stage": "tasseling", "check": "Northern leaf blight"},
            {"day": 55, "stage": "silking", "check": "Common rust, fall army worm"},
            {"day": 70, "stage": "grain_fill", "check": "Grain mold, stem borer"},
        ],
        "common_diseases": {
            "fall_army_worm": {
                "telugu": "ఫాల్ ఆర్మీ వార్మ్",
                "symptoms": "Ragged holes in leaves, frass in whorl",
                "treatment": "Emamectin Benzoate 5SG @ 0.4g per liter, spray in whorl",
                "cost_per_acre": 400,
            },
            "northern_leaf_blight": {
                "telugu": "ఆకు తెగులు",
                "symptoms": "Long cigar-shaped gray-green lesions on leaves",
                "treatment": "Mancozeb 75WP @ 2.5g per pump",
                "cost_per_acre": 150,
            },
        },
    },

    "soybean": {
        "telugu_name": "సోయాబీన్",
        "season": ["kharif"],
        "soil_compatible": ["black_cotton", "red_clayey", "deep_calcareous"],
        "water_requirement": "low",     # rainfed works well
        "input_cost_per_acre": 10000,
        "yield_qtl_per_acre": {
            "canal_irrigated": {"min": 8, "avg": 12, "max": 16},
            "rainfed": {"min": 6, "avg": 9, "max": 12},
        },
        "price_history_qtl": {
            2020: {"min": 3600, "max": 4200, "avg": 3900},
            2021: {"min": 4200, "max": 5800, "avg": 5100},
            2022: {"min": 4500, "max": 6200, "avg": 5300},
            2023: {"min": 4000, "max": 5500, "avg": 4700},
            2024: {"min": 4200, "max": 5800, "avg": 5480},
        },
        "district_acreage_2024": 95000,
        "safe_cap_acres": 150000,
        "grow_duration_days": 95,
        "monitoring_schedule": [
            {"day": 20, "stage": "vegetative", "check": "Girdle beetle, leaf eating caterpillar"},
            {"day": 35, "stage": "flowering", "check": "Pod borer, yellow mosaic virus"},
            {"day": 50, "stage": "pod_formation", "check": "Pod borer — CRITICAL STAGE"},
            {"day": 65, "stage": "pod_fill", "check": "Pod borer, stem fly"},
            {"day": 80, "stage": "maturity", "check": "Pod shattering check"},
        ],
    },

    "cotton": {
        "telugu_name": "పత్తి",
        "season": ["kharif"],
        "soil_compatible": ["black_cotton", "deep_calcareous"],
        "water_requirement": "low",     # rainfed
        "input_cost_per_acre": 15000,
        "yield_qtl_per_acre": {
            "canal_irrigated": {"min": 8, "avg": 12, "max": 16},
            "rainfed": {"min": 5, "avg": 8, "max": 12},
        },
        "price_history_qtl": {          # lint cotton, Adilabad/Nagpur buyers
            2020: {"min": 4800, "max": 6200, "avg": 5400},
            2021: {"min": 5500, "max": 9000, "avg": 7200},
            2022: {"min": 6000, "max": 9500, "avg": 7800},
            2023: {"min": 5200, "max": 7000, "avg": 6100},
            2024: {"min": 5500, "max": 7200, "avg": 6400},
        },
        "district_acreage_2024": 18000,  # LOW — opportunity gap
        "safe_cap_acres": 80000,
        "grow_duration_days": 160,
        "nearest_buyers": ["Adilabad mills", "Nagpur cotton traders", "Karimnagar ginning"],
        "monitoring_schedule": [
            {"day": 20, "stage": "seedling", "check": "Aphids, jassids, thrips"},
            {"day": 40, "stage": "squaring", "check": "Bollworm early signs"},
            {"day": 60, "stage": "flowering", "check": "American/Pink/Spotted bollworm"},
            {"day": 80, "stage": "boll_dev", "check": "Bollworm — CRITICAL"},
            {"day": 110, "stage": "boll_open", "check": "Sucking pests, boll rot"},
        ],
    },

    "red_gram": {
        "telugu_name": "కందులు",
        "season": ["kharif"],
        "soil_compatible": ["red_clayey", "deep_calcareous", "mixed"],
        "water_requirement": "low",
        "input_cost_per_acre": 7000,
        "yield_qtl_per_acre": {
            "rainfed": {"min": 4, "avg": 6, "max": 9},
        },
        "price_history_qtl": {
            2020: {"min": 4500, "max": 6000, "avg": 5200},
            2021: {"min": 5000, "max": 7000, "avg": 6000},
            2022: {"min": 5500, "max": 7500, "avg": 6500},
            2023: {"min": 6000, "max": 8000, "avg": 7000},
            2024: {"min": 6500, "max": 9000, "avg": 7800},
        },
        "district_acreage_2024": 45000,
        "safe_cap_acres": 80000,
        "grow_duration_days": 180,
    },

    "sunflower": {
        "telugu_name": "పొద్దుతిరుగుడు",
        "season": ["rabi"],             # Nov–Mar
        "soil_compatible": ["red_clayey", "deep_calcareous", "black_cotton"],
        "water_requirement": "low",
        "input_cost_per_acre": 8000,
        "yield_qtl_per_acre": {
            "rainfed": {"min": 4, "avg": 6, "max": 9},
        },
        "price_history_qtl": {
            2020: {"min": 4200, "max": 5500, "avg": 4800},
            2021: {"min": 4500, "max": 6000, "avg": 5200},
            2022: {"min": 5000, "max": 7000, "avg": 6000},
            2023: {"min": 5000, "max": 6500, "avg": 5700},
            2024: {"min": 5200, "max": 7000, "avg": 6100},
        },
        "district_acreage_2024": 22000,
        "safe_cap_acres": 60000,
        "grow_duration_days": 90,
        "notes": "Nizamabad is one of largest sunflower producers in Telangana. Underutilized.",
    },

    "green_gram": {
        "telugu_name": "పెసలు",
        "season": ["zaid"],             # Mar–May — BETWEEN SEASON GAP FILLER
        "soil_compatible": ["red_clayey", "deep_calcareous", "mixed", "black_cotton"],
        "water_requirement": "low",
        "input_cost_per_acre": 3500,
        "yield_qtl_per_acre": {
            "rainfed": {"min": 3, "avg": 4.5, "max": 6},
        },
        "price_history_qtl": {
            2020: {"min": 4500, "max": 6000, "avg": 5200},
            2021: {"min": 5000, "max": 6500, "avg": 5800},
            2022: {"min": 5500, "max": 7000, "avg": 6300},
            2023: {"min": 6000, "max": 7500, "avg": 6800},
            2024: {"min": 6500, "max": 8000, "avg": 7200},
        },
        "district_acreage_2024": 12000,
        "safe_cap_acres": 100000,       # barely grown — huge gap
        "grow_duration_days": 60,
        "notes": "45-60 day crop. Planted between kharif and rabi on idle land. Fixes nitrogen.",
    },

    "sugarcane": {
        "telugu_name": "చెరకు",
        "season": ["kharif"],
        "soil_compatible": ["deep_calcareous", "black_cotton"],
        "water_requirement": "very_high",
        "input_cost_per_acre": 35000,
        "yield_qtl_per_acre": {
            "canal_irrigated": {"min": 250, "avg": 320, "max": 400},
        },
        "price_qtl": 370,               # Fixed govt price — no market fluctuation
        "district_acreage_2024": 25000,
        "safe_cap_acres": 40000,
        "grow_duration_days": 360,
        "mill_required": True,          # ONLY viable near Bodhan / Rudrur mills
        "viable_mandals": ["bodhan", "rudrur", "dichpally"],
        "notes": "ONLY recommend if farmer is within 30km of Bodhan or Rudrur sugar mill.",
    },
    "bengal_gram": {
        "telugu_name": "సెనగలు",
        "season": ["rabi"],
        "soil_compatible": ["red_clayey", "deep_calcareous", "black_cotton"],
        "water_requirement": "low",
        "input_cost_per_acre": 20582,
        "yield_qtl_per_acre": {
            "rainfed": {"min": 5.14, "avg": 5.14, "max": 5.14},
        },
        "price_history_qtl": {
            2020: {"min": 5100, "max": 5100, "avg": 5100},
            2021: {"min": 5230, "max": 5230, "avg": 5230},
            2022: {"min": 5335, "max": 5335, "avg": 5335},
            2023: {"min": 5440, "max": 5440, "avg": 5440},
            2024: {"min": 5650, "max": 5650, "avg": 5650},
            2025: {"min": 5300, "max": 5600, "avg": 5450},
        },
        "district_acreage_legacy_hectares": 2790,
        "district_acreage_reference_acres": 6894,
        "district_acreage_reference_year": "2016",
        "grow_duration_days": 105,
        "monitoring_schedule": [
            {"day": 25, "stage": "vegetative", "check": "Wilt patches, cutworm, leaf miner"},
            {"day": 45, "stage": "flowering", "check": "Pod borer early entry"},
            {"day": 65, "stage": "pod_fill", "check": "Helicoverpa - CRITICAL"},
        ],
        "common_diseases": {
            "wilt": {"telugu": "విల్ట్", "symptoms": "Sudden drying of branches/plants", "treatment": "Remove wilted plants and manage seed treatment in next crop"},
            "pod_borer": {"telugu": "పాడ్ బోరర్", "symptoms": "Larvae feed inside pods", "treatment": "Need-based pod borer spray at flowering/pod stage"},
        },
        "data_status": "economics_backfilled_from_official_sources",
        "active_for_recommendation": True,
        "source_notes": [
            "Yield derived from PJTSAU cost of cultivation and cost of production tables for Bengal gram, 2018-19 to 2020-21.",
            "MSP history sourced from PIB MSP releases for RMS 2020-21 to RMS 2024-25.",
            "2025 price range sourced from PJTSAU AMIC Bengalgram Outlook, January 2025.",
            "District acreage baseline sourced from DES Telangana Nizamabad district profile.",
        ],
        "notes": "Dryland rabi pulse fit for Kamareddy-Nizamabad belt; season filter must pass before recommendation.",
    },
    "black_gram": {
        "telugu_name": "మినుములు",
        "season": ["kharif", "rabi"],
        "soil_compatible": ["red_clayey", "deep_calcareous", "black_cotton", "mixed"],
        "water_requirement": "low",
        "input_cost_per_acre": 20377,
        "yield_qtl_per_acre": {
            "rainfed": {"min": 5.34, "avg": 5.34, "max": 5.34},
        },
        "price_history_qtl": {
            2020: {"min": 6000, "max": 6000, "avg": 6000},
            2021: {"min": 6300, "max": 6300, "avg": 6300},
            2022: {"min": 6600, "max": 6600, "avg": 6600},
            2023: {"min": 6950, "max": 6950, "avg": 6950},
            2024: {"min": 7560, "max": 8170, "avg": 7865},
        },
        "district_acreage_legacy_hectares": 929,
        "district_acreage_reference_acres": 2296,
        "district_acreage_reference_year": "2016",
        "grow_duration_days": 75,
        "monitoring_schedule": [
            {"day": 20, "stage": "vegetative", "check": "Leaf spot, sucking pests"},
            {"day": 35, "stage": "flowering", "check": "Yellow mosaic virus"},
            {"day": 50, "stage": "pod_formation", "check": "Pod borer, powdery mildew"},
        ],
        "common_diseases": {
            "yellow_mosaic": {"telugu": "యెల్లో మోసాయిక్", "symptoms": "Yellow mosaic patches on leaves", "treatment": "Whitefly control and rouging"},
            "powdery_mildew": {"telugu": "పౌడరీ మిల్డ్యూ", "symptoms": "White powdery growth on leaves", "treatment": "Sulphur-based fungicide when required"},
        },
        "data_status": "economics_backfilled_from_official_sources",
        "active_for_recommendation": True,
        "source_notes": [
            "Yield sourced from Telangana Atlas 2022 total Blackgram yield for 2020-21.",
            "Input cost derived from official cost of production per quintal published in PIB MSP note for KMS 2021-22.",
            "MSP history sourced from PIB MSP releases; 2024 price range sourced from PJTSAU AMIC Black gram Outlook, April 2024.",
            "District acreage baseline sourced from DES Telangana Nizamabad district profile.",
        ],
        "notes": "Useful as a short-duration pulse only in mandals where the season and soil both fit.",
    },
    "groundnut": {
        "telugu_name": "వేరుశెనగ",
        "season": ["kharif", "rabi"],
        "soil_compatible": ["red_clayey", "mixed"],
        "water_requirement": "low",
        "input_cost_per_acre": 30387,
        "yield_qtl_per_acre": {
            "rainfed": {"min": 8.21, "avg": 8.21, "max": 8.21},
        },
        "price_history_qtl": {
            2020: {"min": 5275, "max": 5275, "avg": 5275},
            2021: {"min": 5550, "max": 5550, "avg": 5550},
            2022: {"min": 5850, "max": 5850, "avg": 5850},
            2023: {"min": 6377, "max": 6377, "avg": 6377},
            2024: {"min": 6783, "max": 6783, "avg": 6783},
            2025: {"min": 5550, "max": 6050, "avg": 5800},
        },
        "district_acreage_legacy_hectares": 625,
        "district_acreage_reference_acres": 1544,
        "district_acreage_reference_year": "2016",
        "grow_duration_days": 110,
        "monitoring_schedule": [
            {"day": 20, "stage": "vegetative", "check": "Leaf miner, early leaf spot"},
            {"day": 40, "stage": "flowering", "check": "Tikka leaf spot, rust"},
            {"day": 70, "stage": "pod_dev", "check": "Stem rot, collar rot"},
        ],
        "common_diseases": {
            "tikka_leaf_spot": {"telugu": "ఆకు మచ్చ", "symptoms": "Dark circular spots on leaves", "treatment": "Protective fungicide schedule during humid weather"},
            "rust": {"telugu": "రస్ట్", "symptoms": "Orange pustules on leaf underside", "treatment": "Timely fungicide spray and residue management"},
        },
        "data_status": "economics_backfilled_from_official_sources",
        "active_for_recommendation": True,
        "source_notes": [
            "Yield derived from PJTSAU cost of cultivation and cost of production tables for Groundnut, 2018-19 to 2020-21.",
            "Input cost derived from official cost of production per quintal published in PIB MSP note for KMS 2021-22.",
            "MSP history sourced from PIB MSP releases; 2025 price range sourced from PJTSAU AMIC Groundnut Outlook, February 2025.",
            "District acreage baseline sourced from DES Telangana Nizamabad district profile.",
        ],
        "notes": "Dryland oilseed option for red and mixed soils once kharif or rabi timing is confirmed.",
    },
    "sesame": {
        "telugu_name": "నువ్వులు",
        "season": ["kharif", "zaid"],
        "soil_compatible": ["red_clayey", "deep_calcareous", "black_cotton"],
        "water_requirement": "low",
        "input_cost_per_acre": 21762,
        "yield_qtl_per_acre": {
            "rainfed": {"min": 3.65, "avg": 3.65, "max": 3.65},
        },
        "price_history_qtl": {
            2020: {"min": 6855, "max": 6855, "avg": 6855},
            2021: {"min": 7307, "max": 7307, "avg": 7307},
            2022: {"min": 7830, "max": 7830, "avg": 7830},
            2023: {"min": 8635, "max": 8635, "avg": 8635},
            2024: {"min": 9267, "max": 9267, "avg": 9267},
        },
        "district_acreage_legacy_irrigated_hectares": 2090,
        "district_acreage_reference_acres": 5164,
        "district_acreage_reference_year": "2015-16",
        "grow_duration_days": 90,
        "monitoring_schedule": [
            {"day": 20, "stage": "vegetative", "check": "Phyllody, leaf spot"},
            {"day": 35, "stage": "flowering", "check": "Alternaria leaf blight"},
            {"day": 55, "stage": "capsule_dev", "check": "Capsule borer, wilt"},
        ],
        "common_diseases": {
            "phyllody": {"telugu": "ఫిలోడీ", "symptoms": "Flower parts become leafy", "treatment": "Remove infected plants and manage vector insects"},
            "leaf_blight": {"telugu": "ఆకు తెగులు", "symptoms": "Necrotic lesions on leaves", "treatment": "Protective fungicide under persistent humidity"},
        },
        "data_status": "economics_backfilled_from_official_sources",
        "active_for_recommendation": True,
        "source_notes": [
            "Yield derived from PJTSAU cost of cultivation and cost of production tables for Sesamum, 2020-21.",
            "Input cost derived from the same PJTSAU cost series for Sesamum.",
            "MSP history sourced from PIB MSP releases for KMS 2020-21 to KMS 2024-25.",
            "District acreage reference uses official irrigated Sesamum area from Telangana Statistical Year Book 2017 as a lower-bound baseline until fresh district crop area is loaded.",
        ],
        "notes": "High-value dryland oilseed; district acreage basis is a lower-bound legacy baseline, so refresh this when newer crop-area data is available.",
    },
    "jowar": {
        "telugu_name": "జొన్న",
        "season": ["kharif", "rabi"],
        "soil_compatible": ["black_cotton", "red_clayey", "mixed"],
        "water_requirement": "low",
        "input_cost_per_acre": 12666,
        "yield_qtl_per_acre": {
            "rainfed": {"min": 6.94, "avg": 6.94, "max": 6.94},
        },
        "price_history_qtl": {
            2020: {"min": 2620, "max": 2620, "avg": 2620},
            2021: {"min": 2738, "max": 2738, "avg": 2738},
            2022: {"min": 2970, "max": 2970, "avg": 2970},
            2023: {"min": 3180, "max": 3180, "avg": 3180},
            2024: {"min": 3371, "max": 3371, "avg": 3371},
        },
        "district_acreage_legacy_hectares": 877,
        "district_acreage_reference_acres": 2167,
        "district_acreage_reference_year": "2016",
        "grow_duration_days": 105,
        "monitoring_schedule": [
            {"day": 18, "stage": "seedling", "check": "Shoot fly, stem borer"},
            {"day": 35, "stage": "vegetative", "check": "Leaf blight, downy mildew"},
            {"day": 60, "stage": "earhead", "check": "Grain mold, midge"},
        ],
        "common_diseases": {
            "downy_mildew": {"telugu": "డౌనీ మిల్డ్యూ", "symptoms": "Chlorotic streaks and malformed growth", "treatment": "Seed treatment and rouging"},
            "grain_mold": {"telugu": "గ్రేన్ మోల్డ్", "symptoms": "Discolored moldy grains at maturity", "treatment": "Timely harvest and weather watch"},
        },
        "data_status": "economics_backfilled_from_official_sources",
        "active_for_recommendation": True,
        "source_notes": [
            "Yield sourced from Telangana Atlas 2022 total Jowar yield for 2020-21.",
            "Input cost derived from official cost of production per quintal published in PIB MSP note for KMS 2021-22.",
            "MSP history sourced from PIB MSP releases for KMS 2020-21 to KMS 2024-25.",
            "District acreage baseline sourced from DES Telangana Nizamabad district profile.",
        ],
        "notes": "Dryland cereal option for black and red soils where farmer wants a lower-risk, lower-cash crop.",
    },
    "castor": {
        "telugu_name": "ఆముదం",
        "season": ["kharif"],
        "soil_compatible": ["red_clayey", "black_cotton"],
        "water_requirement": "low",
        "input_cost_per_acre": None,
        "yield_qtl_per_acre": {
            "rainfed": {"min": 1.47, "avg": 1.47, "max": 1.47},
        },
        "price_history_qtl": {
            2025: {"min": 5300, "max": 5600, "avg": 5450},
        },
        "district_acreage_legacy_irrigated_hectares": 2,
        "district_acreage_reference_acres": 5,
        "district_acreage_reference_year": "2015-16",
        "grow_duration_days": 150,
        "monitoring_schedule": [
            {"day": 25, "stage": "vegetative", "check": "Semilooper, capsule borer"},
            {"day": 50, "stage": "flowering", "check": "Wilt, leafhopper"},
            {"day": 85, "stage": "capsule_dev", "check": "Botrytis, capsule borer"},
        ],
        "common_diseases": {
            "wilt": {"telugu": "విల్ట్", "symptoms": "Sudden drooping and drying", "treatment": "Field sanitation and drainage management"},
            "botrytis": {"telugu": "బోట్రిటిస్", "symptoms": "Blight on spikes/capsules in prolonged humidity", "treatment": "Protective spray in wet spell"},
        },
        "data_status": "supplementary_profile_partially_backfilled_pending_cost",
        "active_for_recommendation": False,
        "source_notes": [
            "Yield sourced from Telangana Atlas 2022 total Castor yield for 2020-21.",
            "2025 price range sourced from PJTSAU AMIC Castor Outlook, February 2025.",
            "District acreage reference uses official irrigated Castor area from Telangana Statistical Year Book 2017 as a minimal baseline.",
        ],
        "notes": "Still inactive until cost-of-cultivation support is backfilled cleanly.",
    },
}

# ── GOVERNMENT SCHEMES ─────────────────────────────────────────────────────────
SCHEMES = {
    "rythu_bandhu": {
        "telugu_name": "రైతు బంధు",
        "amount": "₹5,000 per acre per season (Kharif + Rabi = ₹10,000/acre/year)",
        "who_qualifies": "All farmers with land in Telangana. Must have land in Dharani.",
        "how_to_apply": "Automatic if land registered in Dharani portal. Check with VRO.",
        "payment_months": ["May (Kharif)", "November (Rabi)"],
    },
    "crop_loan_waiver_2024": {
        "telugu_name": "పంట రుణ మాఫీ",
        "amount": "Up to ₹2 lakh waived",
        "who_qualifies": "Crop loans taken Dec 2018 – Dec 2023 from nationalized banks",
        "how_to_apply": "Mandal Agriculture Office. Bring passbook + Aadhaar + land docs.",
        "deadline": "Apply ASAP — scheme window closing",
    },
    "pm_kisan": {
        "telugu_name": "పీఎం కిసాన్",
        "amount": "₹6,000/year in 3 instalments of ₹2,000",
        "who_qualifies": "All small/marginal farmer families",
        "how_to_apply": "pmkisan.gov.in or nearest CSC center with Aadhaar + bank account + land docs",
    },
    "rythu_bima": {
        "telugu_name": "రైతు బీమా",
        "amount": "₹5 lakh to family if farmer dies (any cause)",
        "who_qualifies": "Farmers aged 18-59 with Rythu Bandhu eligibility",
        "how_to_apply": "Automatic enrollment through Rythu Bandhu. Check with agriculture office.",
        "payout_days": 10,
    },
    "kisan_credit_card": {
        "telugu_name": "కిసాన్ క్రెడిట్ కార్డ్",
        "interest_rate": "7% annual (subsidized)",
        "who_qualifies": "Farmers with land documents at nationalized bank",
        "note": "WITHOUT land docs → forced to use private lenders at 24-36% annual. KCC is critical.",
    },
}

# ── WEATHER — NIZAMABAD DISTRICT ───────────────────────────────────────────────
WEATHER_PROFILE = {
    "coords": {"lat": 18.6714, "lon": 78.0942},
    "annual_rainfall_mm": {"min": 867, "max": 1189, "avg": 1028},
    "seasons": {
        "kharif_sowing": {"months": "June–July", "temp_c": "25–35", "rain": "Monsoon onset"},
        "kharif_growing": {"months": "Aug–Sept", "temp_c": "27–33", "rain": "Peak monsoon"},
        "kharif_harvest": {"months": "Oct–Nov", "temp_c": "22–32", "rain": "Retreating monsoon"},
        "rabi_sowing": {"months": "Nov–Dec", "temp_c": "15–28", "rain": "Minimal"},
        "rabi_harvest": {"months": "Feb–Mar", "temp_c": "18–32", "rain": "Minimal"},
        "summer": {"months": "Mar–May", "temp_c": "35–42", "rain": "Very dry, heat stress"},
    },
    "disease_risk_calendar": {
        "june": ["paddy_blast_risk_low", "turmeric_rhizome_rot_if_waterlogged"],
        "july": ["paddy_blast_risk_medium", "maize_fall_army_worm"],
        "august": ["paddy_blast_risk_HIGH", "paddy_blb", "turmeric_leaf_blotch"],
        "september": ["paddy_blast_risk_HIGH", "paddy_sheath_blight", "soybean_pod_borer_CRITICAL"],
        "october": ["paddy_brown_spot", "turmeric_rhizome_rot"],
        "november": ["turmeric_rhizome_rot", "rabi_sowing"],
    },
}

# ── DISTRICT RECOMMENDATION LOG (current season) ──────────────────────────────
# This gets populated dynamically as farmers use the bot.
# At startup: pre-fill with known planted acreage from govt data.

CURRENT_SEASON = "kharif_2025"

DISTRICT_PLANTED_ACRES = {
    # Source: Telangana Dept of Agriculture, as of start of Kharif 2025
    # These are ALREADY planted — before bot makes any recommendations
    # Supplementary dryland crops below use explicit legacy official district
    # baselines currently available in the project:
    # - 2016 "Know Your District - Plan Your District" for Bengal gram,
    #   Black gram, Groundnut, and Jowar
    # - 2015-16 Telangana Statistical Year Book irrigated crop area table for
    #   Sesamum and Castor
    # Refresh these when a newer crop-wise district acreage source is loaded.
    "paddy": 429000,
    "turmeric": 92000,
    "maize": 180000,
    "soybean": 95000,
    "cotton": 18000,
    "red_gram": 45000,
    "sunflower": 5000,
    "green_gram": 12000,
    "sugarcane": 25000,
    "bengal_gram": 6894,
    "black_gram": 2296,
    "groundnut": 1544,
    "sesame": 5164,
    "jowar": 2167,
    "castor": 5,
}

# Bot recommendation log — starts at 0, increments with each recommendation
BOT_RECOMMENDED_ACRES = {crop: 0 for crop in CROPS}
