"""Unit tests for document parsers, text cleaner, and parser selector."""

import pytest
from app.knowledge.ingestion.cleaning import TextCleaner
from app.knowledge.parsers.docx import DocxParser
from app.knowledge.parsers.image import ImageParser
from app.knowledge.parsers.pdf import PdfParser
from app.knowledge.parsers.selector import ParserSelector
from app.knowledge.parsers.txt import TxtParser


@pytest.mark.asyncio
async def test_txt_parser() -> None:
    parser = TxtParser()
    assert parser.supports("text/plain") is True
    assert parser.supports("application/pdf") is False

    content = b"Page 1 content\fPage 2 content"
    parsed = await parser.parse(content, "test.txt")

    assert parsed.total_pages == 2
    assert parsed.pages[0].text == "Page 1 content"
    assert parsed.pages[1].text == "Page 2 content"
    assert "Page 1 content" in parsed.full_text


@pytest.mark.asyncio
async def test_text_cleaner() -> None:
    cleaner = TextCleaner()
    raw_text = "ﬁrst  line\n\n\n\n\n\nRepeated Header\nRepeated Header\nRepeated Header\nRepeated Header\nLast line."
    cleaned = cleaner.clean(raw_text)

    assert "first line" in cleaned
    assert "Repeated Header" not in cleaned
    assert "\n\n\n\n" not in cleaned


@pytest.mark.asyncio
async def test_parser_selector_txt() -> None:
    selector = ParserSelector()
    content = b"Sample agricultural text for wheat crop in Punjab."
    parsed, mime = await selector.parse(content, "advisory.txt", mime_type="text/plain")

    assert mime == "text/plain"
    assert parsed.total_pages == 1
    assert "wheat" in parsed.full_text.lower()


@pytest.mark.asyncio
async def test_parser_selector_unsupported() -> None:
    selector = ParserSelector()
    with pytest.raises(ValueError, match="Unsupported MIME type"):
        await selector.parse(b"data", "file.xyz", mime_type="application/x-custom")
