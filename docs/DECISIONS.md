# Architecture Decision Log

Format: **ADR-NNN, title.** Each entry has a status (proposed / accepted / superseded), context, decision and consequences.

## ADR-001: Single repository, `ml/` as a separate uv project
- **Status:** accepted (project brief, decision 1)
- **Decision:** All work lives in KrishiOS. Training and research code goes in `ml/`, which has its own `pyproject.toml`. The backend only loads exported artifacts from `ml/artifacts/`, mounted read-only.
- **Consequences:** Heavy training dependencies stay out of the backend image.

## ADR-002: "AgriFormer-X" name retired
- **Status:** accepted (brief)
- **Decision:** The research is named "KrishiOS Yield Intelligence", and the model is `krishios_yield`.

## ADR-003: Brief overrides the research proposal's scope guardrail
- **Status:** accepted for engineering; **faculty sign-off pending**
- **Context:** The proposal limits scope to one crop and one benchmark, and warns against adding disease diagnosis. The brief expands scope to multi-crop yield, CV, voice, NLU and Govt Connect.
- **Decision:** Follow the brief, and raise the scope change for faculty sign-off before the Phase 6 scope freeze.

## ADR-004: SACHET CAP feed as the preferred automated weather-warning source
- **Status:** proposed (needs your OK to poll)
- **Context:** The IMD APIs need an API key or IP whitelisting. The NDMA SACHET CAP 1.2 RSS feed is public and includes LGD district codes, severity and expiry.
- **Decision:** Build the SACHET adapter first in Phase 5, and add the IMD API adapter once a key is granted.

## ADR-005: No silent fallback to mock providers
- **Status:** proposed (Phase 1)
- **Context:** `LiveDataProviderRegistry` falls back to mocks with only a log warning.
- **Decision:** Resolve providers from config. An unknown name is a startup error. Every response carries the active provider name and version.

## ADR-006: Separate inference container for heavy speech and translation models
- **Status:** proposed (decide in Phase 2 with measurements; heavyweight dependency, needs approval)
- **Context:** IndicConformer needs a NeMo fork. Keeping it out of the backend image protects build time and image size.
