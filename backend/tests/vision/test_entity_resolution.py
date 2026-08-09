"""Tests for Vision entity resolution integration."""

from app.graph.extraction.entity_resolver import EntityResolver
from app.graph.extraction.types import ExtractedEntity

def test_entity_resolution_vision_crop():
    resolver = EntityResolver()
    
    # Mock lookup
    resolver._lookups = {
        "crop": {"rice": "Paddy", "cotton": "Cotton"}
    }
    
    ext_entity = ExtractedEntity(raw_text="rice", entity_type="crop", start_char=0, end_char=4, confidence=1.0)
    res_entity = resolver.resolve(ext_entity)
    
    assert res_entity is not None
    assert res_entity.canonical_name == "Paddy"

def test_entity_resolution_vision_symptom():
    resolver = EntityResolver()
    
    resolver._lookups = {
        "symptom": {"yellowing leaves": "Chlorosis"}
    }
    
    ext_entity = ExtractedEntity(raw_text="yellowing leaves", entity_type="symptom", start_char=0, end_char=16, confidence=0.8)
    res_entity = resolver.resolve(ext_entity)
    
    assert res_entity is not None
    assert res_entity.canonical_name == "Chlorosis"
