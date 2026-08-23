"""RBAC permission constants and role-to-permission mapping.

Design:
  Permissions are typed string constants in the form "resource:action".
  Each role is mapped to an immutable frozenset of permissions.
  The mapping is the single authoritative source of truth for authorization.

  The Agent Runtime uses AuthContext (carrying user uuid + role + permissions)
  to gate tool execution — it never inherits unrestricted user permissions
  automatically; each tool declares the permission it requires.
"""

from __future__ import annotations

_fs = frozenset  # just an alias for clarity

from app.models.user import UserRole


class Permission:
    """Typed permission constants used throughout the authorization system."""

    # ── Farmer domain ─────────────────────────────────────────────────────────
    FARMER_READ_SELF = "farmer:read_self"
    FARMER_READ = "farmer:read"
    FARMER_CREATE = "farmer:create"
    FARMER_UPDATE_SELF = "farmer:update_self"
    FARMER_UPDATE = "farmer:update"
    FARMER_DELETE = "farmer:delete"

    # ── Field / Crop domain ───────────────────────────────────────────────────
    FIELD_READ = "field:read"
    FIELD_CREATE = "field:create"
    FIELD_UPDATE = "field:update"
    FIELD_DELETE = "field:delete"

    # ── Soil sample domain ────────────────────────────────────────────────────
    SOIL_SAMPLE_READ = "soil_sample:read"
    SOIL_SAMPLE_CREATE = "soil_sample:create"
    SOIL_SAMPLE_UPDATE = "soil_sample:update"

    # ── Knowledge / Documents ─────────────────────────────────────────────────
    KNOWLEDGE_SEARCH = "knowledge:search"
    DOCUMENT_READ = "document:read"
    DOCUMENT_UPLOAD = "document:upload"
    DOCUMENT_DELETE = "document:delete"

    # ── Advisory ─────────────────────────────────────────────────────────────
    ADVISORY_READ = "advisory:read"
    ADVISORY_CREATE = "advisory:create"

    # ── Agent Runtime ─────────────────────────────────────────────────────────
    AGENT_EXECUTE = "agent:execute"
    AGENT_MANAGE = "agent:manage"

    # ── User / Identity management ────────────────────────────────────────────
    USER_READ = "user:read"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DEACTIVATE = "user:deactivate"

    # ── System ────────────────────────────────────────────────────────────────
    SYSTEM_ADMIN = "system:admin"

    # ── Graph / Knowledge Graph ───────────────────────────────────────────────
    GRAPH_READ = "graph:read"
    GRAPH_WRITE = "graph:write"
    GRAPH_REVIEW = "graph:review"
    GRAPH_ADMIN = "graph:admin"

    # ── Vision / Crop Intelligence (Sprint 7) ─────────────────────────────────
    VISION_ANALYZE = "vision:analyze"
    VISION_READ_OWN = "vision:read_own"
    VISION_READ_FIELD = "vision:read_field"
    VISION_REVIEW = "vision:review"

    # ── Voice / Multilingual Intelligence (Sprint 8) ──────────────────────────
    VOICE_SUBMIT = "voice:submit"
    VOICE_READ_OWN = "voice:read_own"
    VOICE_DELETE = "voice:delete"

    # ── Live Agricultural Intelligence (Sprint 9) ────────────────────────────
    LIVE_DATA_READ = "live_data:read"
    LIVE_DATA_SYNC = "live_data:sync"
    WEATHER_READ = "weather:read"
    MARKET_READ = "market:read"
    SCHEME_READ = "scheme:read"

    # ── Proactive Intelligence & Notifications (Sprint 10) ───────────────────
    PROACTIVE_EVENT_EMIT = "proactive:event_emit"
    PROACTIVE_DECISION_READ = "proactive:decision_read"
    ALERT_READ = "alert:read"
    ALERT_ACKNOWLEDGE = "alert:acknowledge"
    ALERT_REVIEW = "alert:review"
    PREFERENCE_READ = "preference:read"
    PREFERENCE_UPDATE = "preference:update"


# ---------------------------------------------------------------------------
# Role → permission mapping
# ---------------------------------------------------------------------------

_FARMER_PERMISSIONS: frozenset[str] = frozenset(
    {
        Permission.FARMER_READ_SELF,
        Permission.FARMER_UPDATE_SELF,
        Permission.FIELD_READ,
        Permission.SOIL_SAMPLE_READ,
        Permission.KNOWLEDGE_SEARCH,
        Permission.ADVISORY_READ,
        Permission.AGENT_EXECUTE,
        Permission.GRAPH_READ,
        Permission.VISION_ANALYZE,
        Permission.VISION_READ_OWN,
        Permission.VOICE_SUBMIT,
        Permission.VOICE_READ_OWN,
        Permission.VOICE_DELETE,
        Permission.LIVE_DATA_READ,
        Permission.WEATHER_READ,
        Permission.MARKET_READ,
        Permission.SCHEME_READ,
        Permission.ALERT_READ,
        Permission.ALERT_ACKNOWLEDGE,
        Permission.PREFERENCE_READ,
        Permission.PREFERENCE_UPDATE,
    }
)

_OFFICER_PERMISSIONS: frozenset[str] = frozenset(
    {
        Permission.FARMER_READ,
        Permission.FARMER_CREATE,
        Permission.FARMER_UPDATE,
        Permission.FIELD_READ,
        Permission.FIELD_CREATE,
        Permission.FIELD_UPDATE,
        Permission.SOIL_SAMPLE_READ,
        Permission.SOIL_SAMPLE_CREATE,
        Permission.SOIL_SAMPLE_UPDATE,
        Permission.KNOWLEDGE_SEARCH,
        Permission.DOCUMENT_READ,
        Permission.DOCUMENT_UPLOAD,
        Permission.ADVISORY_READ,
        Permission.ADVISORY_CREATE,
        Permission.AGENT_EXECUTE,
        Permission.GRAPH_READ,
        Permission.GRAPH_REVIEW,
        Permission.VISION_ANALYZE,
        Permission.VISION_READ_OWN,
        Permission.VISION_READ_FIELD,
        Permission.VISION_REVIEW,
        Permission.VOICE_SUBMIT,
        Permission.VOICE_READ_OWN,
        Permission.VOICE_DELETE,
        Permission.LIVE_DATA_READ,
        Permission.LIVE_DATA_SYNC,
        Permission.WEATHER_READ,
        Permission.MARKET_READ,
        Permission.SCHEME_READ,
        Permission.PROACTIVE_EVENT_EMIT,
        Permission.PROACTIVE_DECISION_READ,
        Permission.ALERT_READ,
        Permission.ALERT_REVIEW,
        Permission.PREFERENCE_READ,
    }
)

_AGRONOMIST_PERMISSIONS: frozenset[str] = frozenset(
    {
        Permission.FARMER_READ,
        Permission.FIELD_READ,
        Permission.SOIL_SAMPLE_READ,
        Permission.KNOWLEDGE_SEARCH,
        Permission.DOCUMENT_READ,
        Permission.ADVISORY_READ,
        Permission.ADVISORY_CREATE,
        Permission.AGENT_EXECUTE,
        Permission.GRAPH_READ,
        Permission.GRAPH_WRITE,
        Permission.VISION_ANALYZE,
        Permission.VISION_READ_OWN,
        Permission.VOICE_SUBMIT,
        Permission.VOICE_READ_OWN,
        Permission.VOICE_DELETE,
        Permission.LIVE_DATA_READ,
        Permission.LIVE_DATA_SYNC,
        Permission.WEATHER_READ,
        Permission.MARKET_READ,
        Permission.SCHEME_READ,
        Permission.PROACTIVE_EVENT_EMIT,
        Permission.PROACTIVE_DECISION_READ,
        Permission.ALERT_READ,
        Permission.ALERT_REVIEW,
        Permission.PREFERENCE_READ,
    }
)

_ALL_PERMISSIONS: frozenset[str] = frozenset(
    {v for k, v in vars(Permission).items() if not k.startswith("_")}
)

ROLE_PERMISSIONS: dict[UserRole, frozenset[str]] = {
    UserRole.FARMER: _FARMER_PERMISSIONS,
    UserRole.OFFICER: _OFFICER_PERMISSIONS,
    UserRole.AGRONOMIST: _AGRONOMIST_PERMISSIONS,
    UserRole.ADMIN: _ALL_PERMISSIONS,
    UserRole.SYSTEM: _ALL_PERMISSIONS,
}


def get_permissions_for_role(role: UserRole) -> frozenset[str]:
    """Return the immutable permission set for a given role."""
    return ROLE_PERMISSIONS.get(role, frozenset())
