/**
 * api.ts — central reference for the backend API URL.
 *
 * In local dev (no env var set), defaults to http://localhost:8000.
 * In production (Vercel), set NEXT_PUBLIC_API_URL to the Render backend URL.
 */
export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  