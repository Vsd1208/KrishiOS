"""Section path per PDF page (Phase 10c), used to give each indexed passage a header.

A passage embedded on its own does not know which chapter it is in: in a crop guide, a dose
paragraph from the paddy-nursery section reads like one from the direct-seeded-rice section.
Prefixing the passage with "guide title | crop chapter > section" lets search tell them apart.

The path comes from headings printed in a larger font than the body text, the font size giving
the level. PDF bookmarks were not used: in the TNAU guide they often omit the crop ("5. OILSEEDS >
CROP MANAGEMENT") where the printed headings name it ("MAIZE > i. IRRIGATED MAIZE"). Bold
body-size text is ignored: in these guides it is mostly table headers and emphasis.
"""

from __future__ import annotations

import re
import statistics
from typing import Any

MAX_PATH_CHARS = 160
MIN_HEADING_STEP = 1.0  # points above the body font size
MAX_HEADING_CHARS = 80
MIN_HEADING_CHARS = 3
PATH_LEVELS = 3  # deepest levels kept in the path


def _clean(title: str) -> str:
    return re.sub(r"\s+", " ", title).strip(" .:-")


def _from_fonts(doc: Any) -> dict[int, str]:
    """Headings = short lines in a font larger than the body text; size gives the level."""
    sizes: list[float] = []
    pages: list[list[tuple[float, str]]] = []
    for page in doc:
        heads: list[tuple[float, str]] = []
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                spans = [s for s in line["spans"] if s["text"].strip()]
                sizes.extend(round(s["size"], 1) for s in spans)
                text = _clean(" ".join(s["text"] for s in spans))
                short = MIN_HEADING_CHARS <= len(text) <= MAX_HEADING_CHARS
                if spans and short and re.search(r"[A-Za-z]", text):
                    heads.append((max(s["size"] for s in spans), text))
        pages.append(heads)
    if not sizes:
        return {}
    body = statistics.mode(sizes)
    stack: list[tuple[float, str]] = []
    out: dict[int, str] = {}
    for p, heads in enumerate(pages, start=1):
        for size, text in heads:
            if size < body + MIN_HEADING_STEP:
                continue
            while stack and stack[-1][0] <= size:
                stack.pop()
            stack.append((size, text))
        out[p] = " > ".join(t for _, t in stack[-PATH_LEVELS:])[:MAX_PATH_CHARS]
    return out


def pdf_section_paths(data: bytes) -> dict[int, str]:
    """{page number (1-based): section path} for a PDF; empty if it cannot be read."""
    try:
        import pymupdf  # noqa: PLC0415 - optional, only needed when building an index
    except ImportError:  # pragma: no cover
        return {}
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception:  # an unreadable file just gets no headers
        return {}
    return _from_fonts(doc)
