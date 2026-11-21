"""Input prefixes some embedding models were trained with (Phase 10c).

The E5 family (e.g. ``intfloat/multilingual-e5-small``) expects ``"query: "`` before search
queries and ``"passage: "`` before indexed text; without them retrieval quality drops. Other
models get no prefix.
"""

from typing import Literal


def embedding_prefix(model_name: str, kind: Literal["query", "passage"]) -> str:
    """Return the prefix ``model_name`` expects for a query or an indexed passage."""
    return f"{kind}: " if "e5" in model_name.lower().split("/")[-1].split("-") else ""
