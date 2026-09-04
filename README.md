# 🌾 KrishiOS

### The AI Operating System for Indian Agriculture

> From a farmer's question to an evidence-grounded agricultural decision — powered by Agentic AI, RAG, GraphRAG, multimodal intelligence, and human-in-the-loop verification.

[![Status](https://img.shields.io/badge/Status-Buildathon%20Ready-success)](https://github.com/Vsd1208/KrishiOS)
[![Backend](https://img.shields.io/badge/Backend-FastAPI-009688)](#)
[![Frontend](https://img.shields.io/badge/Frontend-React%20%2B%20TypeScript-61DAFB)](#)
[![AI](https://img.shields.io/badge/AI-Agentic%20%2B%20RAG%20%2B%20GraphRAG-purple)](#)
[![Database](https://img.shields.io/badge/Data-PostgreSQL%20%7C%20Qdrant%20%7C%20Neo4j-blue)](#)
[![Tests](https://img.shields.io/badge/Tests-49%20Passed-brightgreen)](#)
[![Docker](https://img.shields.io/badge/Deployment-Docker-2496ED)](#)
[![License](https://img.shields.io/badge/License-TBD-lightgrey)](#)

**Repository:** [github.com/Vsd1208/KrishiOS](https://github.com/Vsd1208/KrishiOS)

---

## 🚜 The Problem

Indian farmers rarely face a single agricultural problem.

A question such as:

> **"My chilli leaves are curling. What should I do?"**

may require understanding the crop and crop stage, pest and disease symptoms, local geography, weather conditions, soil and nutrient context, season, trusted agricultural knowledge, intervention safety, confidence in the recommendation — and, in uncertain cases, human expert verification.

Most agricultural digital solutions solve only one part of this problem. **KrishiOS approaches agriculture as a connected intelligence problem.**

---

## 💡 What is KrishiOS?

KrishiOS is a unified agricultural intelligence platform designed around an **AI Operating System architecture**.

Instead of building independent weather apps, pest chatbots, market dashboards, scheme assistants, and soil systems as disconnected tools, KrishiOS provides a shared intelligence layer that all of these capabilities can run on top of.
The architecture deliberately separates the orchestration runtime, specialist agents, AI services, data layer, and integration layer so individual components can evolve independently.


<p align="center">
<img width="777" height="1224" alt="architecture-diagram-cropped" src="https://github.com/user-attachments/assets/0f47a099-9ce3-410f-a4f0-11e4744a6c9c" />
</p>
---

## ✨ Implemented Capabilities

### 🤖 Agentic AI Runtime

KrishiOS is not a single LLM call. The platform uses an orchestrated agent pipeline:

```
Planner → Knowledge Retrieval Agent → Crop Advisory Agent → Response Validation → Farmer-facing response
```

The runtime provides task planning, agent delegation, tool execution, a shared execution context, structured agent contracts, execution policies, timeouts, validation, result merging, and escalation paths. The architecture is built around a **bounded Plan → Act → Observe → Respond loop** rather than unrestricted autonomous behavior — making the system more predictable and auditable in a domain where incorrect recommendations have real-world consequences.

### 📚 Grounded Agricultural RAG

KrishiOS does not rely exclusively on the LLM's parametric knowledge. Agricultural answers are grounded in a curated knowledge layer currently covering:

| Crop | Knowledge |
|---|---|
| 🌾 Paddy / Rice | Pest, disease and crop-management guidance |
| 🌱 Cotton | Crop health, pest and disease management |
| 🌶️ Chilli | Pest, symptom and general management guidance |

Source material is drawn from ICAR, ICAR-IIRR, TNAU, and Agriculture Department publications. Retrieval supports semantic vector search with crop, state, district, season, language, authority, and document-type filtering, plus **progressive metadata relaxation** — a query can start with highly specific context and safely relax geographic constraints when authoritative documents aren't tagged that way.

### 🧠 Enterprise Retrieval Pipeline

Retrieval is built as a standalone platform capability rather than being embedded inside the chatbot:

```
Farmer Query → Query Embedding → Metadata-aware Retrieval (Crop / State / District / Season)
             → Qdrant Vector Search → Ranking / Reranking → Verified Context → Advisory Agent
```

The retrieval API exposes document search independently from LLM generation, so retrieval quality is testable without involving the language model at all.

### 🔄 Blue-Green Retrieval Indexing

Knowledge updates don't require blindly replacing the production index. The retrieval platform supports immutable index versions, background index construction, validation gates, blue-green promotion, live aliases, rollback, incremental ingestion, and index status/version history.

```
Upload → Ingest → Chunk → Embed → Build new index → Evaluate → Promote → Live alias

New Index ──┬── PASS ──→ Promote
            └── FAIL ──→ Keep current production index
```

This is closer to a production information-retrieval system than a typical chatbot vector store.

### 🔎 Retrieval Evaluation

Rather than assuming similarity search is automatically correct, the validated index pipeline evaluates retrieval quality using **Recall, Precision, MRR, nDCG, Coverage, latency, chunk integrity, and embedding integrity** — giving KrishiOS a measurable retrieval-quality layer instead of treating RAG as a black box. The production retrieval index was validated before promotion.

### 🕸️ GraphRAG / Knowledge Graph

A structured agricultural knowledge graph (Neo4j) complements vector retrieval, capturing relationships between entities:

```
Crop ├── HAS_PEST ─────────► Pest
     ├── HAS_DISEASE ──────► Disease
     ├── DEFICIENCY ───────► Nutrient
     ├── HAS_SYMPTOM ──────► Symptom
     └── TREATED_BY ───────► Treatment
```

This lets the platform reason over relationships rather than relying on textual similarity alone. Graph reasoning paths are exposed to the frontend through the Intelligence Canvas.

### 👁️ Multimodal Crop Intelligence

Farmers don't always know the technical name of a pest or disease. KrishiOS supports text, voice, and crop-image input, combining image-based crop diagnostics with knowledge retrieval, graph reasoning, and contextual advisory generation — surfaced through a dedicated **Vision Diagnostic Lab**.

### 🎙️ Voice & Vernacular Interaction

The farmer interface is built around accessibility rather than assuming everyone wants to type a technical question: voice interaction, a multilingual UI, a Telugu mode, audio advisory playback with playback-rate controls, export controls, and crop-aware conversational context.

```
Speak naturally → Understand intent → Retrieve agricultural evidence → Reason over context → Receive actionable guidance
```

### 🌦️ Live Agricultural Context

The intelligence workspace combines advisory knowledge with current context — live weather, farm context, telemetry, a spray-window countdown, and contextual advisory actions — moving from *"here is a generic article about your crop"* to *"given this farmer, this crop, this location and this situation, here is the relevant guidance."*

### 🛡️ Responsible AI & Guardrails

Grounded knowledge retrieval, structured agent contracts, response validation, confidence indicators, evidence/provenance surfaces, human-in-the-loop escalation, officer review workflows, and safe handling of insufficient evidence. When the system lacks enough verified information, it's designed to avoid presenting an unsupported recommendation as fact.

### 👨‍🌾 Farmer Intelligence Workspace

- **Farmer Dashboard** — personalized profile, farm snapshot, crop context, live weather
- **Ask KrishiOS** — conversational AI over text, voice, and crop-image upload
- **Rich AI Responses** — structured advisory, confidence indicator, evidence/provenance surfaces, audio playback, action controls

### 👨‍💼 Human-in-the-Loop Officer Workflow

High-impact or uncertain cases route into an officer workflow rather than being resolved autonomously:

```
AI Advisory → Confidence / Guardrail Check
   ├── Sufficient confidence → Farmer response
   └── Requires review → Officer Review Queue → Inspect provenance → Modify / Approve → Update alert status
```

**AI assists agricultural decision-making; humans remain in the loop when intervention is consequential.**

### 📄 Knowledge Document Management

Document upload, metadata management, ingestion status, chunking, embeddings, vector indexing, semantic document search, document deletion, and index version management — so the advisory system evolves by adding verified knowledge rather than rewriting application logic.

### 🎨 Intelligence Canvas

Makes the system's reasoning visible: GraphRAG reasoning chain visualization, a telemetry matrix, a provenance explorer, the vision diagnostic lab, an AI confidence badge, stage-by-stage thinking indicators, and an advisory action toolbar. Instead of just *"here is your answer,"* KrishiOS shows *"here is the context, evidence, reasoning path, confidence and action."*

### 🧪 Tested & Verified

- **25** test files passed, **49** tests passed
- Production frontend build successfully transformed **1,738 modules**

**Verified Golden Journey:**

```
Farmer Login → Personalized Dashboard → Live Weather → Telugu Mode → Voice/Text Question
   → Crop Image → Vision + RAG + GraphRAG + Agromet Context → Rich AI Advisory
   → Confidence + Evidence → Multilingual Audio → Officer Escalation → Officer Review
   → Approve / Modify → Alert Status Update
```

---

## 🗄️ Data Architecture

Different agricultural data has different access patterns, so KrishiOS uses purpose-built storage per layer:

| Layer | Technology | Purpose |
|---|---|---|
| Relational | PostgreSQL | Farmer, crop, field, document and application data |
| Vector | Qdrant | Semantic agricultural retrieval |
| Graph | Neo4j | Agricultural relationships and GraphRAG |
| Cache | Redis | Fast state/cache operations |
| Application | FastAPI | API and orchestration services |
| Frontend | React + TypeScript | Farmer and officer experience |

The complete development environment is containerized with Docker Compose.

---

## 🧩 Backend Structure

```
backend/
├── agents/
│   ├── contracts/
│   ├── execution/
│   ├── orchestrator/
│   ├── providers/
│   ├── runtime/
│   ├── tools/
│   └── workflows/
├── retrieval/
│   ├── api/
│   ├── deployment/
│   ├── indexing/
│   ├── providers/
│   └── retrieval/
├── knowledge/
├── graph/
├── models/
├── api/
└── config/
```

This keeps clear platform boundaries so the agricultural intelligence layer can evolve without turning the backend into a monolithic chatbot implementation.

---
## ⚙️ Technology Stack

**Frontend:** React 19 · TypeScript · Vite · React Router · TanStack Query · Tailwind CSS · i18next · lucide-react · Vitest

**Backend:** Python · FastAPI · Pydantic v2 · SQLAlchemy 2 · Alembic · Pytest · Ruff · Loguru

**AI / Retrieval:** Gemini · Sentence Transformers · Qdrant · GraphRAG · Neo4j · Agent orchestration runtime · Grounded response validation

**Infrastructure:** Docker · Docker Compose · PostgreSQL · Redis

---

## 🚀 Running KrishiOS Locally

### Prerequisites

- Docker Desktop
- Git
- Node.js
- Python
- Gemini API key

### Clone

```bash
git clone https://github.com/Vsd1208/KrishiOS.git
cd KrishiOS
```

### Configure environment

Create the required environment files using the project's environment templates.

Example frontend configuration:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_DEFAULT_LANGUAGE=en
```

Configure the backend environment with the required database, Redis, Qdrant, Neo4j, and Gemini settings.

### Start the platform

```bash
docker compose up -d --build
```

Check the running services:

```bash
docker compose ps
```

**Expected core services:**

| Service | Port |
|---|---|
| Backend | 8000 |
| Frontend | 80 |
| PostgreSQL | 5432 |
| Redis | 6379 |
| Qdrant | 6333 / 6334 |
| Neo4j | 7474 / 7687 |

---

## 🧭 Buildathon Demo Flow

1. **Farmer** — Login as a farmer and open the personalized dashboard.
2. **Ask** — Ask a natural agricultural question, e.g. *"What pests affect my chilli crop?"*
3. **Context** — KrishiOS identifies the crop and retrieves relevant agricultural evidence.
4. **Intelligence** — Open the Intelligence Canvas: retrieval, GraphRAG, confidence, provenance, contextual signals.
5. **Multimodal** — Upload a crop image and combine it with the farmer's question.
6. **Advisory** — View the generated, grounded advisory.
7. **Explainability** — Open the evidence/provenance interface.
8. **Human Oversight** — Escalate a high-impact case to the officer workflow.
9. **Officer** — Review the advisory, inspect context, modify/approve, and update case status.

---

## 🏆 Why KrishiOS Is Different

Most agricultural AI systems ask: *"Can an LLM answer a farmer's question?"*

KrishiOS asks: **"Can an AI system turn fragmented agricultural information into a traceable, contextual, and human-verifiable decision?"**

```
                AGRICULTURAL INTELLIGENCE
                         │
        ┌────────────────┼────────────────┐
        │                │                │
       RAG            GraphRAG        Multimodal
        │                │                │
        └────────────────┼────────────────┘
                         │
                 Agent Orchestration
                         │
              Context + Guardrails
                         │
                  LLM Reasoning
                         │
                 Human Verification
```

The result is not simply a chatbot — it's an agricultural decision-intelligence platform.

---

## 🌱 Current Knowledge Base Coverage

| Crop | Coverage |
|---|---|
| 🌾 Paddy / Rice | Pest, disease and crop-management guidance |
| 🌱 Cotton | Crop health, pest and disease management |
| 🌶️ Chilli | Pest, symptom and general management guidance |

The architecture is crop-extensible: adding a new crop primarily means adding verified knowledge and structured entities, not building a new application.

---

## 🔭 Roadmap

The current buildathon implementation establishes the core platform. Planned expansion includes:

- Additional Indian crops
- Additional regional languages and dialects
- Broader government-DPI integrations
- Richer soil-health workflows
- Expanded market intelligence
- Additional agricultural vision models
- District-level policy intelligence
- Deeper offline / low-connectivity capabilities
- Broader farmer and officer workflows

The architecture is intentionally designed so these capabilities can be added as services and knowledge sources rather than requiring separate applications.

---

## 🧠 Engineering Principles

1. **Evidence before generation** — retrieve trusted agricultural knowledge before asking the LLM to reason.
2. **Context before recommendation** — crop, geography, season, and farmer context matter.
3. **Explainability before trust** — a recommendation should be inspectable.
4. **Human oversight before high-impact action** — AI should assist experts, not silently replace them.
5. **Platform before features** — new agricultural capabilities should plug into a shared intelligence substrate.

---

## 👥 About

KrishiOS was built as an exploration of what an AI-native agricultural operating system could look like for India. The goal isn't to add an LLM to agriculture — it's to build the intelligence infrastructure around the LLM:

```
data → retrieval → graph → agents → reasoning → validation → action → human oversight
```

---

### ⭐ If this project interests you

Give the [repository](https://github.com/Vsd1208/KrishiOS) a star and follow the development of KrishiOS.

**Built with ❤️ for Indian Agriculture**
