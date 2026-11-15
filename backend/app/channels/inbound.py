"""Inbound feature-phone handling (F5): SMS keywords and the IVR menu.

The farmer is identified by phone number. HELP → menu; WEATHER → the latest cross-checked
district forecast; ALERTS → active official warnings; STOP → alerts back to in-app only;
anything else → the conversation bot (answer returned as SMS). hi/te templates are DRAFT.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.messages import MENU, SmsMessage, compose_sms, inbound_menu
from app.models.farmer import Farmer
from app.models.govconnect import GovtBulletin

KEYWORDS = {
    "help": "help",
    "menu": "help",
    "madad": "help",
    "सहायता": "help",
    "సహాయం": "help",
    "weather": "weather",
    "1": "weather",
    "mausam": "weather",
    "मौसम": "weather",
    "వాతావరణం": "weather",
    "alerts": "alerts",
    "alert": "alerts",
    "2": "alerts",
    "चेतावनी": "alerts",
    "హెచ్చరిక": "alerts",
    "stop": "stop",
    "बंद": "stop",
    "ఆపు": "stop",
}
T = {
    "unknown": {
        "en": "This number is not registered with KrishiOS. Ask your extension worker "
        "to register you.",
        "hi": "यह नंबर KrishiOS में पंजीकृत नहीं है। पंजीकरण के लिए अपने विस्तार कार्यकर्ता से संपर्क करें।",
        "te": "ఈ నంబర్ KrishiOS లో నమోదు కాలేదు. నమోదు కోసం మీ విస్తరణ కార్యకర్తను సంప్రదించండి.",
    },
    "no_weather": {
        "en": "No recent forecast for your district yet.",
        "hi": "आपके ज़िले का हाल का पूर्वानुमान अभी उपलब्ध नहीं है।",
        "te": "మీ జిల్లాకు ఇటీవలి వాతావరణ సూచన ఇంకా లేదు.",
    },
    "weather": {
        "en": "{d} today: max {t}°C, rain {r} mm ({p}%). Next 3 days rain {r3} mm. {c}",
        "hi": "{d} आज: अधिकतम {t}°C, बारिश {r} मिमी ({p}%)। अगले 3 दिन बारिश {r3} मिमी। {c}",
        "te": "{d} ఈరోజు: గరిష్ఠ {t}°C, వర్షం {r} మి.మీ ({p}%). రాబోయే 3 రోజుల వర్షం {r3} మి.మీ. {c}",
    },
    "agree": {
        "en": "Checked with a 2nd source.",
        "hi": "दूसरे स्रोत से जाँचा गया।",
        "te": "మరో మూలంతో సరిచూశాం.",
    },
    "disagree": {
        "en": "Sources disagree: use with care.",
        "hi": "स्रोतों में अंतर है: सावधानी रखें।",
        "te": "మూలాల మధ్య తేడా ఉంది: జాగ్రత్తగా ఉపయోగించండి.",
    },
    "unverified": {"en": "Not cross-checked.", "hi": "जाँच नहीं हुई।", "te": "సరిచూడలేదు."},
    "no_alerts": {
        "en": "No active official warnings for your district.",
        "hi": "आपके ज़िले के लिए कोई सक्रिय सरकारी चेतावनी नहीं है।",
        "te": "మీ జిల్లాకు ప్రస్తుతం ప్రభుత్వ హెచ్చరికలు లేవు.",
    },
    "stopped": {
        "en": "Alerts will now come only in the KrishiOS app. Reply HELP for the menu.",
        "hi": "अब अलर्ट केवल KrishiOS ऐप में आएँगे। मेनू के लिए HELP भेजें।",
        "te": "ఇకపై అలర్ట్‌లు KrishiOS యాప్‌లో మాత్రమే వస్తాయి. మెనూ కోసం HELP పంపండి.",
    },
    "no_account": {
        "en": "Questions by SMS need a KrishiOS account. Call 155261 for help.",
        "hi": "SMS से सवाल पूछने के लिए KrishiOS खाता चाहिए। सहायता के लिए 155261 पर कॉल करें।",
        "te": "SMS ద్వారా ప్రశ్నలకు KrishiOS ఖాతా అవసరం. సహాయం కోసం 155261కి కాల్ చేయండి.",
    },
}


def _t(key: str, lang: str, **kw: Any) -> str:
    table = T[key]
    return (table.get(lang) or table["en"]).format(**kw)


def keyword(text: str) -> str | None:
    words = text.strip().lower().split()
    return KEYWORDS.get(words[0]) if len(words) == 1 else None


def normalize_phone(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    return digits[-10:] if len(digits) >= 10 else digits  # noqa: PLR2004 - Indian mobile


async def farmer_by_phone(session: AsyncSession, phone: str) -> Farmer | None:
    return await session.scalar(select(Farmer).where(Farmer.phone.endswith(normalize_phone(phone))))


def farmer_language(f: Farmer | None) -> str:
    from app.govconnect.targeting import norm_language  # noqa: PLC0415

    return (norm_language(f.preferred_language) if f else None) or "en"


async def weather_text(session: AsyncSession, farmer: Farmer, lang: str) -> str:
    from app.govconnect.api import _farmer_district_codes  # noqa: PLC0415
    from app.govconnect.weather_feed import latest_snapshot  # noqa: PLC0415

    codes = await _farmer_district_codes(session, farmer.id)
    snap = await latest_snapshot(session, codes[0]) if codes else None
    if snap is None or not snap.forecast:
        return _t("no_weather", lang)
    from app.catalog.lgd import get_lgd_directory  # noqa: PLC0415

    d = get_lgd_directory().district(snap.lgd_district_code)
    today = date.today().isoformat()
    days = [f for f in snap.forecast if f["date"] >= today][:3] or snap.forecast[:3]
    first = days[0]
    check = (snap.crosscheck or {}).get("status", "unverified")
    return _t(
        "weather",
        lang,
        d=d.district_name if d else "",
        t=round(first["temperature_max_celsius"]),
        r=round(first["precipitation_sum_mm"]),
        p=round(first["precipitation_probability_percent"]),
        r3=round(sum(f["precipitation_sum_mm"] for f in days)),
        c=_t(check, lang),
    )


async def alerts_text(session: AsyncSession, farmer: Farmer, lang: str) -> str:
    from app.govconnect.api import _farmer_district_codes  # noqa: PLC0415

    codes = set(await _farmer_district_codes(session, farmer.id))
    now = datetime.now(UTC)
    active = [
        b
        for b in (
            await session.scalars(
                select(GovtBulletin).where(
                    GovtBulletin.status == "published", GovtBulletin.valid_to > now
                )
            )
        ).all()
        if codes & set(b.district_codes or [])
    ]
    if not active:
        return _t("no_alerts", lang)
    return "\n".join(f"{b.authority}: {b.title}" for b in active[:3])


async def stop_alerts(session: AsyncSession, farmer: Farmer) -> None:
    from app.models.proactive import NotificationChannel  # noqa: PLC0415
    from app.notifications.service import NotificationService  # noqa: PLC0415

    pref = await NotificationService()._get_or_create_preferences(session, farmer.id)
    pref.preferred_channel = NotificationChannel.IN_APP


async def handle_sms(
    session: AsyncSession, phone: str, text: str, ask: Any = None
) -> tuple[SmsMessage, str]:
    """Return (reply, action). ``ask(farmer, text, lang)`` answers free-text questions."""
    farmer = await farmer_by_phone(session, phone)
    lang = farmer_language(farmer)
    if farmer is None:
        return compose_sms(_t("unknown", "en"), "en", footer=False), "unknown_number"
    action = keyword(text) or "question"
    if action == "help":
        body = MENU.get(lang, MENU["en"])
        return compose_sms(body, lang, footer=False), action
    if action == "weather":
        body = await weather_text(session, farmer, lang)
    elif action == "alerts":
        body = await alerts_text(session, farmer, lang)
    elif action == "stop":
        await stop_alerts(session, farmer)
        return compose_sms(_t("stopped", lang), lang, footer=False), action
    else:
        body = await ask(farmer, text, lang) if ask else None
        body = body or _t("no_account", lang)
    return compose_sms(body, lang), action


async def handle_ivr(session: AsyncSession, phone: str, digits: str | None) -> dict[str, Any]:
    farmer = await farmer_by_phone(session, phone)
    lang = farmer_language(farmer)
    if farmer is None:
        return {
            "language": "en",
            "steps": [{"say": _t("unknown", "en"), "language": "en"}],
            "action": "unknown_number",
        }
    if not digits:
        return {**inbound_menu(lang).to_dict(), "action": "menu"}
    if digits == "1":
        return {
            "language": lang,
            "steps": [{"say": await weather_text(session, farmer, lang), "language": lang}],
            "action": "weather",
        }
    if digits == "2":
        return {
            "language": lang,
            "steps": [{"say": await alerts_text(session, farmer, lang), "language": lang}],
            "action": "alerts",
        }
    if digits == "3":
        return {
            "language": lang,
            "steps": [{"record": {"max_seconds": 60, "then": "/conversation/voice-turns"}}],
            "action": "record_question",
        }
    return {**inbound_menu(lang).to_dict(), "action": "menu"}
