"""Localized system messages for the conversation manager (en / hi / te).

Status: DRAFT, pending native-speaker review (te, hi). These are fixed UI-style messages
(clarification questions, refusals, notices), not advisory content; advisory answers are
produced by the agent runtime and translated by the translation service with safety checks.
"""

from __future__ import annotations

MESSAGES: dict[str, dict[str, str]] = {
    "ask_crop": {
        "en": "Which crop is this about?",
        "hi": "यह किस फसल के बारे में है?",
        "te": "ఇది ఏ పంట గురించి?",
    },
    "pick_crop": {
        "en": "Did you mean one of these crops?",
        "hi": "क्या आपका मतलब इनमें से किसी फसल से है?",
        "te": "మీరు ఈ పంటలలో ఏదైనా అనుకుంటున్నారా?",
    },
    "ask_district": {
        "en": "Which district is your field in?",
        "hi": "आपका खेत किस जिले में है?",
        "te": "మీ పొలం ఏ జిల్లాలో ఉంది?",
    },
    "pick_district": {
        "en": "There are several districts with this name. Which one?",
        "hi": "इस नाम के कई जिले हैं। कौन सा?",
        "te": "ఈ పేరుతో చాలా జిల్లాలు ఉన్నాయి. ఏది?",
    },
    "greeting": {
        "en": "Namaste! Ask me about your crop, weather, market prices or government schemes.",
        "hi": "नमस्ते! अपनी फसल, मौसम, मंडी भाव या सरकारी योजनाओं के बारे में पूछिए।",
        "te": "నమస్కారం! మీ పంట, వాతావరణం, మార్కెట్ ధరలు లేదా ప్రభుత్వ పథకాల గురించి అడగండి.",
    },
    "out_of_scope": {
        "en": "I can only help with farming questions: crops, pests, weather, prices and schemes.",
        "hi": "मैं केवल खेती से जुड़े सवालों में मदद कर सकता हूँ: फसल, कीट, मौसम, भाव और योजनाएँ।",
        "te": "నేను వ్యవసాయ ప్రశ్నలకు మాత్రమే సహాయం చేయగలను: పంటలు, పురుగులు, వాతావరణం, ధరలు, పథకాలు.",
    },
    "translation_unverified": {
        "en": "",
        "hi": "इस उत्तर का सत्यापित अनुवाद उपलब्ध नहीं है, इसलिए अंग्रेज़ी में दिखाया जा रहा है। "
              "एक अधिकारी को सूचित किया गया है।",
        "te": "ఈ సమాధానానికి ధృవీకరించిన అనువాదం అందుబాటులో లేదు, అందుకే ఆంగ్లంలో చూపిస్తున్నాం. "
              "అధికారికి తెలియజేశాం.",
    },
    "no_grounded_answer": {
        "en": "I could not find verified information for this question. "
              "It has been sent to an agricultural officer.",
        "hi": "इस सवाल के लिए सत्यापित जानकारी नहीं मिली। इसे कृषि अधिकारी को भेज दिया गया है।",
        "te": "ఈ ప్రశ్నకు ధృవీకరించిన సమాచారం దొరకలేదు. దీనిని వ్యవసాయ అధికారికి పంపించాం.",
    },
    # Yield outlook (Phase 8). Numbers are filled in by code, never translated.
    "yield_forecast": {
        "en": "Model estimate for {crop} in {district} ({season} {year}): about {value} {unit} "
              "(likely range {low}-{high}); the normal is {normal} {unit}, so this is {change}.",
        "hi": "{district} में {crop} ({season} {year}) का मॉडल अनुमान: लगभग {value} {unit} "
              "(संभावित सीमा {low}-{high}); सामान्य {normal} {unit} है, यानी {change}।",
        "te": "{district}లో {crop} ({season} {year}) మోడల్ అంచనా: సుమారు {value} {unit} "
              "(సంభావ్య పరిధి {low}-{high}); సాధారణం {normal} {unit}, అంటే {change}.",
    },
    "yield_change_below": {"en": "{pct}% below normal", "hi": "सामान्य से {pct}% कम",
                           "te": "సాధారణం కంటే {pct}% తక్కువ"},
    "yield_change_above": {"en": "{pct}% above normal", "hi": "सामान्य से {pct}% अधिक",
                           "te": "సాధారణం కంటే {pct}% ఎక్కువ"},
    "yield_change_near": {"en": "close to normal", "hi": "सामान्य के आसपास",
                          "te": "సాధారణానికి దగ్గరగా"},
    "yield_disclaimer": {
        "en": "This is a model estimate, not an official crop-cutting, YES-TECH or insurance "
              "figure.",
        "hi": "यह एक मॉडल अनुमान है, आधिकारिक फसल कटाई, YES-TECH या बीमा आंकड़ा नहीं।",
        "te": "ఇది మోడల్ అంచనా మాత్రమే; అధికారిక పంట కోత, YES-TECH లేదా బీమా అంకె కాదు.",
    },
    "yield_review": {
        "en": "The uncertainty is high for this crop, so an officer will review it.",
        "hi": "इस फसल के लिए अनिश्चितता अधिक है, इसलिए एक अधिकारी इसकी समीक्षा करेगा।",
        "te": "ఈ పంటకు అనిశ్చితి ఎక్కువ, కాబట్టి అధికారి దీనిని పరిశీలిస్తారు.",
    },
    "yield_abstain": {
        "en": "There is not enough data to forecast {crop} yield in {district} reliably, so no "
              "number is given.",
        "hi": "{district} में {crop} की उपज का भरोसेमंद अनुमान लगाने के लिए पर्याप्त डेटा नहीं है, "
              "इसलिए कोई संख्या नहीं दी जा रही।",
        "te": "{district}లో {crop} దిగుబడిని నమ్మకంగా అంచనా వేయడానికి తగినంత సమాచారం లేదు, "
              "అందుకే సంఖ్య ఇవ్వడం లేదు.",
    },
    "yield_none": {
        "en": "There is no yield forecast for {crop} in {district} yet.",
        "hi": "{district} में {crop} के लिए अभी कोई उपज अनुमान नहीं है।",
        "te": "{district}లో {crop}కు ఇంకా దిగుబడి అంచనా లేదు.",
    },
}


def message(key: str, language: str) -> str:
    """Message in ``language``; falls back to English."""
    entry = MESSAGES[key]
    return entry.get(language) or entry["en"]
