"""F5 channels: SMS composition, keywords, sandbox adapters (no network, no database)."""

from app.channels.inbound import keyword, normalize_phone
from app.channels.messages import alert_call, compose_sms, inbound_menu, is_gsm7
from app.channels.providers import SandboxChannelProvider, channel_providers, mask
from app.dpi.providers import SandboxFarmerRegistry
from app.models.proactive import NotificationChannel
from app.notifications.contracts import NotificationPayload
from app.notifications.webpush import WebPushProvider, push_payload
from app.providers.status import active_providers


def test_sms_encoding_and_segments() -> None:
    en = compose_sms("Heavy rain likely in Khammam tomorrow.", "en")
    assert en.encoding == "gsm7" and en.segments == 1
    assert en.text.endswith("Reply HELP for menu")
    te = compose_sms("ఖమ్మం జిల్లాలో రేపు భారీ వర్షం.", "te")
    assert te.encoding == "ucs2" and te.text.endswith("మెనూ కోసం HELP పంపండి")
    long_te = compose_sms("వర్షం " * 200, "te")
    assert long_te.truncated and long_te.segments <= 3 and len(long_te.text) <= 67 * 3
    long_en = compose_sms("rain " * 200, "en")
    assert long_en.truncated and is_gsm7(long_en.text) and long_en.segments <= 3


def test_keywords_and_phone_normalisation() -> None:
    assert keyword("HELP") == "help" and keyword(" weather ") == "weather"
    assert keyword("మౌసమ్ ఎలా ఉంది") is None  # sentences are questions, not keywords
    assert keyword("వాతావరణం") == "weather" and keyword("2") == "alerts"
    assert normalize_phone("+91 98765-43210") == "9876543210"


def test_ivr_scripts() -> None:
    call = alert_call("Heavy rain warning", "Postpone spraying.", "IMD Hyderabad", "en")
    steps = call.to_dict()["steps"]
    assert steps[1]["say"].startswith("IMD Hyderabad") and steps[-1]["gather"]["options"]
    menu = inbound_menu("hi").to_dict()
    assert set(menu["steps"][1]["gather"]["options"]) == {"1", "2", "3"}


async def test_sandbox_providers_compose_and_never_store_phone_numbers() -> None:
    sms = SandboxChannelProvider(NotificationChannel.SMS)
    payload = NotificationPayload(farmer_id=42, title="IMD: Heavy rain", message="Drain fields.",
                                  channel=NotificationChannel.SMS, language="te")
    result = await sms.send(payload)
    assert result.success and result.message_id.startswith("sandbox-sms-")
    item = sms.outbox[-1]
    assert item["to"] == mask(42) != "42"
    assert item["encoding"] == "ucs2"  # Telugu footer needs Unicode SMS
    voice = SandboxChannelProvider(NotificationChannel.VOICE)
    await voice.send(NotificationPayload(farmer_id=1, title="IMD: Heavy rain",
                                         message="Drain fields.",
                                         channel=NotificationChannel.VOICE, language="en"))
    assert voice.outbox[-1]["call_script"]["steps"][1]["say"].startswith("IMD")
    providers = channel_providers()
    assert set(providers) == {NotificationChannel.SMS, NotificationChannel.VOICE,
                              NotificationChannel.WHATSAPP}


async def test_push_sandbox_and_dpi_sandboxes_return_no_data() -> None:
    push = WebPushProvider()
    res = await push.send(NotificationPayload(farmer_id=1, title="t", message="m" * 400,
                                              channel=NotificationChannel.PUSH))
    assert res.success and res.message_id.startswith("sandbox-push-")  # no VAPID keys in tests
    assert len(push_payload(NotificationPayload(farmer_id=1, title="t", message="m" * 400))
               ["body"]) == 300
    registry = SandboxFarmerRegistry()
    assert (await registry.lookup(farmer_id=1, consent_token=None)).reason == "consent_required"
    granted = await registry.lookup(farmer_id=1, consent_token="token")  # noqa: S106
    assert not granted.available and granted.reason == "agristack_access_not_granted"
    kinds = {p.capability: p.info.kind.value for p in active_providers() if p.info}
    for cap in ("sms", "voice", "whatsapp", "dpi_farmer_registry", "dpi_language"):
        assert kinds[cap] == "sandbox"
