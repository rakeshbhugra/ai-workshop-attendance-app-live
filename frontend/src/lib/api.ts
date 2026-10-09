/**
 * The one place that talks to the network.
 *
 * Every path is relative. In dev, Vite proxies /api to the backend; in
 * production FastAPI serves this bundle from the same origin as the API. So the
 * frontend never needs to know a backend URL, there is no VITE_API_URL to get
 * wrong per environment, and cookies are same-origin everywhere.
 */

const BASE = "/api/v1";

/** An error carrying the HTTP status, so callers can branch on 404 vs 409. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }

  /** True when the server rejected the request for a reason the user can fix —
   *  a broken business rule, not a bug. Worth showing verbatim; a 500's message
   *  never is. */
  get isUserFixable(): boolean {
    return this.status === 409 || this.status === 422 || this.status === 400;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    // Send the session cookie. Same-origin everywhere, so this is belt and braces.
    credentials: "include",
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    // The backend returns {"detail": "..."} for both its own errors and
    // FastAPI's validation errors, so there is exactly one shape to unwrap.
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* a non-JSON error body (a proxy timeout, say) — keep the status text */
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    // The key is omitted rather than set to undefined: with
    // `exactOptionalPropertyTypes` those are different types, and RequestInit
    // does not accept an explicit undefined body.
    request<T>(path, {
      method: "POST",
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  delete: (path: string) => request<void>(path, { method: "DELETE" }),
  upload: <T>(path: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    // No Content-Type header: the browser must set it itself so it can include
    // the multipart boundary. Setting it manually is the classic upload bug.
    return request<T>(path, { method: "POST", body: form });
  },
};
