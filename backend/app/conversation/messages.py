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
}


def message(key: str, language: str) -> str:
    """Message in ``language``; falls back to English."""
    entry = MESSAGES[key]
    return entry.get(language) or entry["en"]
