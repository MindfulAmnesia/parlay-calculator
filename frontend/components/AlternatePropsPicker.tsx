"use client";

import { useEffect, useState } from "react";
import { useParlay } from "@/lib/ParlayContext";
import { API_URL } from "@/lib/api";

interface Prop {
  market: string;
  player: string;
  side: string;
  price: number | null;
  point: number | null;
  book: string;
}

interface AltPropsResponse {
  event_id: string;
  sport_key: string;
  home_team: string;
  away_team: string;
  commence_time: string;
  book: string;
  available_books: string[];
  props: Prop[];
}

interface AlternatePropsPickerProps {
  sportKey: string;
  eventId: string;
  book: string;
}

const MARKET_NAMES: Record<string, string> = {
  batter_hits: "Hits",
  batter_home_runs: "Home Runs",
  batter_total_bases: "Total Bases",
  batter_rbis: "RBIs",
  pitcher_strikeouts: "Strikeouts",
  player_points: "Points",
  player_rebounds: "Rebounds",
  player_assists: "Assists",
  player_threes: "Threes Made",
  player_pass_yds: "Passing Yards",
  player_pass_tds: "Passing TDs",
  player_rush_yds: "Rushing Yards",
  player_reception_yds: "Receiving Yards",
  player_goals: "Goals",
  player_total_saves: "Saves",
};

function marketName(key: string): string {
  return MARKET_NAMES[key] ?? key;
}

function formatOdds(odds: number): string {
  return odds > 0 ? `+${odds}` : `${odds}`;
}

// market -> player -> rungs (sorted by point ascending, then side)
type Grouped = Record<string, Record<string, Prop[]>>;

function groupAltProps(props: Prop[]): Grouped {
  const grouped: Grouped = {};
  for (const p of props) {
    if (p.price === null || p.point === null) continue;
    if (!grouped[p.market]) grouped[p.market] = {};
    if (!grouped[p.market][p.player]) grouped[p.market][p.player] = [];
    grouped[p.market][p.player].push(p);
  }
  for (const market of Object.keys(grouped)) {
    for (const player of Object.keys(grouped[market])) {
      grouped[market][player].sort((a, b) => {
        if (a.point !== b.point) return (a.point ?? 0) - (b.point ?? 0);
        return a.side.localeCompare(b.side);
      });
    }
  }
  return grouped;
}

export default function AlternatePropsPicker({
  sportKey,
  eventId,
  book,
}: AlternatePropsPickerProps) {
  const { addLeg, removeLeg, hasLeg } = useParlay();
  const [data, setData] = useState<AltPropsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(false);

    const fetchAltProps = async () => {
      try {
        const url = `${API_URL}/odds/${sportKey}/events/${eventId}/altprops?book=${book}`;
        const res = await fetch(url);
        if (!res.ok) throw new Error(`status ${res.status}`);
        const json: AltPropsResponse = await res.json();
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

    fetchAltProps();
    return () => {
      cancelled = true;
    };
  }, [sportKey, eventId, book]);

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
        Couldn&rsquo;t load alternate prop lines for this game.
      </div>
    );
  }

  // data is non-null past this point; capture it so the guarantee carries
  // into the nested functions below (TypeScript won't narrow `data` itself
  // inside a closure, but a fresh const keeps its non-null type).

  const propsData = data;

  const grouped = groupAltProps(propsData.props);
  const markets = Object.keys(grouped);

  // Counterpart: same player + market + point, opposite side. Usually absent
  // for milestone (Over-only) lines, in which case the leg shows raw odds.
  
  const counterpartFor = (p: Prop): Prop | undefined => {
    const other = p.side.toLowerCase() === "over" ? "under" : "over";
    return propsData.props.find(
      (c) =>
        c.market === p.market &&
        c.player === p.player &&
        c.point === p.point &&
        c.side.toLowerCase() === other,
    );
  };

  function RungButton({ prop }: { prop: Prop }) {
    if (prop.price === null || prop.point === null) return null;
    const legId = `${eventId}:altprop:${prop.market}:${prop.player}:${prop.side}:${prop.point}`;
    const selected = hasLeg(legId);
    const counterpart = counterpartFor(prop);
    const description = `${prop.player} ${prop.side} ${prop.point} ${marketName(prop.market)}`;
    return (
      <button
        type="button"
        onClick={() =>
          selected
            ? removeLeg(legId)
            : addLeg({
                id: legId,
                description,
                americanOdds: prop.price as number,
                oppositeOdds: counterpart?.price ?? undefined,
                gameId: eventId,
                team: prop.player,
                sportKey,
                book: propsData.book,
              })
        }
        className={`flex justify-between items-center w-full px-2 py-1.5 rounded transition text-sm ${
          selected
            ? "bg-emerald-700 hover:bg-emerald-600"
            : "bg-slate-900 hover:bg-slate-700"
        }`}
      >
        <span className="font-mono">
          {prop.side} {prop.point}
        </span>
        <span className="font-mono text-slate-200 ml-2">
          {formatOdds(prop.price)}
        </span>
      </button>
    );
  }

  if (markets.length === 0) {
    return (
      <div className="mt-3 pt-3 border-t border-slate-700 text-xs text-slate-500 italic">
        No alternate prop lines posted for this game yet.
      </div>
    );
  }

  return (
    <div className="mt-3 pt-3 border-t border-slate-700 space-y-5">
      <p className="text-xs text-slate-500">
        Milestone &amp; alternate lines. Many are Over-only, so legs without a
        matching opposite side show raw odds — the de-vigged fair number needs
        both sides.
      </p>
      {markets.map((market) => (
        <div key={market}>
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">
            {marketName(market)}
          </div>
          <div className="space-y-3">
            {Object.entries(grouped[market]).map(([player, rungs]) => (
              <div key={player}>
                <div className="text-xs text-slate-500 mb-1">{player}</div>
                <div className="grid grid-cols-2 gap-1.5">
                  {rungs.map((rung) => (
                    <RungButton key={`${rung.side}:${rung.point}`} prop={rung} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
