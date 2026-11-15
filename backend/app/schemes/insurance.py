"""F15 insurance helper: PMFBY explanation, deadlines and crop-loss intimation guidance, plus
the district yield outlook as context.

The yield context is a model estimate and is always labelled as **not** an official
YES-TECH, crop-cutting or claim estimate. The guidance items (``insurance_guidance.yaml``) are
shown to farmers only once an officer has verified the PMFBY scheme entry against its source.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

GUIDANCE = Path(__file__).with_name("insurance_guidance.yaml")
YIELD_NOTICE = {
    "en": "Yield outlook from the KrishiOS model: an estimate, NOT an official YES-TECH, "
          "crop-cutting or insurance claim figure. Claims are decided only by the insurer.",
    "hi": "KrishiOS मॉडल का उपज अनुमान: यह केवल अनुमान है, आधिकारिक YES-TECH, फसल कटाई या "
          "बीमा दावा आंकड़ा नहीं। दावे केवल बीमा कंपनी तय करती है।",
    "te": "KrishiOS మోడల్ దిగుబడి అంచనా: ఇది అంచనా మాత్రమే, అధికారిక YES-TECH, పంట కోత లేదా "
          "బీమా క్లెయిమ్ అంకె కాదు. క్లెయిమ్‌లను బీమా కంపెనీ మాత్రమే నిర్ణయిస్తుంది.",
}


@lru_cache(maxsize=1)
def guidance_items() -> list[dict[str, Any]]:
    items = yaml.safe_load(GUIDANCE.read_text(encoding="utf-8"))
    for it in items:
        missing = {"id", "source", "source_url", "text"} - set(it)
        if missing or set(it["text"]) != {"en", "hi", "te"}:
            raise ValueError(f"insurance guidance item {it.get('id')} is incomplete: {missing}")
    return items


def build_helper(*, scheme: dict[str, Any] | None, verified: bool, officer: bool,
                 language: str, yield_card: dict[str, Any] | None) -> dict[str, Any]:
    show = verified or officer
    items = [
        {"id": it["id"], "text": it["text"].get(language) or it["text"]["en"],
         "source": it["source"], "source_url": it["source_url"],
         **({"checked": it.get("checked"), "needs_official_source":
             it.get("needs_official_source")} if officer else {})}
        for it in guidance_items()
    ] if show else []
    return {
        "scheme": scheme,
        "status": "verified" if verified else "pending_officer_verification",
        "guidance": items,
        "official_portal": "https://pmfby.gov.in/",
        "yield_context": None if yield_card is None else {
            **yield_card, "official": False,
            "notice": YIELD_NOTICE.get(language, YIELD_NOTICE["en"])},
    }
