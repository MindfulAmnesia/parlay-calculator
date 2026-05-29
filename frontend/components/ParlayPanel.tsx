"use client";

import Link from "next/link";
import { useState } from "react";
import { API_URL, authHeaders } from "@/lib/api";
import { useAuth } from "@/lib/AuthContext";
import { useParlay } from "@/lib/ParlayContext";
import { impliedToAmerican, parlayProbability } from "@/lib/parlay-math";

function formatPercent(p: number): string {
  return `${(p * 100).toFixed(2)}%`;
}

function formatOdds(odds: number): string {
  return odds > 0 ? `+${odds}` : `${odds}`;
}

interface SaveState {
  status: "idle" | "saving" | "saved" | "error";
  parlayId?: number;
  error?: string;
}

export default function ParlayPanel() {
  const { legs, removeLeg, clear } = useParlay();
  const { user } = useAuth();
  const [saveState, setSaveState] = useState<SaveState>({ status: "idle" });

  if (legs.length === 0) {
    return null;
  }

  const { raw, fair } = parlayProbability(legs);

  async function handleSave() {
    setSaveState({ status: "saving" });

    const body = {
      legs: legs.map((leg) => ({
        description: leg.description,
        american_odds: leg.americanOdds,
        opposite_odds: leg.oppositeOdds ?? null,
      })),
      sport_key: legs[0]?.sportKey ?? null,
      book: legs[0]?.book ?? null,
    };

    try {
      const res = await fetch(`${API_URL}/parlay/save`, {
        method: "POST",
        headers: authHeaders(true),
        body: JSON.stringify(body),
      });
      if (res.status === 401) {
        throw new Error("Your session expired. Please log in again.");
      }
      if (!res.ok) {
        throw new Error(`Backend returned ${res.status}`);
      }
      const data = await res.json();
      setSaveState({ status: "saved", parlayId: data.id });
    } catch (e) {
      setSaveState({
        status: "error",
        error: e instanceof Error ? e.message : String(e),
      });
    }
  }

  function handleClear() {
    clear();
    setSaveState({ status: "idle" });
  }

  return (
    <div className="fixed bottom-4 right-4 w-96 bg-slate-800 border border-slate-700 rounded-lg shadow-2xl p-4 text-slate-100">
      <div className="flex justify-between items-center mb-3">
        <h2 className="text-lg font-semibold">
          Parlay ({legs.length} {legs.length === 1 ? "leg" : "legs"})
        </h2>
        <button
          onClick={handleClear}
          className="text-xs text-slate-400 hover:text-slate-200"
        >
          Clear
        </button>
      </div>

      <ul className="space-y-2 mb-4 max-h-64 overflow-y-auto">
        {legs.map((leg) => (
          <li
            key={leg.id}
            className="flex justify-between items-center bg-slate-900 p-2 rounded"
          >
            <div className="flex-1 min-w-0">
              <div className="text-sm truncate">{leg.description}</div>
              <div className="text-xs text-slate-400 font-mono">
                {formatOdds(leg.americanOdds)} • {leg.book}
              </div>
            </div>
            <button
              onClick={() => removeLeg(leg.id)}
              className="text-slate-500 hover:text-red-400 ml-2 text-lg leading-none"
              aria-label="Remove leg"
            >
              ×
            </button>
          </li>
        ))}
      </ul>

      <div className="border-t border-slate-700 pt-3 space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-slate-400">Raw probability</span>
          <span className="font-mono">{formatPercent(raw)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">Combined odds</span>
          <span className="font-mono">{formatOdds(impliedToAmerican(raw))}</span>
        </div>
        {fair !== null && (
          <>
            <div className="flex justify-between text-emerald-300">
              <span>Fair probability (de-vigged)</span>
              <span className="font-mono">{formatPercent(fair)}</span>
            </div>
            <div className="flex justify-between text-emerald-300">
              <span>Fair odds</span>
              <span className="font-mono">{formatOdds(impliedToAmerican(fair))}</span>
            </div>
          </>
        )}
      </div>

      <div className="mt-4 pt-3 border-t border-slate-700">
        {!user ? (
          <Link
            href="/login"
            className="block w-full text-center bg-slate-700 hover:bg-slate-600 text-white py-2 rounded font-medium transition"
          >
            Log in to save
          </Link>
        ) : (
          <>
            {saveState.status === "idle" && (
              <button
                onClick={handleSave}
                className="w-full bg-emerald-600 hover:bg-emerald-500 text-white py-2 rounded font-medium transition"
              >
                Save Parlay
              </button>
            )}
            {saveState.status === "saving" && (
              <button
                disabled
                className="w-full bg-slate-600 text-slate-400 py-2 rounded font-medium cursor-not-allowed"
              >
                Saving...
              </button>
            )}
            {saveState.status === "saved" && (
              <div className="text-center text-sm">
                <div className="text-emerald-300">
                  ✓ Saved as parlay #{saveState.parlayId}
                </div>
                <Link
                  href="/parlays"
                  className="inline-block mt-1 text-xs text-slate-400 hover:text-slate-200 underline"
                >
                  View all saved parlays →
                </Link>
              </div>
            )}
            {saveState.status === "error" && (
              <div className="text-center text-sm text-red-300">
                Save failed: {saveState.error}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
