/** Native-fetch transport, safe during SSR import; hooks opt into browser-only calls. */
export function normalizeApiBaseUrl(value: string | undefined): string {
  const url = new URL(value?.trim() || "http://localhost:8000");
  if (!["http:", "https:"].includes(url.protocol) || url.username || url.password || url.search || url.hash) {
    throw new Error("VITE_API_BASE_URL must be an HTTP(S) URL without credentials, query or fragment.");
  }
  return url.toString().replace(/\/+$/, "");
}

export const API_BASE_URL = normalizeApiBaseUrl(import.meta.env?.["VITE_API_BASE_URL"]);

export class ApiError extends Error {
  readonly status: number | null;
  readonly detail: unknown;
  constructor(message: string, status: number | null = null, detail: unknown = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

function errorMessage(status: number, payload: unknown): string {
  if (status >= 500) return status === 503 ? "Backend unavailable." : "Backend request failed.";
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = payload.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      const messages = detail.flatMap((item: unknown) =>
        item && typeof item === "object" && "msg" in item && typeof item.msg === "string" ? [item.msg] : [],
      );
      if (messages.length) return messages.join("; ");
    }
  }
  return `API request failed (HTTP ${status}).`;
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  // Reject ambiguous URLs so endpoint functions always stay under the configured base.
  if (!path.startsWith("/") || path.startsWith("//")) throw new Error("API path must start with one slash.");
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      credentials: options.credentials ?? "omit",
      signal: options.signal ?? AbortSignal.timeout(10_000),
      headers: { Accept: "application/json", ...options.headers },
    });
  } catch (error) {
    if (options.signal?.aborted) throw error;
    throw new ApiError("Backend unavailable. Check the API connection and base URL.");
  }
  if (response.status === 204 && response.ok) return undefined as T;
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new ApiError(response.ok ? "Backend returned invalid JSON." : `API request failed (HTTP ${response.status}).`, response.status);
  }
  if (!response.ok) throw new ApiError(errorMessage(response.status, payload), response.status, payload);
  return payload as T;
}
