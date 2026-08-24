# KrishiOS

KrishiOS is an AI decision-intelligence platform for Indian agriculture. It brings farmer and agricultural-officer workflows together with crop, field, soil, knowledge retrieval, vision, voice, live-data, and proactive advisory capabilities.

## What is included

- **Farmer portal** with role-protected routes and a mobile-first shell.
- **Officer console** for officers, agronomists, and administrators.
- **Agricultural domain APIs** for farmers, officers, districts, fields, crops, field crops, and soil samples.
- **Knowledge infrastructure** for document upload, asynchronous ingestion, semantic search, embeddings, reranking, and citations.
- **Decision intelligence** for graph-backed retrieval, crop vision, voice workflows, weather and market data, government schemes, and proactive risk decisions.
- **Authentication** with JWT access and rotating refresh tokens.
- **Multilingual UI foundation** with English, Telugu, and Hindi translations.

## Features in detail

### 1. Two role-specific experiences

KrishiOS serves two connected audiences:

- **Farmers** get a mobile-first experience for field information, crop context, alerts, advisories, and accessible AI-assisted guidance.
- **Agricultural officers, agronomists, and administrators** get a separate console for managing agricultural records, reviewing evidence, and taking action on cases that need professional judgment.

Authentication and role-based route guards keep each experience focused. Access tokens remain in memory, refresh tokens are rotated, and expired sessions are refreshed automatically by the frontend API client.

### 2. Agricultural records and field context

The platform models the information needed to make an advisory useful in practice:

- Farmer and officer profiles
- District reference data
- Fields and field-crop relationships
- Crop catalog data
- Soil samples

This context lets an advisory relate to a farmer, location, crop, growth stage, and soil condition instead of returning a generic answer that could apply anywhere.

### 3. Knowledge ingestion and grounded retrieval

Authorized users can upload PDF, DOCX, text, and image documents. KrishiOS validates the file, detects duplicates using a SHA-256 hash, stores it, and starts ingestion asynchronously. The ingestion pipeline parses and chunks the document, creates embeddings, and indexes the result in Qdrant.

Search uses semantic retrieval, metadata filters, freshness and authority signals, and reranking. Responses can include citations so users and officers can inspect where an answer came from. The intended sources include agricultural schemes, advisories, research, and other trusted domain material.

### 4. Vector search plus knowledge graph reasoning

Qdrant handles similarity search across document chunks. Neo4j represents relationships between entities and concepts. Using both allows KrishiOS to combine:

- **Vector evidence:** passages that are semantically relevant to a question.
- **Graph evidence:** connected entities, relationships, and paths that explain how facts relate.

This is useful for questions where the relationship matters, such as connecting a crop to a disease, a region, a season, a scheme, or a recommended practice.

### 5. Crop vision and voice workflows

The backend exposes vision workflows for crop-image analysis and voice workflows for speech input and output. The design includes validation, file-size and MIME limits, caching, multilingual interaction, and structured results rather than unbounded text.

The repository currently uses mock vision, speech-to-text, and text-to-speech providers by default. Provider interfaces make it possible to connect production services later without changing the farmer and officer workflows.

### 6. Live agricultural intelligence

Live-data adapters provide a common boundary for information that changes over time:

- Weather observations and forecasts
- Market and mandi prices
- Agricultural advisories
- Government schemes

Each provider has caching, rate limits, timeouts, and circuit-breaker settings. The defaults are mock providers, which keeps local development deterministic while preserving the integration points for real services.

### 7. Proactive risk detection

KrishiOS is designed to do more than wait for a farmer to ask a question. External events can trigger rules for:

- Heavy rainfall and drainage risk
- Extreme heat and crop stress
- Disease-favorable microclimates
- Market price movement
- Government scheme eligibility

The proactive pipeline targets relevant farmers and fields, gathers profile and live context, combines vector and graph evidence, evaluates risk, and creates a localized alert when the conditions justify one.

### 8. Evidence, confidence, and human review

Every proactive decision can carry an evidence package containing live telemetry, document citations, graph paths, rule versions, validity periods, and confidence details. Stale external data is penalized rather than silently treated as current.

High-impact or low-confidence decisions are sent to an officer review queue. Officers can inspect the evidence, edit an advisory, approve it, or reject it before delivery. This creates a practical boundary between automated detection and professional agricultural judgment.

### 9. Notification preferences and delivery controls

Farmers can control preferred language, alert categories, minimum severity, delivery channels, and quiet hours. Supported channel abstractions include in-app, SMS, push, and voice notifications.

The notification layer deduplicates repeated events and supports urgent overrides for important alerts. This reduces notification fatigue while preserving high-priority warnings.

### 10. Explainable AI interface

The frontend includes reusable components for confidence, risk severity, freshness, citations, evidence, and AI messages. AI output is presented alongside its supporting information instead of being treated as an unexplained final answer.

## How KrishiOS is different

KrishiOS is not positioned as only a chatbot, a weather app, a crop disease classifier, or a document search tool. Its distinguishing approach is to connect those capabilities around agricultural context and accountable decisions.

| Common approach | KrishiOS approach |
| --- | --- |
| Generic conversational answer | Context-aware guidance linked to the farmer, field, crop, location, and season |
| Single-source retrieval | Hybrid vector retrieval plus knowledge-graph relationships |
| AI answer without provenance | Citations, authority, freshness, graph paths, and confidence information |
| Reactive chat only | Event-driven proactive detection and targeted alerts |
| Fully automatic high-impact advice | Human-in-the-loop officer review for uncertain or consequential decisions |
| One-size-fits-all notifications | Language, severity, category, channel, and quiet-hour preferences |
| Separate tools for farmers and officials | One system with role-specific farmer and officer workflows |
| Hard-coded external integrations | Provider interfaces with caching, rate limits, timeouts, circuit breakers, and local mocks |
| Broad AI claims without operational controls | Rule gates, deduplication, stale-data suppression, audit records, and testable workflows |

The practical benefit is a decision trail: **what changed, which farmers or fields were affected, which rule matched, what evidence was collected, how confident the system was, who approved the result, and how it was delivered**.

## Typical decision flow

```text
External event or farmer question
	|
	v
Context: farmer + field + crop + location + season
	|
	v
Rules and retrieval: structured checks + vector evidence + graph relationships
	|
	v
Risk assessment and evidence package
	|
	+--> High confidence and low impact: localized notification
	|
	+--> High impact or uncertain: officer review, edit, approve, or reject
```

## Current implementation status

The repository contains the platform foundation, domain services, API routes, frontend shells, intelligence abstractions, migrations, and automated tests. Some integrations intentionally default to deterministic mock providers, including vision, voice, weather, market, advisory, and scheme data. Replace those providers and production secrets before using KrishiOS with live users or operational decisions.

## Architecture

| Layer | Technology |
| --- | --- |
| Frontend | React 19, TypeScript, Vite 6, Tailwind CSS, TanStack Query, React Router, i18next |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic Settings |
| Relational data | PostgreSQL 16 |
| Cache and event support | Redis 7 |
| Vector search | Qdrant 1.9 |
| Knowledge graph | Neo4j 5 with APOC |

## Prerequisites

For the recommended containerized workflow, install:

- Docker Desktop with Docker Compose
- Git

For split local development, also install:

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Node.js and npm

## Quick start with Docker

From the repository root:

```sh
cp backend/.env.example backend/.env
docker compose up --build
```

On Windows PowerShell, use this instead of `cp`:

```powershell
Copy-Item backend/.env.example backend/.env
docker compose up --build
```

The backend is available at `http://localhost:8000`. The Compose stack also starts PostgreSQL, Redis, Qdrant, and Neo4j. Database migrations run automatically when the backend container starts.

Useful service URLs:

- API root: `http://localhost:8000/api/v1/`
- Health: `http://localhost:8000/api/v1/health`
- Readiness: `http://localhost:8000/api/v1/ready`
- OpenAPI UI: `http://localhost:8000/docs`
- Qdrant: `http://localhost:6333/dashboard`
- Neo4j Browser: `http://localhost:7474`

Stop the stack with:

```sh
docker compose down
```

Add `-v` only when you intentionally want to remove the persisted PostgreSQL, Redis, Qdrant, Neo4j, and document volumes.

## Local development

### Backend

```sh
cd backend
uv sync --all-groups
cp .env.example .env
uv run alembic upgrade head
uv run fastapi dev app/main.py
```

The backend expects PostgreSQL, Redis, Qdrant, and Neo4j to be reachable. You can start those dependencies with `docker compose up postgres redis qdrant neo4j`, then run the backend locally. When running outside Docker, the default host values in `.env.example` are `localhost`.

Run backend checks:

```sh
cd backend
uv run pytest
uv run ruff check app tests
uv run ruff format --check app tests
```

### Frontend

```sh
cd frontend
npm install
npm run dev
```

Vite serves the frontend at `http://localhost:5173`. The frontend defaults to `/api/v1`; configure `VITE_API_BASE_URL` in `frontend/.env.local` when the API is hosted elsewhere:

```dotenv
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_DEFAULT_LANGUAGE=en
```

Run frontend checks:

```sh
cd frontend
npm run typecheck
npm run lint
npm test
npm run build
```

## API overview

The versioned API is mounted under `/api/v1`. FastAPI generates interactive documentation at `/docs` and the OpenAPI schema at `/openapi.json`.

Main route groups include:

| Group | Examples |
| --- | --- |
| Authentication | `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout` |
| Core domain | `/farmers`, `/officers`, `/districts`, `/fields`, `/crops`, `/field-crops`, `/soil-samples` |
| Knowledge | `POST /documents/upload`, `GET /documents`, `POST /documents/search` |
| Intelligence | Retrieval, agents, graph, vision, voice, live data, and proactive decision routes |

See [docs/API.md](docs/API.md) for API documentation and [docs/PRD.md](docs/PRD.md) for product requirements.

## Repository layout

```text
backend/     FastAPI application, migrations, and Python tests
docs/        Product, API, database, roadmap, and AI documentation
frontend/    React application, UI components, features, and frontend tests
docker-compose.yml
```

## Configuration and security

`backend/.env.example` contains local development defaults. Do not use its default passwords or JWT secret in a deployed environment. Keep real environment files and credentials out of version control, use strong generated secrets, and set `DEBUG=false` outside local development.

The Compose file currently uses `backend/.env.example` as the backend container environment file and overrides service hosts for the Compose network. Review that setup before deploying beyond local development.

## License

This project is licensed under the terms in [LICENSE](LICENSE).
