"""WER/CER with script-aware normalisation (Telugu, Devanagari, Latin).

Normalisation (applied identically to reference and hypothesis): NFC, casefold, map
Devanagari/Telugu digits to ASCII, drop punctuation (keeping Indic combining marks), and
collapse whitespace. Zero-width joiners are removed because Telugu text is inconsistent
about them.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

import jiwer

_DIGITS = {**{0x0966 + i: str(i) for i in range(10)}, **{0x0C66 + i: str(i) for i in range(10)}}
_TOKEN = re.compile(r"[\wऀ-ॿఀ-౿]+")
_ZW = dict.fromkeys(map(ord, "​‌‍﻿"))


def normalize_for_wer(text: str) -> str:
    text = unicodedata.normalize("NFC", text).casefold().translate(_DIGITS).translate(_ZW)
    text = text.replace("।", " ").replace("॥", " ")  # danda, double danda
    return " ".join(_TOKEN.findall(text))


@dataclass(frozen=True, slots=True)
class ErrorRates:
    wer: float
    cer: float
    n_utterances: int
    n_ref_words: int


def error_rates(references: list[str], hypotheses: list[str]) -> ErrorRates:
    """Corpus-level WER and CER (errors summed over the corpus, not averaged per utterance)."""
    refs = [normalize_for_wer(r) for r in references]
    hyps = [normalize_for_wer(h) for h in hypotheses]
    keep = [(r, h) for r, h in zip(refs, hyps, strict=True) if r]
    r_list, h_list = [k[0] for k in keep], [k[1] for k in keep]
    return ErrorRates(
        wer=round(jiwer.wer(r_list, h_list), 4),
        cer=round(jiwer.cer(r_list, h_list), 4),
        n_utterances=len(keep),
        n_ref_words=sum(len(r.split()) for r in r_list),
    )
