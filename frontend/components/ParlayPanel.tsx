"use client";

import { useParlay } from "@/lib/ParlayContext";
import { impliedToAmerican, parlayProbability } from "@/lib/parlay-math";

function formatPercent(p: number): string {
  return `${(p * 100).toFixed(2)}%`;
}

function formatOdds(odds: number): string {
  return odds > 0 ? `+${odds}` : `${odds}`;
}

export default function ParlayPanel() {
  const { legs, removeLeg, clear } = useParlay();

  if (legs.length === 0) {
    return null;
  }

  const { raw, fair } = parlayProbability(legs);

  return (
    <div className="fixed bottom-4 right-4 w-96 bg-slate-800 border border-slate-700 rounded-lg shadow-2xl p-4 text-slate-100">
      <div className="flex justify-between items-center mb-3">
        <h2 className="text-lg font-semibold">
          Parlay ({legs.length} {legs.length === 1 ? "leg" : "legs"})
        </h2>
        <button
          onClick={clear}
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
    </div>
  );
}
