"""Deterministic multilingual NLU (always available, no network).

Language ID is script-based. Latin-only text is checked for romanised Hindi/Telugu function
words. Intents come from the multilingual lexicon with explicit priorities (yield > govt
bulletin > scheme > market > disease > weather > advisory > officer > smalltalk). Entities
are resolved only against the crop catalog and the LGD directory.
"""

from __future__ import annotations

from functools import lru_cache

from app.catalog import get_crop_catalog, get_lgd_directory
from app.catalog.phrases import PhraseMatcher
from app.catalog.text import normalize, script_of, tokenize
from app.nlu.lexicon import Lexicon, get_lexicon
from app.nlu.types import Intent, NLUEntities, NLUResult

PROVIDER_NAME = "rule-based-nlu"
_DISTRICT_WORDS = {"district", "dist", "zilla", "jila", "जिला", "जिले", "జిల్లా"}
MIN_ROMANIZED_MARKERS = 2


@lru_cache(maxsize=1)
def _district_matcher() -> tuple[PhraseMatcher, frozenset[str]]:
    """District-name matcher plus names that collide with ordinary words/lexicon phrases
    (e.g. 'Mandi', 'Kota', 'Una'); those only match next to a word for 'district'."""
    lgd = get_lgd_directory()
    lex = get_lexicon()
    names = {d.district_name for d in lgd.districts()}
    pairs = [(n, n) for n in names]
    lexicon_tokens: set[str] = set()
    for matcher in (lex.intents, lex.seasons, lex.symptoms, lex.schemes, lex.times):
        lexicon_tokens.update(matcher.phrases())
    for entry in get_crop_catalog().entries():
        lexicon_tokens.update(normalize(a) for a in entry.aliases)
    common_words = {"kota", "una", "sagar", "leh", "mandi", "durg", "kal", "aaj"}
    collide = frozenset(normalize(n) for n in names
                        if normalize(n) in lexicon_tokens or normalize(n) in common_words)
    return PhraseMatcher(pairs), collide


def detect_language(text: str, lexicon: Lexicon,
                    hint: str | None = None) -> tuple[str, str, bool, bool]:
    """Return (language, script, is_code_switched, romanized)."""
    tokens = tokenize(text)
    scripts = [script_of(t) for t in tokens]
    te, hi, lat = scripts.count("telugu"), scripts.count("devanagari"), scripts.count("latin")
    if te or hi:
        lang = "te" if te >= hi else "hi"
        return lang, "telugu" if lang == "te" else "devanagari", lat > 0, False
    marks = {k: sum(t in v for t in tokens) for k, v in lexicon.romanized_markers.items()}
    best = max(marks, key=marks.__getitem__) if marks else None
    if best and marks[best] >= MIN_ROMANIZED_MARKERS and marks[best] > min(marks.values()):
        return best, "latin", True, True
    if hint in {"te", "hi"} and best and marks[best] >= 1:
        return hint, "latin", True, True
    return "en", "latin", False, False


class RuleBasedNLUProvider:
    provider_name = PROVIDER_NAME

    def __init__(self) -> None:
        self._lex = get_lexicon()
        self.model_version = self._lex.version

    def _districts(self, text: str) -> tuple[int | None, str | None, tuple[int, ...]]:
        matcher, collide = _district_matcher()
        tokens = tokenize(text)
        lgd = get_lgd_directory()
        found: list[int] = []
        for hit in matcher.find(text):
            name_norm = normalize(hit.label)
            near = set(tokens[max(0, hit.token_start - 1): hit.token_end + 1])
            if name_norm in collide and not near & _DISTRICT_WORDS:
                continue
            found.extend(d.lgd_district_code for d in lgd.find_districts(hit.label))
        unique = tuple(sorted(set(found)))
        if len(unique) == 1:
            d = lgd.district(unique[0])
            return unique[0], d.district_name if d else None, unique
        return None, None, unique

    def parse_sync(self, text: str, language_hint: str | None = None) -> NLUResult:
        lex = self._lex
        language, script, code_switched, romanized = detect_language(text, lex, language_hint)

        hits = lex.intents.find(text)
        by_intent: dict[str, int] = {}
        for h in hits:
            by_intent[h.label] = by_intent.get(h.label, 0) + 1
        ranked = sorted(by_intent, key=lambda i: (lex.priorities[i], by_intent[i]), reverse=True)

        crop = get_crop_catalog().resolve(text)
        if ranked:
            primary = Intent(ranked[0])
            secondary = tuple(Intent(i) for i in ranked[1:] if i != Intent.SMALLTALK)
            confidence = min(0.9, 0.6 + 0.1 * by_intent[ranked[0]]) - 0.05 * len(secondary)
        elif crop.status.value != "not_found":
            primary, secondary, confidence = Intent.ADVISORY, (), 0.5
        else:
            primary, secondary, confidence = Intent.OUT_OF_SCOPE, (), 0.4
        if primary is Intent.SMALLTALK and crop.status.value != "not_found":
            primary = Intent.ADVISORY

        code, name, candidates = self._districts(text)
        seasons = lex.seasons.find(text)
        times = lex.times.find(text)
        schemes = lex.schemes.find(text)
        entities = NLUEntities(
            crop=crop.crop,
            crop_status=crop.status.value,
            crop_candidates=crop.candidates,
            district_lgd_code=code,
            district_name=name,
            district_candidates=candidates,
            season=seasons[0].label if seasons else None,
            symptoms=tuple(dict.fromkeys(h.label for h in lex.symptoms.find(text))),
            time_expression=times[0].label if times else None,
            scheme=schemes[0].label if schemes else None,
        )
        return NLUResult(
            intent=primary,
            confidence=round(max(0.3, confidence), 2),
            language=language,
            is_code_switched=code_switched,
            entities=entities,
            secondary_intents=secondary,
            script=script,
            romanized=romanized,
            provider=self.provider_name,
            provider_version=self.model_version,
            evidence=tuple(f"{h.label}:{h.phrase}" for h in hits),
        )

    async def parse(self, text: str, language_hint: str | None = None) -> NLUResult:
        return self.parse_sync(text, language_hint)
