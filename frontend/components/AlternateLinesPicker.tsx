"use client";

import { useEffect, useState } from "react";
import { useParlay } from "@/lib/ParlayContext";
import { API_URL } from "@/lib/api";

interface Line {
  name: string;
  price: number;
  point: number;
}

interface AlternatesResponse {
  event_id: string;
  sport_key: string;
  home_team: string;
  away_team: string;
  commence_time: string;
  book: string;
  available_books: string[];
  spreads: Line[];
  totals: Line[];
}

interface AlternateLinesPickerProps {
  sportKey: string;
  gameId: string;
  book: string;
  homeTeam: string;
  awayTeam: string;
}

function formatOdds(odds: number): string {
  return odds > 0 ? `+${odds}` : `${odds}`;
}

function formatPoint(point: number): string {
  if (point > 0) return `+${point}`;
  if (point === 0) return "0";
  return `${point}`;
}

export default function AlternateLinesPicker({
  sportKey,
  gameId,
  book,
  homeTeam,
  awayTeam,
}: AlternateLinesPickerProps) {
  const { addLeg, removeLeg, hasLeg } = useParlay();
  const [data, setData] = useState<AlternatesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  // Fetch the ladder once, when the picker opens (or the book changes).
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(false);

    const fetchAlternates = async () => {
      try {
        const url = `${API_URL}/odds/${sportKey}/events/${gameId}/alternates?book=${book}`;
        const res = await fetch(url);
        if (!res.ok) throw new Error(`status ${res.status}`);
        const json: AlternatesResponse = await res.json();
        if (!cancelled) {
          setData(json);
          setLoading(false);
        }
      } catch {
        if (!cancelled) {
          setError(true);
          setLoading(false);
        }
      }
    };

    fetchAlternates();
    return () => {
      cancelled = true;
    };
  }, [sportKey, gameId, book]);

  if (loading) {
    return (
      <div className="mt-3 pt-3 border-t border-slate-700 text-xs text-slate-500">
        Loading alternate lines…
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="mt-3 pt-3 border-t border-slate-700 text-xs text-slate-500">
        Couldn&rsquo;t load alternate lines for this game.
      </div>
    );
  }

  // Group spreads by team and totals by side, preserving the backend's
  // ascending-by-point order so each ladder reads low to high.
  const spreadsByTeam: Record<string, Line[]> = {};
  for (const s of data.spreads) {
    if (!spreadsByTeam[s.name]) spreadsByTeam[s.name] = [];
    spreadsByTeam[s.name].push(s);
  }

  const totalsBySide: Record<string, Line[]> = {};
  for (const t of data.totals) {
    if (!totalsBySide[t.name]) totalsBySide[t.name] = [];
    totalsBySide[t.name].push(t);
  }

  // A spread's counterpart is the other team at the negated point
  // (e.g. Red Sox -1.5 pairs with Royals +1.5). Used for de-vigging.
  const spreadCounterpart = (name: string, point: number): Line | undefined => {
    const other = name === homeTeam ? awayTeam : homeTeam;
    return data.spreads.find((s) => s.name === other && s.point === -point);
  };

  // A total's counterpart is the opposite side at the same point.
  const totalCounterpart = (name: string, point: number): Line | undefined => {
    const other = name === "Over" ? "Under" : "Over";
    return data.totals.find((t) => t.name === other && t.point === point);
  };

  function LadderButton({
    legId,
    label,
    price,
    onAdd,
  }: {
    legId: string;
    label: string;
    price: number;
    onAdd: () => void;
  }) {
    const selected = hasLeg(legId);
    return (
      <button
        type="button"
        onClick={() => (selected ? removeLeg(legId) : onAdd())}
        className={`flex justify-between items-center w-full px-2 py-1.5 rounded transition text-sm ${
          selected
            ? "bg-emerald-700 hover:bg-emerald-600"
            : "bg-slate-900 hover:bg-slate-700"
        }`}
      >
        <span className="font-mono">{label}</span>
        <span className="font-mono text-slate-200 ml-2">{formatOdds(price)}</span>
      </button>
    );
  }

  const hasSpreads = Object.keys(spreadsByTeam).length > 0;
  const hasTotals = Object.keys(totalsBySide).length > 0;

  return (
    <div className="mt-3 pt-3 border-t border-slate-700 space-y-4">
      {!hasSpreads && !hasTotals && (
        <p className="text-xs text-slate-500 italic">
          No alternate lines posted for this game yet.
        </p>
      )}

      {hasSpreads && (
        <div>
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">
            Alternate Spreads
          </div>
          <div className="space-y-3">
            {Object.entries(spreadsByTeam).map(([team, lines]) => (
              <div key={team}>
                <div className="text-xs text-slate-500 mb-1">{team}</div>
                <div className="grid grid-cols-2 gap-1.5">
                  {lines.map((line) => {
                    const legId = `${gameId}:altspread:${team}:${line.point}`;
                    const counterpart = spreadCounterpart(team, line.point);
                    return (
                      <LadderButton
                        key={legId}
                        legId={legId}
                        label={formatPoint(line.point)}
                        price={line.price}
                        onAdd={() =>
                          addLeg({
                            id: legId,
                            description: `${team} ${formatPoint(line.point)}`,
                            americanOdds: line.price,
                            oppositeOdds: counterpart?.price,
                            gameId,
                            team,
                            sportKey,
                            book: data.book,
                          })
                        }
                      />
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {hasTotals && (
        <div>
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">
            Alternate Totals
          </div>
          <div className="space-y-3">
            {Object.entries(totalsBySide).map(([side, lines]) => (
              <div key={side}>
                <div className="text-xs text-slate-500 mb-1">{side}</div>
                <div className="grid grid-cols-2 gap-1.5">
                  {lines.map((line) => {
                    const legId = `${gameId}:alttotal:${side}:${line.point}`;
                    const counterpart = totalCounterpart(side, line.point);
                    return (
                      <LadderButton
                        key={legId}
                        legId={legId}
                        label={`${line.point}`}
                        price={line.price}
                        onAdd={() =>
                          addLeg({
                            id: legId,
                            description: `${side} ${line.point}`,
                            americanOdds: line.price,
                            oppositeOdds: counterpart?.price,
                            gameId,
                            team: side,
                            sportKey,
                            book: data.book,
                          })
                        }
                      />
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
