# Sprint 10 Walkthrough — Proactive Agricultural Decision Intelligence Platform

## Overview
KrishiOS has evolved from a reactive AI conversational system into an **Event-Driven Proactive Decision Intelligence Platform**. The platform autonomously detects environmental, biological, market, and institutional changes, matches them against registered farmer profiles and field geometry, evaluates domain risks via modular rule logic, generates multi-source evidence packages (combining Live Telemetry, Qdrant Vector RAG, and Neo4j GraphRAG), enforces human-in-the-loop sign-off for high-impact/uncertain decisions, and delivers deduplicated, localized advisories respecting farmer preferences and quiet hours.

---

## Architecture

```
[ External Telemetry & Ingestion Events ]
(Weather Forecasts, Market Feeds, Vision Findings, Knowledge Indexing, Schemes)
                   │
                   ▼
       [ Event Ingestion & Bus ]
  (EventEnvelope, AsyncEventBus, EventDeduplicator)
                   │
                   ▼
        [ Event Processor & Rules ]
  (Spatial Targeting, HeavyRain, Heat, Disease, Market, Scheme Rules)
                   │ (Rule Matched)
                   ▼
       [ Context Collection Engine ]
  (Farmer Profile, Field Crop Stages, Live Data, Vector RAG, Neo4j GraphRAG)
                   │
                   ▼
     [ Risk Engine & Evidence Packaging ]
  (RiskAssessment, EvidencePackage with Citations & Graph Paths)
                   │
                   ▼
    [ Proactive Agent & Agent Runtime ]
  (ProactiveIntelligenceAgent, Guardrails, Citations, Uncertainty Tracking)
                   │
         ┌─────────┴─────────┐
         │ (High Confidence) │ (High Impact / Low Conf)
         ▼                   ▼
[ Notification Engine ]   [ Officer Review System ]
(Preferences, Channels,    (Pending Review Queue,
 Quiet Hours, 24h Dedup)   Approve, Modify, Reject)
         │                   │
         └─────────┬─────────┘
                   │
                   ▼
        [ Farmer Notification ]
```

---

## Key Modules Implemented

1. **Event System (`app/events/`)**:
   - `EventEnvelope`: Immutable, UUID-tracked, schema-versioned event envelope.
   - `AsyncEventBus`: High-throughput async pub/sub bus with pattern routing (`weather.*`, `*`) and error isolation.
2. **Deduplication Engine (`app/proactive/deduplication.py`)**:
   - Deterministic SHA-256 fingerprinting for events and farmer-level notifications.
   - Cooldown window management suppressing duplicate external triggers and spamming.
3. **Modular Rule & Relevance Engine (`app/proactive/rules/`)**:
   - `HeavyRainfallRule`: Evaluates precipitation intensity and soil drainage.
   - `ExtremeHeatRule`: Detects heatwaves and evapotranspiration stress.
   - `DiseaseRiskRule`: Identifies microclimate spore incubation conditions (humidity + temperature) and host crop susceptibility.
   - `MarketPriceVolatilityRule`: Evaluates commodity price swings (>10-15%) without generating financial speculation.
   - `SchemeEligibilityRule`: Matches farmer landholding and state criteria for government support programs.
4. **Context Collection Engine (`app/proactive/context.py`)**:
   - Queries PostgreSQL for active farmers and standing crop stages (`FieldCrop`).
   - Gathers live weather, agromet advisories, and mandi price telemetry from `LiveDataService`.
   - Enriches context with Neo4j Knowledge Graph paths and Qdrant Vector RAG snippets.
5. **Risk Assessment & Evidence Packaging (`app/proactive/risk/`)**:
   - `RiskEvaluator`: Produces structured `RiskAssessment` objects with severity levels (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) and validity periods.
   - `EvidencePackage`: Auditable snapshot of live telemetry, citations, graph paths, rule versions, and confidence breakdowns.
   - Stale data penalty: Automatically penalizes events older than 72 hours and routes to human review.
6. **Proactive Agent & Workflows (`app/agents/`)**:
   - `ProactiveIntelligenceAgent`: Grounded LLM synthesis triggered only when rules pass.
   - Reusable proactive workflows: `proactive_weather_risk`, `proactive_disease_risk`, `proactive_market_movement`, `proactive_scheme_notification`.
7. **Human-in-the-Loop Review (`app/proactive/review.py`)**:
   - Routes `CRITICAL`/`HIGH` risk assessments with confidence `< 0.80` to `PENDING_REVIEW`.
   - Agricultural Officers can inspect evidence packages, edit advisories, approve, or reject.
8. **Notification Engine & Preferences (`app/notifications/`)**:
   - Multi-channel provider abstractions (`IN_APP`, `SMS`, `PUSH`, `VOICE`).
   - Farmer preference management: quiet hours, preferred language, minimum severity, category toggles.
9. **Database Persistence & Migrations (`app/models/proactive.py`, `0008_sprint_10_proactive_intelligence.py`)**:
   - Tables: `proactive_event_record`, `proactive_decision_record`, `alert_notification_record`, `notification_preference_record`.
10. **REST API Endpoints (`app/proactive/api/`)**:
    - `POST /proactive/events`: Ingest events.
    - `GET /proactive/decisions`: Query past decisions and evidence packages.
    - `GET /proactive/alerts`: List alerts for farmers.
    - `POST /proactive/alerts/{id}/acknowledge`: Mark alert as read.
    - `GET /proactive/reviews`: Officer pending review queue.
    - `POST /proactive/reviews/{id}/action`: Officer approve/reject action.
    - `GET/PUT /proactive/preferences`: Farmer preference management.

---

## Verification & Golden Scenarios

| Test Suite | Scenario Verified | Result |
|---|---|---|
| `test_event_envelope_and_bus.py` | Envelope serialization, wildcard routing, subscriber error isolation | ✅ Passed |
| `test_event_deduplication.py` | Deterministic SHA-256 deduplication and 24h cooldown windows (Scenario 4) | ✅ Passed |
| `test_rule_engine.py` | Heavy rain, extreme heat, disease microclimate, market volatility, scheme eligibility | ✅ Passed |
| `test_proactive_weather_workflow.py` | **Golden Scenario 1**: Heavy rain forecast on Paddy in Nizamabad -> Risk -> Advisory -> Notification | ✅ Passed |
| `test_proactive_disease_workflow.py` | **Golden Scenario 2**: High humidity + Chilli susceptibility + GraphRAG -> Disease Risk Alert without ungrounded diagnosis | ✅ Passed |
| `test_proactive_market_workflow.py` | **Golden Scenario 3**: Mandi price drop (-18%) for Tomato -> Transparent price shift alert | ✅ Passed |
| `test_human_in_the_loop_review.py` | **Golden Scenario 5**: Low confidence / high impact -> `PENDING_REVIEW` -> Officer approval & dispatch | ✅ Passed |
| `test_stale_data_suppression.py` | **Golden Scenario 6**: >72h stale external data penalty -> routing to human review | ✅ Passed |
| `test_notification_preferences.py` | Quiet hours suppression, urgent override, and category toggles | ✅ Passed |

**Overall Result: 17 Passed across all suites in 0.34s.**

---

## Performance, Costs & Observability

- **LLM Invocation Rate**: Invocations occur **only** when rule conditions match affected farmer fields. Polled events with no meaningful change cost 0 LLM tokens.
- **Notification Suppression Rate**: Redundant events within the 24-hour window are suppressed at the deduplicator layer before reaching the notification engine.
- **Explainability**: Every alert dispatched contains explicit source attribution (e.g. IMD, ICAR, Agromet Advisory) and evidence trail.
