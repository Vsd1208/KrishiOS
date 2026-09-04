/**
 * API-level TypeScript types.
 *
 * These match the backend's standardized error envelope and pagination conventions.
 * See: backend/app/exceptions/handlers.py for the error format.
 */

// ── Error Responses ──────────────────────────────────────────────────────────

/** Error detail object nested inside every backend error response. */
export interface ApiErrorDetail {
  code: string;
  message: string;
  details?: ValidationErrorItem[];
}

/** Top-level error envelope returned by the backend. */
export interface ApiErrorResponse {
  error: ApiErrorDetail;
}

/** Individual field-level validation error (422 responses). */
export interface ValidationErrorItem {
  loc: (string | number)[];
  msg: string;
  type: string;
}

// ── Client-Side Error ────────────────────────────────────────────────────────

/**
 * Normalized error thrown by the API client.
 *
 * Components should catch this type rather than raw fetch errors.
 */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly details?: ValidationErrorItem[],
  ) {
    super(message);
    this.name = 'ApiError';
  }

  /** True for 401 Unauthorized responses. */
  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  /** True for 403 Forbidden responses. */
  get isForbidden(): boolean {
    return this.status === 403;
  }

  /** True for 404 Not Found responses. */
  get isNotFound(): boolean {
    return this.status === 404;
  }

  /** True for 422 validation errors with field-level details. */
  get isValidation(): boolean {
    return this.status === 422;
  }
}

// ── Pagination ───────────────────────────────────────────────────────────────

/** Query parameters for paginated list endpoints. */
export interface PaginationParams {
  offset?: number;
  limit?: number;
}
/**
 * Response returned by the document upload endpoint.
 *
 * POST /api/v1/documents/upload
 */
export interface DocumentUploadResponse {
  document_id?: number;
  status?: string;
  message?: string;
  [key: string]: unknown;
}