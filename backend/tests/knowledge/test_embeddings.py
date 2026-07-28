"""Unit tests for metadata extractor and embedding pipeline logic."""

from uuid import uuid4

from app.knowledge.interfaces.chunker import TextChunk
from app.knowledge.metadata.extractor import MetadataExtractor


def test_metadata_extractor() -> None:
    extractor = MetadataExtractor()
    text = "Detailed guidelines for Kharif season rice cultivation in Karnal district, Haryana."

    extracted = extractor.extract(text)
    assert extracted.detected_language == "en"
    assert extracted.detected_season == "kharif"
    assert extracted.detected_crop == "rice"


def test_metadata_extractor_hindi() -> None:
    extractor = MetadataExtractor()
    text = "खरीफ सीजन में धान की खेती के लिए सिफारिशें।"

    extracted = extractor.extract(text)
    assert extracted.detected_language in {"hi", "mr"}
    assert extracted.detected_season == "kharif"
