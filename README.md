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

![KrishiOS Architecture Diagram](./docs/architecture-diagram.svg)

The architecture deliberately separates the orchestration runtime, specialist agents, AI services, data layer, and integration layer so individual components can evolve independently.

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
## Architecture Diagram
<svg viewBox="0 0 900 1500" xmlns="http://www.w3.org/2000/svg" font-family="Helvetica, Arial, sans-serif" xmlns:c2pa="http://c2pa.org/manifest"><metadata><c2pa:manifest>AAAWgmp1bWIAAAAeanVtZGMycGEAEQAQgAAAqgA4m3EDYzJwYQAAABZcanVtYgAAAEdqdW1kYzJtYQARABCAAACqADibcQN1cm46YzJwYTo3YmM2NGY4MC04NjljLTQ4ZTktODUxZi00OTkzM2EzNTkzYjUAAAADl2p1bWIAAAApanVtZGMyYXMAEQAQgAAAqgA4m3EDYzJwYS5hc3NlcnRpb25zAAAAALxqdW1iAAAARGp1bWRjYm9yABEAEIAAAKoAOJtxE2MycGEuaW5ncmVkaWVudC52MwAAAAAYYzJzaGnebqHJNy3uu3Hzwsy5Fk0AAABwY2JvcqNpZGM6Zm9ybWF0bWltYWdlL3N2Zyt4bWxqaW5zdGFuY2VJRHgseG1wOmlpZDowZDAyZDk5MS0yOWRlLTQ5MzItOTFiMC0yMjBkMDZhODE1YmFscmVsYXRpb25zaGlwaHBhcmVudE9mAAAB4mp1bWIAAABBanVtZGNib3IAEQAQgAAAqgA4m3ETYzJwYS5hY3Rpb25zLnYyAAAAABhjMnNoYWZuXcr7S5/+Sksd2izJwwAAAZljYm9yomdhY3Rpb25zgqJmYWN0aW9ua2MycGEub3BlbmVkanBhcmFtZXRlcnOha2luZ3JlZGllbnRzgaJjdXJseC1zZWxmI2p1bWJmPWMycGEuYXNzZXJ0aW9ucy9jMnBhLmluZ3JlZGllbnQudjNkaGFzaFggiObRcOr6R4kJDl/gqgNINqD5KY6HgnJC/LRDHdIS7GqkZmFjdGlvbngdY29tLmFudGhyb3BpYy5jbGF1ZGUucHJvdmlkZWRqcGFyYW1ldGVyc6F4H2NvbS5hbnRocm9waWMub3JpZ2luLWNvbmZpZGVuY2VndW5rbm93bmtkZXNjcmlwdGlvbnhmQ2xhdWRlIHByb3ZpZGVkIHRoaXMgZmlsZSBhdCB0aGUgcmVxdWVzdCBvZiBhIHVzZXIgYW5kIG1heSBoYXZlIGNyZWF0ZWQgb3IgbW9kaWZpZWQgdGhlIGZpbGUgY29udGVudHMubXNvZnR3YXJlQWdlbnShZG5hbWVmQ2xhdWRlcmFsbEFjdGlvbnNJbmNsdWRlZPUAAADIanVtYgAAAEBqdW1kY2JvcgARABCAAACqADibcRNjMnBhLmhhc2guZGF0YQAAAAAYYzJzaNIeAxsTRGMp83hUOSGiGbcAAACAY2JvcqVjYWxnZnNoYTI1NmNwYWRNAAAAAAAAAAAAAAAAAGRoYXNoWCB9KK3Xvj8NOkDQiU5RQD51k2sU/IFLm+aHkfA7ZiurAWRuYW1lbmp1bWJmIG1hbmlmZXN0amV4Y2x1c2lvbnOBomVzdGFydBipZmxlbmd0aBkeBAAAAj5qdW1iAAAAJ2p1bWRjMmNsABEAEIAAAKoAOJtxA2MycGEuY2xhaW0udjIAAAACD2Nib3KlY2FsZ2ZzaGEyNTZpc2lnbmF0dXJleE1zZWxmI2p1bWJmPS9jMnBhL3VybjpjMnBhOjdiYzY0ZjgwLTg2OWMtNDhlOS04NTFmLTQ5OTMzYTM1OTNiNS9jMnBhLnNpZ25hdHVyZWppbnN0YW5jZUlEeCx4bXA6aWlkOjQ2NDhlZDhhLTJiMjctNDA0ZS04ZTY4LTAxNWJhYjI4YzNjNHJjcmVhdGVkX2Fzc2VydGlvbnODomN1cmx4LXNlbGYjanVtYmY9YzJwYS5hc3NlcnRpb25zL2MycGEuaW5ncmVkaWVudC52M2RoYXNoWCCI5tFw6vpHiQkOX+CqA0g2oPkpjoeCckL8tEMd0hLsaqJjdXJseCpzZWxmI2p1bWJmPWMycGEuYXNzZXJ0aW9ucy9jMnBhLmFjdGlvbnMudjJkaGFzaFgg1l9XV2ENa0SXJcLVoMOtbnO3VJ+d6FANFXZv8Wi+vCqiY3VybHgpc2VsZiNqdW1iZj1jMnBhLmFzc2VydGlvbnMvYzJwYS5oYXNoLmRhdGFkaGFzaFgg+LOnQPCgQTI2hiWgSUdy0dnB1Ox8qDkxxqvrlZjkwpB0Y2xhaW1fZ2VuZXJhdG9yX2luZm+jZG5hbWVvQW50aHJvcGljIEZpbGVzZ3ZlcnNpb25lMS4wLjBrc3BlY1ZlcnNpb25lMi40LjAAABA4anVtYgAAAChqdW1kYzJjcwARABCAAACqADibcQNjMnBhLnNpZ25hdHVyZQAAABAIY2JvctKEWQISogEmGCFZAgowggIGMIIBjaADAgECAhRA5aAK7sI50L64g/oGQgU9Z1UTADAKBggqhkjOPQQDAzBJMRcwFQYDVQQKEw5BbnRocm9waWMsIFBCQzEuMCwGA1UEAxMlQW50aHJvcGljIENvbnRlbnQgQ3JlZGVudGlhbHMgUm9vdCBDQTAeFw0yNjA4MDcxODQzNTZaFw0yODA4MDYxOTQzNTZaMEQxFzAVBgNVBAoTDkFudGhyb3BpYywgUEJDMSkwJwYDVQQDEyBBbnRocm9waWMgQ2xhdWRlIENvbnRlbnQgU2lnbmluZzBZMBMGByqGSM49AgEGCCqGSM49AwEHA0IABJh6CmvLUBgFFNU0vUKlOVtE6djd17L5SuwX0LemFisBM3dkd/3cyjxFA3Qo5S46fX0/ihY0VZ7mfb9KF703t5OjWDBWMA4GA1UdDwEB/wQEAwIHgDAVBgNVHSUEDjAMBgorBgEEAYPoXgIBMAwGA1UdEwEB/wQCMAAwHwYDVR0jBBgwFoAUzlHiBIFOZFsj+OPEz5o+nMHXXMIwCgYIKoZIzj0EAwMDZwAwZAIwMXMdFJ4BetLLVY7ORuE9noqbbAZOZn/aArXyTwFAZfKrPzxF2vPoJNf1+UCdg1XGAjBwX1zd9WGqYkqmL5SFqw1QySjr1zJfpJM9+1rdDwSPLMOPOjKuiXjoU/pUUeG9RwmhY3BhZFkNngAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAPZYQO/2tr/QnPoBm310Bfct1GbDwoyJPOQxcSFccTNlenL4Cg3sjZI+Y7OtMzbJGDQFU3JpcFdCXEKfUB+NWWXMCtw=</c2pa:manifest></metadata>
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#4b5563"/>
    </marker>
    <marker id="arrowGreen" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#15803d"/>
    </marker>
  </defs>

  <rect width="900" height="1500" fill="#fafaf9"/>

  <!-- Title -->
  <text x="450" y="42" text-anchor="middle" font-size="24" font-weight="700" fill="#1c1917">KrishiOS — System Architecture</text>
  <text x="450" y="66" text-anchor="middle" font-size="13" fill="#78716c">Farmer question → grounded, evidence-backed agricultural decision</text>

  <!-- Farmer / Officer -->
  <rect x="300" y="95" width="300" height="60" rx="10" fill="#eef2ff" stroke="#6366f1" stroke-width="1.5"/>
  <text x="450" y="120" text-anchor="middle" font-size="14" font-weight="600" fill="#3730a3">Farmer / Officer</text>
  <text x="450" y="140" text-anchor="middle" font-size="12" fill="#4338ca">Text · Voice · Image</text>
  <line x1="450" y1="155" x2="450" y2="185" stroke="#4b5563" stroke-width="1.5" marker-end="url(#arrow)"/>

  <!-- API / Auth -->
  <rect x="330" y="188" width="240" height="52" rx="10" fill="#ecfdf5" stroke="#10b981" stroke-width="1.5"/>
  <text x="450" y="219" text-anchor="middle" font-size="14" font-weight="600" fill="#065f46">API / Auth  (FastAPI)</text>
  <line x1="450" y1="240" x2="450" y2="270" stroke="#4b5563" stroke-width="1.5" marker-end="url(#arrow)"/>

  <!-- Agent Orchestrator -->
  <rect x="260" y="273" width="380" height="72" rx="10" fill="#f5f3ff" stroke="#8b5cf6" stroke-width="1.5"/>
  <text x="450" y="300" text-anchor="middle" font-size="15" font-weight="700" fill="#5b21b6">Agent Orchestrator</text>
  <text x="450" y="320" text-anchor="middle" font-size="12" fill="#6d28d9">Plan → Act → Observe → Respond</text>
  <text x="450" y="336" text-anchor="middle" font-size="10.5" fill="#7c3aed">bounded execution · contracts · timeouts · escalation</text>

  <!-- fan out lines -->
  <line x1="450" y1="345" x2="450" y2="365" stroke="#4b5563" stroke-width="1.5"/>
  <line x1="200" y1="365" x2="700" y2="365" stroke="#4b5563" stroke-width="1.5"/>
  <line x1="200" y1="365" x2="200" y2="390" stroke="#4b5563" stroke-width="1.5" marker-end="url(#arrow)"/>
  <line x1="450" y1="365" x2="450" y2="390" stroke="#4b5563" stroke-width="1.5" marker-end="url(#arrow)"/>
  <line x1="700" y1="365" x2="700" y2="390" stroke="#4b5563" stroke-width="1.5" marker-end="url(#arrow)"/>

  <!-- Three agents -->
  <rect x="110" y="393" width="180" height="58" rx="9" fill="#fff7ed" stroke="#f97316" stroke-width="1.5"/>
  <text x="200" y="427" text-anchor="middle" font-size="13" font-weight="600" fill="#9a3412">Advisory Agent</text>

  <rect x="360" y="393" width="180" height="58" rx="9" fill="#fff7ed" stroke="#f97316" stroke-width="1.5"/>
  <text x="450" y="427" text-anchor="middle" font-size="13" font-weight="600" fill="#9a3412">Vision Agent</text>

  <rect x="610" y="393" width="180" height="58" rx="9" fill="#fff7ed" stroke="#f97316" stroke-width="1.5"/>
  <text x="700" y="427" text-anchor="middle" font-size="13" font-weight="600" fill="#9a3412">Weather Agent</text>

  <!-- Advisory agent goes down to Intelligence layer -->
  <line x1="200" y1="451" x2="200" y2="480" stroke="#4b5563" stroke-width="1.5"/>
  <line x1="200" y1="480" x2="450" y2="480" stroke="#4b5563" stroke-width="1.5" marker-end="url(#arrow)"/>

  <!-- Agricultural Intelligence layer -->
  <rect x="150" y="483" width="600" height="120" rx="10" fill="#eff6ff" stroke="#3b82f6" stroke-width="1.5"/>
  <text x="450" y="508" text-anchor="middle" font-size="15" font-weight="700" fill="#1e3a8a">Agricultural Intelligence Layer</text>

  <rect x="175" y="522" width="165" height="62" rx="8" fill="#ffffff" stroke="#60a5fa" stroke-width="1.2"/>
  <text x="257" y="546" text-anchor="middle" font-size="12" font-weight="600" fill="#1e40af">RAG</text>
  <text x="257" y="562" text-anchor="middle" font-size="10" fill="#1e40af">Qdrant vector search</text>
  <text x="257" y="576" text-anchor="middle" font-size="10" fill="#1e40af">blue-green indexing</text>

  <rect x="368" y="522" width="165" height="62" rx="8" fill="#ffffff" stroke="#60a5fa" stroke-width="1.2"/>
  <text x="450" y="546" text-anchor="middle" font-size="12" font-weight="600" fill="#1e40af">GraphRAG</text>
  <text x="450" y="562" text-anchor="middle" font-size="10" fill="#1e40af">Neo4j knowledge graph</text>
  <text x="450" y="576" text-anchor="middle" font-size="10" fill="#1e40af">crop / pest / treatment</text>

  <rect x="561" y="522" width="165" height="62" rx="8" fill="#ffffff" stroke="#60a5fa" stroke-width="1.2"/>
  <text x="643" y="546" text-anchor="middle" font-size="12" font-weight="600" fill="#1e40af">Verified Context</text>
  <text x="643" y="562" text-anchor="middle" font-size="10" fill="#1e40af">ICAR · TNAU · IIRR</text>
  <text x="643" y="576" text-anchor="middle" font-size="10" fill="#1e40af">retrieval evaluation</text>

  <line x1="450" y1="603" x2="450" y2="628" stroke="#4b5563" stroke-width="1.5" marker-end="url(#arrow)"/>

  <!-- LLM Reasoning -->
  <rect x="330" y="631" width="240" height="55" rx="10" fill="#f5f3ff" stroke="#8b5cf6" stroke-width="1.5"/>
  <text x="450" y="655" text-anchor="middle" font-size="14" font-weight="600" fill="#5b21b6">LLM Reasoning</text>
  <text x="450" y="674" text-anchor="middle" font-size="11" fill="#6d28d9">Gemini</text>
  <line x1="450" y1="686" x2="450" y2="712" stroke="#4b5563" stroke-width="1.5" marker-end="url(#arrow)"/>

  <!-- Validated Farmer Advisory -->
  <rect x="200" y="715" width="500" height="90" rx="10" fill="#ecfdf5" stroke="#10b981" stroke-width="1.5"/>
  <text x="450" y="742" text-anchor="middle" font-size="15" font-weight="700" fill="#065f46">Validated Farmer Advisory</text>
  <text x="450" y="763" text-anchor="middle" font-size="11.5" fill="#047857">Evidence · Confidence · Provenance</text>
  <text x="450" y="781" text-anchor="middle" font-size="11.5" fill="#047857">Actions · Safety · Escalation</text>

  <line x1="450" y1="805" x2="450" y2="830" stroke="#4b5563" stroke-width="1.5" marker-end="url(#arrow)"/>

  <!-- Human Expert Loop -->
  <rect x="300" y="833" width="300" height="62" rx="10" fill="#fef2f2" stroke="#ef4444" stroke-width="1.5"/>
  <text x="450" y="860" text-anchor="middle" font-size="14" font-weight="700" fill="#991b1b">Human Expert Loop</text>
  <text x="450" y="879" text-anchor="middle" font-size="11.5" fill="#b91c1c">Officer review · approve / modify</text>

  <!-- Divider -->
  <line x1="60" y1="930" x2="840" y2="930" stroke="#e7e5e4" stroke-width="1"/>

  <!-- Data layer section -->
  <text x="450" y="965" text-anchor="middle" font-size="15" font-weight="700" fill="#1c1917">Data &amp; Storage Layer</text>

  <rect x="70" y="985" width="150" height="70" rx="9" fill="#ffffff" stroke="#a8a29e" stroke-width="1.3"/>
  <text x="145" y="1013" text-anchor="middle" font-size="12" font-weight="600" fill="#292524">PostgreSQL</text>
  <text x="145" y="1032" text-anchor="middle" font-size="10" fill="#57534e">Relational data</text>

  <rect x="240" y="985" width="150" height="70" rx="9" fill="#ffffff" stroke="#a8a29e" stroke-width="1.3"/>
  <text x="315" y="1013" text-anchor="middle" font-size="12" font-weight="600" fill="#292524">Qdrant</text>
  <text x="315" y="1032" text-anchor="middle" font-size="10" fill="#57534e">Vector search</text>

  <rect x="410" y="985" width="150" height="70" rx="9" fill="#ffffff" stroke="#a8a29e" stroke-width="1.3"/>
  <text x="485" y="1013" text-anchor="middle" font-size="12" font-weight="600" fill="#292524">Neo4j</text>
  <text x="485" y="1032" text-anchor="middle" font-size="10" fill="#57534e">Knowledge graph</text>

  <rect x="580" y="985" width="150" height="70" rx="9" fill="#ffffff" stroke="#a8a29e" stroke-width="1.3"/>
  <text x="655" y="1013" text-anchor="middle" font-size="12" font-weight="600" fill="#292524">Redis</text>
  <text x="655" y="1032" text-anchor="middle" font-size="10" fill="#57534e">Cache / state</text>

  <!-- connecting the intelligence layer conceptually to data layer -->
  <line x1="145" y1="985" x2="145" y2="960" stroke="#d6d3d1" stroke-width="1" stroke-dasharray="4 3"/>
  <line x1="315" y1="985" x2="315" y2="960" stroke="#d6d3d1" stroke-width="1" stroke-dasharray="4 3"/>
  <line x1="485" y1="985" x2="485" y2="960" stroke="#d6d3d1" stroke-width="1" stroke-dasharray="4 3"/>
  <line x1="655" y1="985" x2="655" y2="960" stroke="#d6d3d1" stroke-width="1" stroke-dasharray="4 3"/>
  <line x1="145" y1="960" x2="655" y2="960" stroke="#d6d3d1" stroke-width="1" stroke-dasharray="4 3"/>

  <!-- Legend -->
  <text x="450" y="1100" text-anchor="middle" font-size="13" font-weight="700" fill="#1c1917">Legend</text>

  <rect x="90" y="1125" width="18" height="18" rx="4" fill="#eef2ff" stroke="#6366f1"/>
  <text x="115" y="1139" font-size="11.5" fill="#292524">User-facing entry</text>

  <rect x="280" y="1125" width="18" height="18" rx="4" fill="#ecfdf5" stroke="#10b981"/>
  <text x="305" y="1139" font-size="11.5" fill="#292524">API / validated output</text>

  <rect x="470" y="1125" width="18" height="18" rx="4" fill="#f5f3ff" stroke="#8b5cf6"/>
  <text x="495" y="1139" font-size="11.5" fill="#292524">Orchestration / LLM</text>

  <rect x="90" y="1155" width="18" height="18" rx="4" fill="#fff7ed" stroke="#f97316"/>
  <text x="115" y="1169" font-size="11.5" fill="#292524">Specialist agents</text>

  <rect x="280" y="1155" width="18" height="18" rx="4" fill="#eff6ff" stroke="#3b82f6"/>
  <text x="305" y="1169" font-size="11.5" fill="#292524">Knowledge / retrieval</text>

  <rect x="470" y="1155" width="18" height="18" rx="4" fill="#fef2f2" stroke="#ef4444"/>
  <text x="495" y="1169" font-size="11.5" fill="#292524">Human oversight</text>

  <text x="450" y="1220" text-anchor="middle" font-size="10.5" fill="#a8a29e">KrishiOS — AI Operating System for Indian Agriculture</text>
</svg>


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
