"""Multi-turn, multilingual conversation manager.

One turn:

1. Load the dialogue state. If a clarification is pending and this turn answers it (chip
   choice, or text that resolves the slot), fill the slot and resume the original question.
2. Parse with NLU (intent, language, crop/district via catalog/LGD).
3. Merge entities into the state. An ambiguous crop or district becomes a clarification with
   choices: never a guess.
4. Smalltalk and out-of-scope get fixed localized replies.
5. Fill required slots for the intent from the state or the farmer profile; ask for missing ones.
6. Translate the question to English (the knowledge base is English), run the agent runtime,
   translate the answer back with the translation safety checks. If the translation is
   blocked, show the English answer with a notice and flag the turn for officer review.
7. Optional TTS of the reply. Persist the turn (audit, feedback).

Yield questions (Phase 8) skip the agent runtime: the answer is the imported forecast from the
yield provider, rendered from fixed localized templates (numbers filled in by code) with a
"model estimate, not official" notice and a structured ``yield_forecast`` card. Tier C and
missing forecasts are said plainly, with no number.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass, field
from typing import Any

from loguru import logger

from app.catalog import get_crop_catalog, get_lgd_directory
from app.conversation.answer import AnswerContext, AnswerRunner, RuntimeAnswerRunner
from app.conversation.messages import message
from app.conversation.state import DialogueState, InMemoryStateStore, Pending, StateStore
from app.nlu import service as nlu_service
from app.nlu.types import Intent, NLUResult
from app.translation.service import TranslationService, TranslationStatus, get_translation_service

REQUIRED_SLOTS: dict[Intent, tuple[str, ...]] = {
    Intent.DISEASE: ("crop",),
    Intent.ADVISORY: ("crop",),
    Intent.MARKET: ("crop",),
    Intent.YIELD: ("crop", "district"),
    Intent.WEATHER: ("district",),
}
DELIVERABLE = {TranslationStatus.PASSTHROUGH, TranslationStatus.AUTO_APPROVED}
REFUSED = {Intent.OUT_OF_SCOPE, Intent.OFFICER}
# Replies that cannot be a new farming question (used to re-ask a pending clarification).
_NOT_A_QUESTION = {Intent.OUT_OF_SCOPE, Intent.SMALLTALK}


@dataclass(slots=True)
class FarmerProfile:
    """Defaults the bot may use without asking (from the farmer's registered profile)."""

    district_lgd_code: int | None = None
    crops: list[str] = field(default_factory=list)  # catalog keys


@dataclass(slots=True)
class TurnInput:
    user_uuid: str
    text: str
    language: str  # reply language chosen in the UI (en | hi | te)
    conversation_id: str | None = None
    choice: dict[str, Any] | None = None  # {"slot": "crop", "value": "cabbage"}
    speak: bool = False
    profile: FarmerProfile | None = None
    acting_for_farmer_id: int | None = None
    auth: Any = None
    # "Ask about this" on a Govt Connect bulletin: the official text (English) is given to
    # the agent runtime as context, and the turn is linked to the bulletin for analytics.
    context_en: str | None = None
    bulletin_uuid: str | None = None


@dataclass(slots=True)
class TurnResult:
    conversation_id: str
    turn_id: str
    status: str  # answered | clarification | smalltalk | refused
    language: str
    reply_text: str
    reply_text_en: str | None = None
    intent: str | None = None
    detected_language: str | None = None
    clarification: dict[str, Any] | None = None
    citations: list[dict[str, Any]] = field(default_factory=list)
    slots: dict[str, Any] = field(default_factory=dict)
    translation_status: str | None = None
    requires_review: bool = False
    review_reason: str | None = None
    providers: dict[str, Any] = field(default_factory=dict)
    weather: dict[str, Any] | None = None
    audio_uuid: str | None = None
    resumed_question: str | None = None
    symptoms: list[str] = field(default_factory=list)
    media: list[dict[str, Any]] = field(default_factory=list)
    yield_forecast: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class _Question:
    """The question being answered this turn (possibly resumed after a clarification)."""

    text: str
    language: str
    intent: Intent
    answered_slot: str | None = None
    resumed: bool = False


TurnSink = Callable[[DialogueState, TurnInput, TurnResult], Awaitable[None]]
YieldLookup = Callable[[int, str, str | None], Awaitable[dict[str, Any] | None]]
UNIT_LABEL = {"Tonnes/Hectare": "t/ha", "bales_170kg/ha": "bales/ha",
              "bales_180kg/ha": "bales/ha", "nuts/ha": "nuts/ha"}
NEAR_NORMAL = 0.05


async def default_yield_lookup(lgd: int, crop: str, season: str | None) -> dict[str, Any] | None:
    from app.database.session import async_session_factory  # noqa: PLC0415
    from app.forecasting.selection import get_yield_provider  # noqa: PLC0415

    async with async_session_factory() as session:
        f = await get_yield_provider().forecast(session, lgd, crop, season)
    return f.to_dict() if f else None


class ConversationManager:
    def __init__(  # noqa: PLR0913, PLR0917 - injectable collaborators (tests)
        self, store: StateStore | None = None, runner: AnswerRunner | None = None,
                 translator: TranslationService | None = None,
                 sink: TurnSink | None = None, tts: Any = None,
                 yield_lookup: YieldLookup | None = None) -> None:
        self._store = store or InMemoryStateStore()
        self._runner = runner or RuntimeAnswerRunner()
        self._translator = translator or get_translation_service()
        self._sink = sink
        self._tts = tts
        self._yield_lookup = yield_lookup or default_yield_lookup
        self._catalog = get_crop_catalog()
        self._lgd = get_lgd_directory()

    # ── public ──────────────────────────────────────────────────────────────
    async def handle(self, inp: TurnInput) -> TurnResult:
        state = await self._load_state(inp)
        pending_before = state.pending
        resume = self._resume_pending(state, inp)
        text = resume.text if resume else inp.text.strip()
        nlu = await nlu_service.parse(text, language_hint=state.language)
        q = resume or _Question(text=text, language=nlu.language, intent=nlu.intent)
        state.remember("user", inp.text, nlu.language)

        if resume is None and pending_before is not None and nlu.intent in _NOT_A_QUESTION:
            # The reply did not fill the slot and is not a new farming question: keep the
            # original question and ask again (with fresh choices if the reply was ambiguous).
            result = self._reask(state, pending_before, nlu)
        else:
            result = await self._dispatch(state, inp, nlu, q)
        if q.resumed:
            result.resumed_question = q.text
        if inp.speak and self._tts is not None and result.reply_text:
            result.audio_uuid = await self._speak(result.reply_text, state.language, result)

        state.remember("assistant", result.reply_text, state.language)
        await self._store.save(state)
        await self._persist(state, inp, result)
        return result

    # ── turn steps ──────────────────────────────────────────────────────────
    async def _load_state(self, inp: TurnInput) -> DialogueState:
        state = await self._store.get(inp.conversation_id) if inp.conversation_id else None
        if state is None or state.user_uuid != inp.user_uuid:
            state = DialogueState.new(inp.user_uuid, inp.language, inp.acting_for_farmer_id)
        state.language = inp.language or state.language
        return state

    def _resume_pending(self, state: DialogueState, inp: TurnInput) -> _Question | None:
        """If this turn answers the pending clarification, return the question to resume."""
        pending = state.pending
        if pending is None:
            return None
        state.pending = None
        if not self._fill_pending(state, pending, inp):
            return None  # the farmer asked something new instead
        return _Question(text=pending.original_text, language=pending.original_language,
                         intent=Intent(pending.intent), answered_slot=pending.slot, resumed=True)

    def _reask(self, state: DialogueState, pending: Pending, nlu: NLUResult) -> TurnResult:
        q = _Question(text=pending.original_text, language=pending.original_language,
                      intent=Intent(pending.intent))
        e = nlu.entities
        if pending.slot == "district" and len(e.district_candidates) > 1:
            choices = [self._district_choice(c) for c in e.district_candidates]
            key = "pick_district"
        elif pending.slot == "crop" and e.crop_status == "ambiguous" and e.crop_candidates:
            choices = [self._crop_choice(c, state.language) for c in e.crop_candidates]
            key = "pick_crop"
        else:
            choices = pending.choices
            key = f"{'pick' if choices else 'ask'}_{pending.slot}"
        clarification = self._clarify(state, pending.slot, key, choices, q)
        return self._result(state, "clarification", clarification["question"], q, nlu,
                            clarification=clarification)

    async def _dispatch(self, state: DialogueState, inp: TurnInput, nlu: NLUResult,
                        q: _Question) -> TurnResult:
        clarification = self._merge_entities(state, nlu, q)
        if clarification is None and q.intent in REQUIRED_SLOTS:
            self._apply_profile(state, inp.profile)
            clarification = self._ask_missing(state, inp.profile, q)
        if clarification is not None:
            return self._result(state, "clarification", clarification["question"], q, nlu,
                                clarification=clarification)
        if q.intent is Intent.SMALLTALK:
            return self._result(state, "smalltalk", message("greeting", state.language), q, nlu)
        if q.intent in REFUSED:
            return self._result(state, "refused", message("out_of_scope", state.language), q,
                                nlu)
        if q.intent is Intent.YIELD and state.crop and state.district_lgd_code:
            return await self._answer_yield(state, nlu, q)
        return await self._answer(state, inp, nlu, q)

    async def _answer_yield(self, state: DialogueState, nlu: NLUResult,
                            q: _Question) -> TurnResult:
        lang = state.language
        entry = self._catalog.get(state.crop)
        names = {"crop": entry.display_name(lang) if entry else state.crop,
                 "district": state.district_name or str(state.district_lgd_code)}
        try:
            f = await self._yield_lookup(state.district_lgd_code, state.crop, state.season)
        except Exception as exc:
            logger.warning("yield lookup failed: {}", exc)
            f = None
        providers = {"nlu": nlu.provider, "yield": f["model_version"] if f else None}
        if f is None:
            return self._result(state, "answered", message("yield_none", lang).format(**names),
                                q, nlu, providers=providers)
        if f["abstained"]:
            return self._result(state, "answered",
                                message("yield_abstain", lang).format(**names), q, nlu,
                                providers=providers, yield_forecast={**f, "official": False})
        change = f["change_vs_normal"]
        pct = round(abs(change) * 100)
        key = ("yield_change_near" if abs(change) < NEAR_NORMAL
               else "yield_change_below" if change < 0 else "yield_change_above")
        year = f"{f['crop_year']}-{str(f['crop_year'] + 1)[-2:]}"
        text = message("yield_forecast", lang).format(
            **names, season=f["season"], year=year, value=f"{f['predicted_yield']:.2f}",
            low=f"{f['interval_low']:.2f}", high=f"{f['interval_high']:.2f}",
            normal=f"{f['normal_yield']:.2f}", unit=UNIT_LABEL.get(f["unit"], f["unit"]),
            change=message(key, lang).format(pct=pct))
        parts = [text, message("yield_disclaimer", lang)]
        review = bool(f["requires_human_review"])
        if review:
            parts.append(message("yield_review", lang))
        return self._result(state, "answered", "\n\n".join(parts), q, nlu, providers=providers,
                            requires_review=review,
                            review_reason="yield_uncertain" if review else None,
                            yield_forecast={**f, "official": False})

    async def _persist(self, state: DialogueState, inp: TurnInput, result: TurnResult) -> None:
        if self._sink is None:
            return
        try:
            await self._sink(state, inp, result)
        except Exception:  # audit persistence must not break the conversation
            logger.exception("Conversation turn persistence failed")

    # ── slots ───────────────────────────────────────────────────────────────
    def _fill_pending(self, state: DialogueState, pending: Pending, inp: TurnInput) -> bool:
        value = None
        if inp.choice and inp.choice.get("slot") == pending.slot:
            value = inp.choice.get("value")
        else:  # free-text answer: a chip label, or text that resolves to the slot
            text = inp.text.strip().casefold()
            for c in pending.choices:
                if text and text in {str(c["label"]).casefold(), str(c["value"]).casefold()}:
                    value = c["value"]
            if value is None and pending.slot == "crop":
                value = self._catalog.resolve(inp.text).crop
            if value is None and pending.slot == "district":
                d = self._lgd.resolve_district(inp.text.strip())
                value = d.lgd_district_code if d else None
        if value is None:
            return False
        self._set_slot(state, pending.slot, value)
        return True

    def _set_slot(self, state: DialogueState, slot: str, value: Any) -> None:
        if slot == "crop" and value in self._catalog:
            state.crop = str(value)
        elif slot == "district":
            d = self._lgd.district(int(value))
            if d is not None:
                state.district_lgd_code = d.lgd_district_code
                state.district_name, state.state_name = d.district_name, d.state_name

    def _merge_entities(self, state: DialogueState, nlu: NLUResult,
                        q: _Question) -> dict[str, Any] | None:
        """Copy resolved entities into the state; ambiguity becomes a clarification. The slot
        the farmer just answered (``q.answered_slot``) is never re-asked for this question."""
        e = nlu.entities
        if q.answered_slot != "crop":
            if e.crop:
                state.crop = e.crop
            elif e.crop_status in {"ambiguous", "multiple"} and e.crop_candidates:
                choices = [self._crop_choice(c, state.language) for c in e.crop_candidates]
                return self._clarify(state, "crop", "pick_crop", choices, q)
        if q.answered_slot != "district":
            if e.district_lgd_code:
                self._set_slot(state, "district", e.district_lgd_code)
            elif len(e.district_candidates) > 1:
                choices = [self._district_choice(c) for c in e.district_candidates]
                return self._clarify(state, "district", "pick_district", choices, q)
        if e.season:
            state.season = e.season
        return None

    def _apply_profile(self, state: DialogueState, profile: FarmerProfile | None) -> None:
        if profile is None:
            return
        if state.district_lgd_code is None and profile.district_lgd_code:
            self._set_slot(state, "district", profile.district_lgd_code)
        if state.crop is None and len(profile.crops) == 1:
            self._set_slot(state, "crop", profile.crops[0])

    def _ask_missing(self, state: DialogueState, profile: FarmerProfile | None,
                     q: _Question) -> dict[str, Any] | None:
        for slot in REQUIRED_SLOTS[q.intent]:
            if slot == "crop" and state.crop is None:
                crops = [c for c in (profile.crops if profile else []) if c in self._catalog]
                choices = [self._crop_choice(c, state.language) for c in crops]
                return self._clarify(state, "crop", "ask_crop", choices, q)
            if slot == "district" and state.district_lgd_code is None:
                return self._clarify(state, "district", "ask_district", [], q)
        return None

    def _clarify(self, state: DialogueState, slot: str, key: str,
                 choices: list[dict[str, Any]], q: _Question) -> dict[str, Any]:
        state.pending = Pending(slot=slot, choices=choices, original_text=q.text,
                                original_language=q.language, intent=q.intent.value)
        return {"slot": slot, "question": message(key, state.language), "choices": choices}

    def _crop_choice(self, key: str, language: str) -> dict[str, Any]:
        entry = self._catalog.get(key)
        return {"value": key, "label": entry.display_name(language) if entry else key}

    def _district_choice(self, lgd_code: int) -> dict[str, Any]:
        d = self._lgd.district(lgd_code)
        label = f"{d.district_name}, {d.state_name}" if d else str(lgd_code)
        return {"value": lgd_code, "label": label}

    # ── answering ───────────────────────────────────────────────────────────
    async def _answer(self, state: DialogueState, inp: TurnInput, nlu: NLUResult,
                      q: _Question) -> TurnResult:
        providers: dict[str, Any] = {"nlu": nlu.provider}
        goal_en = q.text
        if q.language != "en" and not nlu.romanized:
            tin = await self._translator.translate(q.text, q.language, "en", personal_data=True)
            providers["translation_in"] = {"provider": tin.provider, "status": tin.status.value}
            if tin.status in DELIVERABLE:
                goal_en = tin.text
        if inp.context_en:
            goal_en = (f"{inp.context_en}\n\nThe farmer asks about this official bulletin: "
                       f"{goal_en}")
        entry = self._catalog.get(state.crop) if state.crop else None
        answer = await self._runner.run(AnswerContext(
            goal_en=goal_en, session_id=state.conversation_id,
            crop_name_en=entry.name_en.split("(")[0].strip() if entry else None,
            district=state.district_name, state=state.state_name, season=state.season,
            auth=inp.auth,
        ))
        providers["agents"] = answer.agents
        if not answer.text_en:
            return self._result(state, "answered", message("no_grounded_answer", state.language),
                                q, nlu, providers=providers, requires_review=True,
                                review_reason=answer.review_reason or "no_answer")

        reply, reply_status = answer.text_en, TranslationStatus.PASSTHROUGH
        requires_review, reason = answer.requires_review, answer.review_reason
        if state.language != "en":
            out = await self._translator.translate(answer.text_en, "en", state.language,
                                                   personal_data=True)
            reply_status = out.status
            providers["translation_out"] = {"provider": out.provider, "status": out.status.value}
            if out.status in DELIVERABLE:
                reply = out.text
            else:  # unverified translation: never show it; show English + notice, escalate
                reply = f"{message('translation_unverified', state.language)}\n\n{answer.text_en}"
                requires_review, reason = True, "translation_unverified"
        return self._result(state, "answered", reply, q, nlu, reply_en=answer.text_en,
                            citations=answer.citations, translation_status=reply_status.value,
                            providers=providers, requires_review=requires_review,
                            review_reason=reason, weather=answer.weather)

    async def _speak(self, text: str, language: str, result: TurnResult) -> str | None:
        try:
            tts = await self._tts.synthesize(text=text, language=language)
            result.providers["tts"] = {"provider": tts.model_name, "version": tts.model_version}
            return str(tts.audio_uuid)
        except Exception as exc:  # speech is optional; the text answer stands
            logger.warning("TTS failed: {}", type(exc).__name__)
            result.providers["tts"] = {"error": type(exc).__name__}
            return None

    def _result(  # noqa: PLR0913 - keyword-only builder for the response record
        self, state: DialogueState, status: str, reply: str, q: _Question, nlu: NLUResult, *,
        reply_en: str | None = None, clarification: dict[str, Any] | None = None,
        citations: list[dict[str, Any]] | None = None, translation_status: str | None = None,
        providers: dict[str, Any] | None = None, requires_review: bool = False,
        review_reason: str | None = None, weather: dict[str, Any] | None = None,
        yield_forecast: dict[str, Any] | None = None,
    ) -> TurnResult:
        return TurnResult(
            conversation_id=state.conversation_id, turn_id=uuid.uuid4().hex, status=status,
            language=state.language, reply_text=reply, reply_text_en=reply_en,
            intent=q.intent.value, detected_language=nlu.language, clarification=clarification,
            citations=citations or [], slots={
                "crop": state.crop, "district_lgd_code": state.district_lgd_code,
                "district_name": state.district_name, "season": state.season},
            translation_status=translation_status, requires_review=requires_review,
            review_reason=review_reason, providers=providers or {"nlu": nlu.provider},
            weather=weather, symptoms=list(nlu.entities.symptoms),
            yield_forecast=yield_forecast,
        )
