"""Domain dictionaries for entity normalization in the KrishiOS agricultural ontology.

Purpose:
  These dictionaries map raw text mentions to canonical entity names.
  They are the first line of defense against entity fragmentation.

  Example: "rice", "Rice crop", "paddy crop", "Oryza sativa" all map
           to canonical_name = "Paddy".

Structure:
  {canonical_name: [alias1, alias2, ...]}
  The canonical_name itself is always matched as well.

MVP coverage:
  - Crops: Paddy, Cotton, Tomato, Wheat (enough for evaluation scenarios)
  - Diseases: key diseases for the above crops
  - Pests: key pests for the above crops
  - Symptoms: common observable conditions
  - Nutrients: macronutrients and important micronutrients
  - Soil types: major Indian soil classifications
  - Seasons: as used in KrishiOS (matches existing season field)
  - Authorities: common Indian agricultural institutions

Extensibility:
  Add entries here. The DictionaryEntityExtractor loads these at startup.
  Future sprints can load these from a database table or an LLM-populated
  knowledge base instead.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Crops
# ---------------------------------------------------------------------------

CROP_DICTIONARY: dict[str, list[str]] = {
    "Paddy": [
        "rice", "rice crop", "paddy crop", "oryza sativa", "dhaan", "chawal",
        "dhan", "rice plant", "paddy plant", "wet rice", "upland rice",
        "వరి", "వరి పైరు", "వరి పంట",
    ],
    "Cotton": [
        "gossypium", "kapas", "kappas", "cotton plant", "bt cotton",
        "american cotton", "desi cotton", "white gold", "ప్రత్తి", "కపాస్",
    ],
    "Tomato": [
        "lycopersicon esculentum", "solanum lycopersicum", "tamatar",
        "tomato plant", "tomato crop", "టమాట", "టమోటా",
    ],
    "Wheat": [
        "triticum aestivum", "gehun", "gahu", "wheat crop", "wheat plant",
        "rabi wheat", "గోధుమ",
    ],
    "Maize": [
        "corn", "zea mays", "makka", "maize crop", "sweet corn", "మొక్కజొన్న",
    ],
    "Groundnut": [
        "peanut", "arachis hypogaea", "moongphali", "groundnut crop", "వేరుశనగ",
    ],
    "Soybean": [
        "glycine max", "soya bean", "soya", "soyabean",
    ],
    "Sugarcane": [
        "saccharum officinarum", "ganna", "ikshu", "sugarcane crop", "చెరకు",
    ],
}

# ---------------------------------------------------------------------------
# Diseases (keyed to crops where specific, otherwise generic)
# ---------------------------------------------------------------------------

DISEASE_DICTIONARY: dict[str, list[str]] = {
    # Paddy diseases
    "Blast": [
        "rice blast", "paddy blast", "leaf blast", "neck blast",
        "magnaporthe oryzae", "pyricularia oryzae", "pyricularia blast",
        "collar blast", "panicle blast", "అగ్గి తెగులు", "ब्लास्ट रोग",
    ],
    "Brown Spot": [
        "paddy brown spot", "rice brown spot", "helminthosporium oryzae",
        "cochliobolus miyabeanus", "brown leaf spot", "భూరా మచ్చ", "भूरा धब्बा",
    ],
    "Sheath Blight": [
        "paddy sheath blight", "rhizoctonia solani", "sheath rot blight",
    ],
    "Bacterial Leaf Blight": [
        "blb", "kresek", "xanthomonas oryzae", "bacterial blight",
        "rice bacterial blight",
    ],
    # Cotton diseases
    "Bacterial Blight of Cotton": [
        "cotton blight", "xanthomonas axonopodis", "angular leaf spot cotton",
        "black arm cotton",
    ],
    "Fusarium Wilt": [
        "fusarium oxysporum", "cotton wilt", "wilt disease",
    ],
    # Tomato diseases
    "Early Blight": [
        "alternaria solani", "tomato early blight", "target spot tomato",
    ],
    "Late Blight": [
        "phytophthora infestans", "tomato late blight", "downy mildew tomato",
    ],
    "Tomato Leaf Curl": [
        "tomato yellow leaf curl", "tylcv", "tomato leaf curl virus",
    ],
    # Generic / cross-crop
    "Powdery Mildew": [
        "white powder disease", "erysiphe", "powdery mildew disease",
    ],
    "Root Rot": [
        "root rot disease", "phytophthora root rot", "pythium root rot",
    ],
    "Iron Deficiency Chlorosis": [
        "iron deficiency", "fe deficiency", "iron chlorosis", "yellow leaf iron",
        "interveinal chlorosis",
    ],
    "Zinc Deficiency": [
        "zn deficiency", "zinc deficiency disease", "khaira disease",
        "zinc deficiency paddy",
    ],
    "Nitrogen Deficiency": [
        "n deficiency", "nitrogen starvation", "nitrogen deficiency disease",
    ],
}

# ---------------------------------------------------------------------------
# Pests
# ---------------------------------------------------------------------------

PEST_DICTIONARY: dict[str, list[str]] = {
    "Brown Planthopper": [
        "bph", "nilaparvata lugens", "hopper", "paddy hopper",
        "brown hopper",
    ],
    "Stem Borer": [
        "yellow stem borer", "scirpophaga incertulas", "paddy stem borer",
        "chilo suppressalis", "white stem borer",
    ],
    "Leafhopper": [
        "green leafhopper", "nephotettix virescens", "rice leafhopper",
        "paddy leafhopper",
    ],
    "Whitefly": [
        "bemisia tabaci", "cotton whitefly", "tobacco whitefly",
        "sweet potato whitefly",
    ],
    "Bollworm": [
        "helicoverpa armigera", "american bollworm", "cotton bollworm",
        "fruit borer cotton",
    ],
    "Aphid": [
        "aphis gossypii", "cotton aphid", "melon aphid", "plant lice",
    ],
    "Thrips": [
        "thrips tabaci", "onion thrips", "cotton thrips", "chilli thrips",
    ],
    "Fruit Borer": [
        "helicoverpa armigera tomato", "tomato fruit borer", "tomato worm",
    ],
}

# ---------------------------------------------------------------------------
# Symptoms
# ---------------------------------------------------------------------------

SYMPTOM_DICTIONARY: dict[str, list[str]] = {
    "Yellow Leaves": [
        "yellowing of leaves", "leaf yellowing", "yellow foliage",
        "yellow leaf", "yellow discoloration", "chlorotic leaves",
        "chlorosis", "yellowing", "pale yellow leaves",
    ],
    "Brown Spots": [
        "brown spot on leaves", "leaf brown spots", "brown lesions",
        "brown patches", "necrotic spots brown",
    ],
    "White Powdery Growth": [
        "white powder on leaves", "powdery coating", "white mycelium",
        "white fluffy growth",
    ],
    "Leaf Lesions": [
        "lesions on leaf", "leaf blight lesion", "diamond shaped lesion",
        "spindle lesion", "blast lesion",
    ],
    "Wilting": [
        "plant wilting", "drooping leaves", "wilted plant", "wilt symptom",
        "sudden wilting",
    ],
    "Stunted Growth": [
        "stunting", "poor growth", "reduced height", "dwarfing",
        "growth retardation",
    ],
    "Leaf Curl": [
        "curling of leaves", "rolled leaves", "leaf rolling", "upward curl",
        "leaf curling",
    ],
    "Root Decay": [
        "root rot symptom", "decaying roots", "black roots", "rotting roots",
    ],
    "Interveinal Chlorosis": [
        "yellowing between veins", "green veins yellow leaf",
        "interveinal yellowing", "iron deficiency symptoms",
    ],
    "Dead Heart": [
        "central shoot dead", "dead central tiller", "deadheart", "stem borer damage",
    ],
    "White Ear": [
        "white panicle", "unfilled grain", "empty panicle", "white ear symptom",
    ],
}

# ---------------------------------------------------------------------------
# Nutrients
# ---------------------------------------------------------------------------

NUTRIENT_DICTIONARY: dict[str, list[str]] = {
    "Nitrogen": ["N", "urea nitrogen", "nitrate nitrogen", "ammonia nitrogen"],
    "Phosphorus": ["P", "phosphate", "phosphorous"],
    "Potassium": ["K", "potash", "potassium chloride"],
    "Iron": ["Fe", "ferrous", "ferric iron"],
    "Zinc": ["Zn", "zinc sulphate"],
    "Manganese": ["Mn", "manganese sulphate"],
    "Boron": ["B", "borax"],
    "Sulfur": ["S", "sulphur", "sulfate sulfur"],
    "Magnesium": ["Mg", "magnesium sulphate"],
}

# ---------------------------------------------------------------------------
# Soil types (major Indian classifications)
# ---------------------------------------------------------------------------

SOIL_TYPE_DICTIONARY: dict[str, list[str]] = {
    "Alluvial Soil": ["alluvium", "river soil", "plains soil"],
    "Black Cotton Soil": ["regur soil", "vertisol", "cotton soil", "black soil"],
    "Red Soil": ["red laterite", "red loam"],
    "Laterite Soil": ["lateritic soil", "laterite"],
    "Sandy Soil": ["sandy loam", "light soil", "coarse soil"],
    "Clay Soil": ["clayey soil", "heavy soil", "clay loam"],
    "Loam Soil": ["loamy soil", "medium soil"],
}

# ---------------------------------------------------------------------------
# Seasons (matches existing KrishiOS season field values)
# ---------------------------------------------------------------------------

SEASON_DICTIONARY: dict[str, list[str]] = {
    "kharif": ["kharif season", "monsoon season", "summer crop"],
    "rabi": ["rabi season", "winter season", "winter crop"],
    "zaid": ["zaid season", "summer season", "summer kharif"],
    "perennial": ["year round", "throughout the year", "evergreen"],
}

# ---------------------------------------------------------------------------
# Authorities (Indian agricultural institutions)
# ---------------------------------------------------------------------------

AUTHORITY_DICTIONARY: dict[str, list[str]] = {
    "ICAR": [
        "indian council of agricultural research", "icar india",
    ],
    "NABARD": [
        "national bank for agriculture and rural development",
    ],
    "Ministry of Agriculture": [
        "ministry of agriculture and farmers welfare", "agriculture ministry india",
        "union agriculture ministry", "moafw",
    ],
    "APEDA": [
        "agricultural and processed food products export development authority",
    ],
    "State Agriculture Department": [
        "state agri dept", "department of agriculture", "agriculture department",
        "state department of agriculture",
    ],
}

# ---------------------------------------------------------------------------
# Master registry — maps entity_type → dictionary for the extractor
# ---------------------------------------------------------------------------

ALL_DICTIONARIES: dict[str, dict[str, list[str]]] = {
    "Crop": CROP_DICTIONARY,
    "Disease": DISEASE_DICTIONARY,
    "Pest": PEST_DICTIONARY,
    "Symptom": SYMPTOM_DICTIONARY,
    "Nutrient": NUTRIENT_DICTIONARY,
    "SoilType": SOIL_TYPE_DICTIONARY,
    "Season": SEASON_DICTIONARY,
    "Authority": AUTHORITY_DICTIONARY,
}


def build_reverse_lookup(entity_type: str) -> dict[str, str]:
    """Build alias → canonical_name lookup for one entity type.

    Used by the entity resolver.

    Returns:
        {alias_lowercase: canonical_name}
    """
    dictionary = ALL_DICTIONARIES.get(entity_type, {})
    lookup: dict[str, str] = {}
    for canonical, aliases in dictionary.items():
        lookup[canonical.lower()] = canonical
        for alias in aliases:
            lookup[alias.lower()] = canonical
    return lookup
