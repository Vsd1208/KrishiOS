# Frontend Sprint 1 Walkthrough — KrishiOS Frontend Foundation

## Overview
We have constructed the production-grade frontend foundation for **KrishiOS** (AI Decision Intelligence Platform for Indian Agriculture). The frontend is built on **React 19 + TypeScript + Vite 6 + Tailwind CSS + TanStack Query v5 + React Router v7 + i18next**, establishing a clean architecture for both the **Farmer Portal** and the **Agricultural Officer Console**.

---

## 1. Technology Stack & Directory Architecture

```
frontend/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.ts
├── postcss.config.js
├── eslint.config.js
├── .env.example
├── .prettierrc
│
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── vite-env.d.ts
    │
    ├── app/
    │   ├── config.ts              # Centralized environment configuration
    │   ├── providers.tsx           # Composed providers (React Query, Auth, Toast)
    │   └── router.tsx             # React Router tree with lazy-loaded route splitting
    │
    ├── components/
    │   ├── ui/                    # Design System Primitives
    │   │   ├── Button.tsx         # Variants: primary, secondary, outline, ghost, danger
    │   │   ├── Input.tsx          # Accessible input with label, error, helperText, adornments
    │   │   ├── Card.tsx           # Surface container with CardHeader/Title/Description/Content/Footer
    │   │   ├── Badge.tsx          # Variants: default, success, warning, danger, info, primary
    │   │   ├── Spinner.tsx        # Sizes: sm, md, lg, xl with sr-only labels
    │   │   ├── Skeleton.tsx       # Content loader with pulse animations
    │   │   ├── Alert.tsx          # Semantic status banner with dismiss support
    │   │   ├── Modal.tsx          # Accessible portal dialog with focus trap & Esc listener
    │   │   └── index.ts           # Barrel export
    │   │
    │   ├── layout/                # Shell Layouts
    │   │   ├── Header.tsx         # App branding, language switcher, user status, logout
    │   │   ├── FarmerShell.tsx    # Mobile-first shell with bottom navigation tabs
    │   │   └── OfficerShell.tsx   # Desktop-first shell with collapsible sidebar
    │   │
    │   ├── feedback/              # Feedback & States
    │   │   ├── LoadingState.tsx   # Inline & full-page spinner loaders
    │   │   ├── ErrorState.tsx     # Friendly error mapping without exposing raw stack traces
    │   │   ├── EmptyState.tsx     # Clean empty state with icon & action CTA
    │   │   └── Toast.tsx          # Toast notification provider & stacking container
    │   │
    │   └── ai/                    # AI-Specific UI Primitives
    │       ├── ConfidenceBadge.tsx    # HIGH (green), MEDIUM (amber), LOW (red) with icons
    │       ├── FreshnessIndicator.tsx # FRESH (<1h), RECENT (<24h), STALE (<72h), EXPIRED (>72h)
    │       ├── RiskBadge.tsx          # LOW, MEDIUM, HIGH, CRITICAL with accessible labels
    │       ├── CitationCard.tsx       # Provenance, authority, relevance scores, and snippets
    │       ├── EvidenceCard.tsx       # Collapsible telemetry, citations, graph paths, active rules
    │       ├── AIMessage.tsx          # Distinct AI container with confidence & citations footer
    │       ├── ThinkingIndicator.tsx  # Animated analyzer loader with contextual messages
    │       ├── SourceReference.tsx    # Compact inline citation tag
    │       └── index.ts               # Barrel export
    │
    ├── features/
    │   └── auth/
    │       ├── AuthContext.tsx        # JWT decoding, memory access token, refresh token handling
    │       ├── LoginPage.tsx          # Phone/Email login with validation and role redirection
    │       ├── ProtectedRoute.tsx     # Redirects unauthenticated users to /login
    │       └── RoleRoute.tsx          # Enforces role permissions (403 for unauthorized roles)
    │
    ├── services/
    │   └── api/
    │       ├── client.ts              # Centralized fetch client with 401 refresh queue & error parsing
    │       ├── auth.ts                # Auth API endpoints (login, refresh, logout)
    │       └── health.ts              # Health & readiness checks
    │
    ├── hooks/
    │   ├── useAuth.ts                 # Auth hook
    │   └── useToast.ts                # Toast notifications hook
    │
    ├── types/
    │   ├── api.ts                     # ApiError, ApiErrorResponse, PaginationParams
    │   ├── auth.ts                    # UserRole, LoginRequest, TokenResponse, AuthUser
    │   ├── domain.ts                  # Farmer, Officer, Field, Crop, FieldCrop, SoilSample
    │   └── proactive.ts               # RiskSeverity, AlertStatus, ProactiveDecision, EvidencePackage
    │
    ├── i18n/
    │   ├── index.ts                   # i18next configuration with browser language detection
    │   └── locales/
    │       ├── en/common.json         # English translations
    │       ├── te/common.json         # Telugu translations
    │       └── hi/common.json         # Hindi translations
    │
    └── pages/
        ├── farmer/FarmerDashboard.tsx # Placeholder Farmer Dashboard
        └── officer/OfficerDashboard.tsx # Placeholder Officer Console
```

---

## 2. Authentication & Role-Based Routing Architecture

- **Token Lifecycle**:
  - `access_token` (15-min TTL) is stored strictly in memory via closures in `client.ts` and `AuthContext.tsx`.
  - `refresh_token` is stored in `localStorage` and rotated upon use.
  - On application mount or 401 Unauthorized response, `client.ts` triggers a queued refresh request (`POST /api/v1/auth/refresh`), preventing race conditions.
  - User identity (`uuid`, `role`, `permissions`) is decoded client-side using `atob()` on the stateless JWT payload.
- **Routing**:
  - `/login`: Public login form.
  - `/farmer/*`: Guarded by `<ProtectedRoute />` and `<RoleRoute allowedRoles={['farmer']} />` rendering `<FarmerShell />`.
  - `/officer/*`: Guarded by `<ProtectedRoute />` and `<RoleRoute allowedRoles={['officer', 'agronomist', 'admin']} />` rendering `<OfficerShell />`.

---

## 3. Design System & Semantic Design Tokens

- **Palette**: Agricultural Green (`--color-primary-50` to `--color-primary-900`), Neutral Surface (`--color-surface`, `--color-surface-raised`), Borders (`--color-border`), and semantic feedback tokens (`success`, `warning`, `danger`, `info`).
- **Typography Hierarchy**: `display`, `heading`, `subheading`, `body`, `small`, `caption` configured in Tailwind with support for Indian scripts (`Noto Sans Telugu`, `Noto Sans Devanagari`, `Inter`).
- **Accessibility**: All interactive elements include `:focus-visible` styling, ARIA roles (`role="alert"`, `role="status"`, `role="dialog"`), accessible names, and never rely on color alone.

---

## 4. Verification Results

| Check | Command | Result |
|---|---|---|
| **TypeScript Typecheck** | `npm run typecheck` (`tsc --noEmit`) | ✅ **0 errors** |
| **ESLint** | `npm run lint` (`eslint src/`) | ✅ **0 errors** (4 fast-refresh warnings) |
| **Vitest Tests** | `npm run test` (`vitest run`) | ✅ **17/17 tests passed** |
| **Production Build** | `npm run build` (`tsc -b && vite build`) | ✅ **Success** (Chunks: `vendor`, `query`, `i18n`, `FarmerDashboard`, `OfficerDashboard`) |

---

## 5. Verification Matrix for Phase 20 Health Checks

- [x] 1. Frontend starts (`vite`).
- [x] 2. Frontend builds (`tsc -b && vite build` completed in 22.84s).
- [x] 3. TypeScript passes (0 errors).
- [x] 4. Linting passes (0 errors).
- [x] 5. Login page renders at `/login`.
- [x] 6. Authentication communicates with backend endpoints (`/auth/login`, `/auth/refresh`, `/auth/logout`).
- [x] 7. Protected routing redirects unauthenticated users.
- [x] 8. Farmer route exists at `/farmer`.
- [x] 9. Officer route exists at `/officer`.
- [x] 10. Role-based routing enforces permissions.
- [x] 11. Application shells render (`FarmerShell` mobile-first, `OfficerShell` desktop-first).
- [x] 12. Language selector switches between English, Telugu, and Hindi.
- [x] 13. Responsive layouts support mobile, tablet, and desktop.
- [x] 14. Loading, error, and empty states handle async workflows.
- [x] 15. API errors are normalized into `ApiError` with user-friendly messages.
- [x] 16. AI UI primitives render confidence, risk, freshness, citations, and evidence packages.
- [x] 17. No backend files modified; backend test suite remains untouched and intact.
