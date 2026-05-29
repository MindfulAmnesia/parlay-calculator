/**
 * api.ts — central reference for the backend API URL and auth helpers.
 *
 * In local dev (no env var set), defaults to http://localhost:8000.
 * In production (Vercel), set NEXT_PUBLIC_API_URL to the Render backend URL.
 */
export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const TOKEN_KEY = "parlay-calculator:token";

/**
 * Read the stored session token (browser only). Returns null if absent
 * or if storage is unavailable.
 */
export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

/**
 * Build request headers, attaching the Bearer token when present.
 * Pass includeJson=true for requests that send a JSON body.
 */
export function authHeaders(includeJson = false): Record<string, string> {
  const headers: Record<string, string> = {};
  if (includeJson) {
    headers["Content-Type"] = "application/json";
  }
  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}
