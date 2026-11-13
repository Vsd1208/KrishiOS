"""Devanagari <-> Telugu transliteration for IndicTrans2's script-unified I/O.

IndicTrans2 represents Indic text in Devanagari internally (script unification); its
official post-processor converts output back to the native script. The Unicode Devanagari
(U+0900-U+097F) and Telugu (U+0C00-U+0C7F) blocks are ISCII-aligned, so most characters
map by a fixed offset of 0x300. Characters without a Telugu counterpart (e.g. nukta forms)
are mapped to their closest base letter; dandas and Latin text are left unchanged.
"""

from __future__ import annotations

import unicodedata

_OFFSET = 0x0C00 - 0x0900
_DEVA = range(0x0900, 0x0980)
_TELU = range(0x0C00, 0x0C80)
_KEEP = {0x0964, 0x0965}  # danda, double danda: shared punctuation


def _assigned(cp: int) -> bool:
    return unicodedata.category(chr(cp)) != "Cn"


def _build_maps() -> tuple[dict[int, str], dict[int, str]]:
    deva_to_telu: dict[int, str] = {}
    telu_to_deva: dict[int, str] = {}
    for cp in _DEVA:
        if cp in _KEEP or not _assigned(cp):
            continue
        target = cp + _OFFSET
        if target in _TELU and _assigned(target):
            deva_to_telu[cp] = chr(target)
            telu_to_deva[target] = chr(cp)
    # Nukta forms (Devanagari-only) -> base consonant; the nukta sign itself is dropped.
    for composed in "क़ख़ग़ज़ड़ढ़फ़य़":
        base = unicodedata.normalize("NFD", composed)[0]
        deva_to_telu[ord(composed)] = chr(ord(base) + _OFFSET)
    deva_to_telu[0x093C] = ""  # nukta
    return deva_to_telu, telu_to_deva


_DEVA_TO_TELU, _TELU_TO_DEVA = _build_maps()


def devanagari_to_telugu(text: str) -> str:
    return text.translate(_DEVA_TO_TELU)


def telugu_to_devanagari(text: str) -> str:
    return text.translate(_TELU_TO_DEVA)
