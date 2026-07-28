"""Unit tests for chunking strategies and pipeline."""

from app.knowledge.chunking.pipeline import ChunkingPipeline
from app.knowledge.chunking.recursive import RecursiveChunker
from app.knowledge.chunking.semantic import SemanticChunker
from app.knowledge.interfaces.chunker import ChunkerConfig
from app.knowledge.interfaces.parser import ParsedDocument, ParsedPage


def test_recursive_chunker() -> None:
    chunker = RecursiveChunker()
    config = ChunkerConfig(chunk_size=50, chunk_overlap=10)
    text = "Agricultural advisory for Kharif season. Rice cultivation requires proper water management and nitrogen fertilizers."

    chunks = chunker.chunk(text=text, page_number=1, config=config)
    assert len(chunks) > 0
    assert chunks[0].page_number == 1
    assert all(len(c.text) <= 100 for c in chunks)  # bounded size


def test_semantic_chunker() -> None:
    chunker = SemanticChunker()
    config = ChunkerConfig(chunk_size=100, chunk_overlap=20)
    text = "First sentence about wheat. Second sentence about soil health! Third sentence about irrigation."

    chunks = chunker.chunk(text=text, page_number=1, config=config)
    assert len(chunks) > 0
    assert "First sentence" in chunks[0].text


def test_chunking_pipeline_global_reindexing() -> None:
    pipeline = ChunkingPipeline(config=ChunkerConfig(chunk_size=40, chunk_overlap=5))
    parsed = ParsedDocument(
        pages=[
            ParsedPage(page_number=1, text="Page one text about maize crops."),
            ParsedPage(page_number=2, text="Page two text about fertilizer usage."),
        ],
        total_pages=2,
    )

    chunks = pipeline.run(parsed=parsed, document_type="general", extra_metadata={"crop": "maize"})
    assert len(chunks) >= 2
    # Ensure global reindexing
    for idx, c in enumerate(chunks):
        assert c.chunk_index == idx
        assert c.metadata.get("crop") == "maize"
