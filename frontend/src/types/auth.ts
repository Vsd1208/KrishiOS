/**
 * Authentication types matching the backend's Sprint 5 auth system.
 *
 * See: backend/app/schemas/auth.py
 *      backend/app/models/user.py
 *      backend/app/auth/security.py
 */

// ── User Roles ───────────────────────────────────────────────────────────────

export type UserRole = 'farmer' | 'officer' | 'agronomist' | 'admin' | 'system';

// ── Request Payloads ─────────────────────────────────────────────────────────

/** Login request — at least one of phone or email must be provided. */
export interface LoginRequest {
  phone?: string;
  email?: string;
  password: string;
}

/** Refresh token request. */
export interface RefreshRequest {
  refresh_token: string;
}

// ── Response Payloads ────────────────────────────────────────────────────────

/** Token pair returned on successful login or refresh. */
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'Bearer';
  expires_in: number;
}

// ── JWT Payload (decoded access token) ───────────────────────────────────────

/** Shape of the decoded JWT access token payload. */
export interface JwtPayload {
  sub: string; // user UUID
  role: UserRole;
  permissions: string[];
  jti: string;
  iat: number;
  exp: number;
}

// ── Client-side Auth State ───────────────────────────────────────────────────

/** Authenticated user representation in the frontend. */
export interface AuthUser {
  uuid: string;
  role: UserRole;
  permissions: string[];
}
