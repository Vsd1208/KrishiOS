"""E5 embedding models need query/passage prefixes; others need none."""

from app.knowledge.embeddings.prefixes import embedding_prefix


def test_e5_models_get_prefixes() -> None:
    assert embedding_prefix("intfloat/multilingual-e5-small", "query") == "query: "
    assert embedding_prefix("intfloat/e5-base-v2", "passage") == "passage: "


def test_other_models_get_none() -> None:
    assert embedding_prefix("all-MiniLM-L6-v2", "query") == ""
    assert embedding_prefix("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                            "passage") == ""
