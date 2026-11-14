"""Feature-phone message composition (F5): SMS segmenting and IVR call scripts.

SMS: GSM-7 text fits 160 characters (153 per part when concatenated); anything else (Telugu,
Hindi) is UCS-2 at 70 (67 per part). Messages are trimmed to ``MAX_SEGMENTS`` parts with an
ellipsis and always end with the localized reply-keyword footer. hi/te strings are DRAFT.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

MAX_SEGMENTS = 3
_GSM7 = set(
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
)
FOOTER = {"en": "Reply HELP for menu", "hi": "मेनू के लिए HELP भेजें", "te": "మెనూ కోసం HELP పంపండి"}
HELPLINE = "155261"  # Bharat-VISTAAR farmer helpline (orientation report, PIB source)
MENU = {
    "en": "KrishiOS: reply WEATHER for forecast, ALERTS for official warnings, or type your "
    f"question. STOP to stop alerts. Helpline {HELPLINE}",
    "hi": "KrishiOS: मौसम के लिए WEATHER, सरकारी चेतावनी के लिए ALERTS भेजें, या अपना सवाल लिखें। "
    f"अलर्ट बंद करने के लिए STOP। हेल्पलाइन {HELPLINE}",
    "te": "KrishiOS: వాతావరణం కోసం WEATHER, ప్రభుత్వ హెచ్చరికల కోసం ALERTS పంపండి, లేదా మీ ప్రశ్న "
    f"రాయండి. అలర్ట్‌లు ఆపడానికి STOP. హెల్ప్‌లైన్ {HELPLINE}",
}


def is_gsm7(text: str) -> bool:
    return all(ch in _GSM7 for ch in text)


@dataclass(frozen=True, slots=True)
class SmsMessage:
    text: str
    encoding: str  # gsm7 | ucs2
    segments: int
    truncated: bool


def compose_sms(
    body: str, language: str = "en", *, footer: bool = True, max_segments: int = MAX_SEGMENTS
) -> SmsMessage:
    tail = f"\n{FOOTER.get(language, FOOTER['en'])}" if footer else ""
    gsm = is_gsm7(body + tail)
    single, part = (160, 153) if gsm else (70, 67)
    budget = single if max_segments == 1 else part * max_segments
    text, truncated = body.strip() + tail, False
    if len(text) > budget:
        keep = budget - len(tail) - 1
        text, truncated = body.strip()[:keep].rstrip() + "…" + tail, True
        if gsm and not is_gsm7(text):  # "…" is not GSM-7; use three dots instead
            text = body.strip()[: keep - 2].rstrip() + "..." + tail
    segments = 1 if len(text) <= single else -(-len(text) // part)
    return SmsMessage(text, "gsm7" if is_gsm7(text) else "ucs2", segments, truncated)


@dataclass(slots=True)
class CallScript:
    """Provider-neutral IVR script: an ordered list of say / gather / record / play steps."""

    language: str
    steps: list[dict[str, Any]] = field(default_factory=list)

    def say(self, text: str) -> CallScript:
        self.steps.append({"say": text, "language": self.language})
        return self

    def gather(self, prompt: str, options: dict[str, str]) -> CallScript:
        self.steps.append(
            {"gather": {"prompt": prompt, "options": options, "language": self.language}}
        )
        return self

    def to_dict(self) -> dict[str, Any]:
        return {"language": self.language, "steps": self.steps}


IVR_TEXT = {
    "en": {
        "welcome": "Welcome to KrishiOS.",
        "menu": "Press 1 for weather, 2 for official warnings, 3 to record your question.",
        "repeat": "Press 9 to hear this again.",
    },
    "hi": {
        "welcome": "KrishiOS में आपका स्वागत है।",
        "menu": "मौसम के लिए 1, सरकारी चेतावनी के लिए 2, अपना सवाल रिकॉर्ड करने के लिए 3 दबाएँ।",
        "repeat": "दोबारा सुनने के लिए 9 दबाएँ।",
    },
    "te": {
        "welcome": "KrishiOS కి స్వాగతం.",
        "menu": "వాతావరణం కోసం 1, ప్రభుత్వ హెచ్చరికల కోసం 2, మీ ప్రశ్న రికార్డ్ చేయడానికి 3 నొక్కండి.",
        "repeat": "మళ్ళీ వినడానికి 9 నొక్కండి.",
    },
}


def alert_call(title: str, body: str, authority: str, language: str) -> CallScript:
    """Outbound voice alert: who issued it, then the message, then a repeat option."""
    t = IVR_TEXT.get(language, IVR_TEXT["en"])
    return (
        CallScript(language)
        .say(t["welcome"])
        .say(f"{authority}. {title}.")
        .say(body)
        .gather(t["repeat"], {"9": "repeat"})
    )


def inbound_menu(language: str) -> CallScript:
    t = IVR_TEXT.get(language, IVR_TEXT["en"])
    return (
        CallScript(language)
        .say(t["welcome"])
        .gather(t["menu"], {"1": "weather", "2": "alerts", "3": "record_question"})
    )
