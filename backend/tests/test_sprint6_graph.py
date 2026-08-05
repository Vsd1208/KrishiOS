"""Tests for Sprint 6 Graph Knowledge."""

import json
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.graph.extraction.entity_extractor import DictionaryEntityExtractor
from app.graph.extraction.entity_resolver import EntityResolver
from app.graph.extraction.relationship_extractor import PatternRelationshipExtractor
from app.graph.validation.relationship_validator import RelationshipValidator


@pytest.fixture
def golden_dataset() -> list[dict]:
    path = Path(__file__).parent / "golden_dataset.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.asyncio
async def test_entity_extraction(golden_dataset: list[dict]):
    """Test entity extraction against golden dataset."""
    extractor = DictionaryEntityExtractor()
    resolver = EntityResolver()

    for item in golden_dataset:
        metadata = {"crop": item["crop"]}
        
        # 1. Extract
        raw_entities = await extractor.extract(item["text"], document_metadata=metadata)
        
        # 2. Resolve
        resolved_entities = resolver.resolve_bulk(raw_entities)
        
        extracted_names = {e.canonical_name for e in resolved_entities}
        
        # Verify expected entities were found
        for expected in item["expected_entities"]:
            assert expected["name"] in extracted_names, f"Missing entity {expected['name']} in doc {item['id']}"


@pytest.mark.asyncio
async def test_relationship_extraction_and_validation(golden_dataset: list[dict]):
    """Test relationship extraction and validation."""
    extractor = DictionaryEntityExtractor()
    resolver = EntityResolver()
    rel_extractor = PatternRelationshipExtractor()
    validator = RelationshipValidator()

    for item in golden_dataset:
        metadata = {"crop": item["crop"]}
        
        raw_entities = await extractor.extract(item["text"], document_metadata=metadata)
        resolved_entities = resolver.resolve_bulk(raw_entities)
        
        raw_rels = await rel_extractor.extract(resolved_entities, item["text"], document_metadata=metadata)
        valid_rels = validator.validate(raw_rels)
        
        extracted_triples = {(r.subject.canonical_name, r.predicate, r.obj.canonical_name) for r in valid_rels}
        
        for expected in item["expected_relationships"]:
            triple = (expected["subject"], expected["predicate"], expected["object"])
            assert triple in extracted_triples, f"Missing relationship {triple} in doc {item['id']}"
