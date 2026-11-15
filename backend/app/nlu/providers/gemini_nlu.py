"""Gemini structured-output NLU (off-device; opt-in via ALLOW_OFF_DEVICE_PROVIDERS).

Gemini proposes the intent and raw entity strings under a strict JSON schema. Every value
is then re-validated: crops through the catalog, districts through LGD. Language and script
come from the deterministic detector, so the LLM never invents a crop or district.
"""

from __future__ import annotations

import json

from google import genai
from google.genai import types

from app.catalog import get_crop_catalog, get_lgd_directory
from app.nlu.lexicon import get_lexicon
from app.nlu.providers.rule_based import RuleBasedNLUProvider, detect_language
from app.nlu.types import Intent, NLUEntities, NLUResult

_INTENTS = [i.value for i in Intent]
_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "intent": {"type": "STRING", "enum": _INTENTS},
        "secondary_intents": {"type": "ARRAY", "items": {"type": "STRING", "enum": _INTENTS}},
        "confidence": {"type": "NUMBER"},
        "crop_mention": {"type": "STRING", "nullable": True},
        "district_mention": {"type": "STRING", "nullable": True},
        "state_mention": {"type": "STRING", "nullable": True},
    },
    "required": ["intent", "confidence"],
}
_SYSTEM = (
    "You classify farmer questions for an Indian agricultural assistant. Questions may be in "
    "Telugu, Hindi, English, romanised Telugu/Hindi, or a mix. Intents: advisory (how to grow, "
    "fertiliser, sowing, irrigation, spraying), disease (pests, diseases, symptoms), weather, "
    "market (prices, mandi), scheme (government schemes, subsidy, insurance), govt_bulletin "
    "(what an official department/IMD/KVK said or instructed), yield (expected yield or "
    "production; a 'yield forecast' is yield, not weather), officer (officer reports), "
    "smalltalk, out_of_scope. Copy crop and district mentions exactly as written by the user; "
    "never guess one that is not in the text."
)


class GeminiNLUProvider:
    provider_name = "gemini-nlu"

    def __init__(self, api_key: str | None, model_name: str, timeout_seconds: float = 30.0) -> None:
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        self.model_version = model_name
        self._model = model_name
        self._client = genai.Client(
            api_key=api_key, http_options=types.HttpOptions(timeout=int(timeout_seconds * 1000))
        )
        self._rules = RuleBasedNLUProvider()

    async def parse(self, text: str, language_hint: str | None = None) -> NLUResult:
        resp = await self._client.aio.models.generate_content(
            model=self._model,
            contents=text,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM, temperature=0.0,
                response_mime_type="application/json", response_schema=_SCHEMA,
            ),
        )
        data = json.loads(resp.text or "{}")
        intent = Intent(data["intent"])
        secondary = tuple(Intent(i) for i in data.get("secondary_intents") or [] if i in _INTENTS
                          and i != intent.value)
        rules = self._rules.parse_sync(text, language_hint)
        lang, script, switched, romanized = detect_language(text, get_lexicon(), language_hint)

        catalog = get_crop_catalog()
        crop_res = catalog.resolve(data.get("crop_mention") or "") \
            if data.get("crop_mention") else None
        if crop_res is None or crop_res.status.value == "not_found":
            entities_crop = (rules.entities.crop, rules.entities.crop_status,
                             rules.entities.crop_candidates)
        else:
            entities_crop = (crop_res.crop, crop_res.status.value, crop_res.candidates)

        district = None
        if data.get("district_mention"):
            district = get_lgd_directory().resolve_district(
                data["district_mention"], data.get("state_mention"))
        entities = NLUEntities(
            crop=entities_crop[0], crop_status=entities_crop[1],
            crop_candidates=entities_crop[2],
            district_lgd_code=district.lgd_district_code if district
            else rules.entities.district_lgd_code,
            district_name=district.district_name if district else rules.entities.district_name,
            district_candidates=rules.entities.district_candidates,
            season=rules.entities.season, symptoms=rules.entities.symptoms,
            time_expression=rules.entities.time_expression, scheme=rules.entities.scheme,
        )
        return NLUResult(
            intent=intent, confidence=float(data.get("confidence", 0.7)), language=lang,
            is_code_switched=switched, entities=entities, secondary_intents=secondary,
            script=script, romanized=romanized, provider=self.provider_name,
            provider_version=self.model_version, evidence=("gemini-structured-output",),
        )
