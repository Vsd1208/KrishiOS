# 🌾 KrishiOS — AI Decision Intelligence Platform for Indian Agriculture

[![Vitest Tests](https://img.shields.io/badge/Tests-50%2F50%20PASS-brightgreen.svg)]()
[![TypeScript](https://img.shields.io/badge/TypeScript-Strict%200%20Errors-blue.svg)]()
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%200.115-teal.svg)]()
[![React](https://img.shields.io/badge/Frontend-React%2019%20%2B%20Vite-indigo.svg)]()
[![Buildathon Status](https://img.shields.io/badge/Buildathon-Submission%20Ready-gold.svg)]()

> **From farmer question to evidence-backed agricultural decision.**  
> KrishiOS bridges the gap between multimodal Indian farmer inquiries (Telugu/Hindi/English voice, text, crop disease photos) and trustworthy agricultural extension officer oversight using hybrid RAG, GraphRAG, and real-time agromet intelligence.

---

## 🏗️ 1. Architecture Overview

```
                            FARMER
                              │
                     Text / Voice / Image
                              │
                              ▼
                     KRISHIOS FRONTEND
                              │
                              ▼
                      AGENT RUNTIME
                              │
           ┌──────────────────┼──────────────────┐
           ▼                  ▼                  ▼
          RAG              GraphRAG            Vision
           │                  │                  │
           └──────────────────┼──────────────────┘
                              │
                              ▼
                        LIVE CONTEXT
                      Weather / Market
                              │
                              ▼
                        EVIDENCE LAYER
                              │
                  ┌───────────┼───────────┐
                  ▼           ▼           ▼
              Confidence   Freshness   Citations
                  │           │           │
                  └───────────┼───────────┘
                              ▼
                       AI ADVISORY
                              │
                      Risk / Decision
                              │
                              ▼
                      HUMAN OFFICER
                              │
                              ▼
                        FINAL ACTION
                              │
                              ▼
                        TRUST CENTER
```

### Knowledge & Data Infrastructure:
- **Vector Retrieval**: Qdrant vector database (`krishios-live`) with immutable Blue/Green alias promotion.
- **Knowledge Graph**: Neo4j with ICAR ontological entities (*Crop $\to$ Pest $\to$ Treatment $\to$ Spray Constraints*).
- **Relational Store**: PostgreSQL 16 for users, plots, soil profiles, and proactive decision records.
- **Live Data**: Open-Meteo & IMD Agromet APIs for 7-day spray feasibility windows and Mandi market prices.

---

## 🌟 2. Key Differentiators

| Capability | Generic Chatbot | KrishiOS Platform |
| :--- | :--- | :--- |
| **Input Modality** | Text prompt only | Multimodal: Telugu/Hindi Voice + Crop leaf photos + Plot soil context |
| **Scientific Provenance** | Unverified / Hallucinatory | Strict RAG citations from ICAR Package of Practices with page numbers |
| **Domain Reasoning** | Keyword matching | GraphRAG multi-hop causal reasoning (*Disease $\to$ Pathogen $\to$ Safe Chemical*) |
| **Live Telemetry** | Stale / Static | Real-time micro-climate sensors & 7-day agricultural spray window feasibility |
| **Safety & Governance** | Black-box output | Human-in-the-Loop agricultural officer review queue for high-impact decisions |
| **Observability** | None | Dedicated AI Trust & Evaluation Center with Blue/Green index status |

---

## 🚀 3. Quick Start

### Prerequisites
- Node.js (v18+) & npm
- Python 3.12 & `uv` (or Docker Desktop)
- PostgreSQL, Qdrant, Neo4j

### 1. Start Backend Services
```bash
cd backend
cp .env.example .env
# Start FastAPI application
uv run fastapi dev app/main.py
```
*Backend runs on `http://localhost:8000` (OpenAPI docs at `http://localhost:8000/docs`).*

### 2. Start Frontend Application
```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```
*Frontend opens at `http://localhost:5173`.*

### 3. Run Automated Checks
```bash
cd frontend
npm run typecheck    # 0 errors
npm run lint         # 0 errors
npm test             # 50/50 tests pass (26 test files)
npm run build        # Clean production build (dist/)
```

---

## 🎬 4. Golden Demo Workflow (3–5 Minutes)

### **Part 1: The Telugu Farmer Experience**
1. **Login**: Navigate to `/login` and sign in as a farmer.
2. **Context**: Farmer Home renders personalized paddy landholding details, plot soil health (pH 6.8), and live Agromet weather.
3. **Multimodal Inquiry**:
   - Switch language to **తెలుగు (Telugu)**.
   - Click microphone to ask: *"నా వరి పంటలో ఆకుమచ్చ తెగులు లక్షణాలు కనిపిస్తున్నాయి, ఏమి చేయాలి?"*
   - Attach leaf diagnostic photo.
4. **Grounded Advisory**:
   - KrishiOS executes Agent Runtime fusing CropNet Vision, ICAR RAG citations, and GraphRAG treatment paths.
   - Displays **AI Confidence: 92%**, **Freshness: Live**, and **Verified ICAR NRRI Sources**.
   - Listen to synthesized Telugu spoken audio advisory.

### **Part 2: The Agricultural Officer Review & Trust Center**
1. **Advisory Verification**:
   - High-impact recommendations route to `/officer/reviews`.
   - Officer inspects evidence trace, verifies chemical dosage safety, and signs off.
2. **AI Trust & Evaluation Center (`/officer/evaluation`)**:
   - Visualizes Blue/Green knowledge index status (`krishios-live`).
   - Deep-dive into decision traces, ontological paths, and human review metrics.

---

## 📊 5. Verified Test Baseline

- **Unit & Component Tests**: `50 / 50 passed (100%)`
- **TypeScript**: `0 errors` (`tsc --noEmit`)
- **ESLint**: `0 errors` (`eslint src/`)
- **Production Build**: Clean production bundle with code-splitting chunks.

---

## 🔒 6. Responsible AI Guardrails

- **Confidence $\neq$ Certainty**: AI confidence is labeled explicitly as *"AI Confidence"* (never absolute diagnosis).
- **Low-Confidence Safety Prompts**: When confidence $< 75\%$, KrishiOS prompts field verification prior to chemical spray.
- **Zero Fabricated Citations**: Citations and GraphRAG chains strictly originate from validated backend evidence.
- **Role-Guarded Access**: Officer evaluation tools and review queues are protected by RBAC.

---

## 👥 7. Repository Structure

```
├── backend/                  # FastAPI backend, migrations, and AI pipeline
│   ├── app/
│   │   ├── agents/           # Multi-agent orchestration runtime
│   │   ├── graph/            # Neo4j GraphRAG integration
│   │   ├── retrieval/        # Enterprise semantic retrieval & Blue/Green indexing
│   │   ├── vision/           # CropNet leaf disease analysis
│   │   ├── voice/            # Multilingual STT & speech pipeline
│   │   └── proactive/        # Event-driven agricultural risk intelligence
├── frontend/                 # React 19 + TypeScript + Vite frontend
│   ├── src/
│   │   ├── app/              # Router, providers, and environment config
│   │   ├── components/       # Reusable UI & AI explainability design system
│   │   ├── features/         # Farmer, Officer, and AI Workspace modules
│   │   ├── pages/            # Farmer Portal, Officer Console & Trust Center
│   │   ├── services/         # Centralized API client & feature endpoints
│   │   └── types/            # TypeScript contracts & domain models
└── docs/                     # Technical specifications & PRD documents
```

---

## 📄 License
Licensed under the Apache License 2.0.
