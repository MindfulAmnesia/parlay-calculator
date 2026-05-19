"use client";

import { useParlay } from "@/lib/ParlayContext";
import { calculateVig } from "@/lib/parlay-math";

interface Prices {
  [team: string]: number;
}

interface PointOutcome {
  name: string;
  price: number;
  point: number;
}

interface GameCardProps {
  gameId: string;
  homeTeam: string;
  awayTeam: string;
  commenceTime: string;
  prices: Prices;
  spreads: PointOutcome[];
  totals: PointOutcome[];
  source: string;
  sportKey: string;
}

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

function formatOdds(odds: number): string {
  return odds > 0 ? `+${odds}` : `${odds}`;
}

function formatPoint(point: number): string {
  if (point > 0) return `+${point}`;
  if (point === 0) return "0";
  return `${point}`;
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "TBD";
  const weekday = WEEKDAYS[d.getDay()];
  const month = MONTHS[d.getMonth()];
  const day = d.getDate();
  let hour = d.getHours();
  const minute = String(d.getMinutes()).padStart(2, "0");
  const ampm = hour >= 12 ? "PM" : "AM";
  hour = hour % 12 || 12;
  return `${weekday}, ${month} ${day}, ${hour}:${minute} ${ampm}`;
}

function vigBadgeClass(vig: number): string {
  if (vig < 0.04) {
    return "px-2 py-0.5 rounded text-xs font-medium font-mono bg-emerald-900 text-emerald-300";
  }
  if (vig < 0.06) {
    return "px-2 py-0.5 rounded text-xs font-medium font-mono bg-amber-900 text-amber-300";
  }
  return "px-2 py-0.5 rounded text-xs font-medium font-mono bg-red-900 text-red-300";
}

export default function GameCard({
  gameId,
  homeTeam,
  awayTeam,
  commenceTime,
  prices,
  spreads,
  totals,
  source,
  sportKey,
}: GameCardProps) {
  const { addLeg, removeLeg, hasLeg } = useParlay();
  const vig = calculateVig(prices);

  // Generic pickable button used by all three markets
  function PickButton({
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
        className={`flex justify-between items-center w-full p-2 rounded transition ${
          selected
            ? "bg-emerald-700 hover:bg-emerald-600"
            : "bg-slate-900 hover:bg-slate-700"
        }`}
      >
        <span className="truncate text-sm">{label}</span>
        <span className="font-mono text-slate-200 ml-2 text-sm">
          {formatOdds(price)}
        </span>
      </button>
    );
  }

  // Render one h2h row (moneyline)
  function renderH2H(team: string, opposingTeam: string) {
    const price = prices[team];
    if (price === undefined) {
      return (
        <div
          key={`h2h-empty-${team}`}
          className="flex justify-between items-center p-2 opacity-50 text-sm"
        >
          <span>{team}</span>
          <span className="font-mono text-slate-500">—</span>
        </div>
      );
    }
    const legId = `${gameId}:h2h:${team}`;
    const oppositeOdds = prices[opposingTeam];
    return (
      <PickButton
        key={legId}
        legId={legId}
        label={team}
        price={price}
        onAdd={() => {
          addLeg({
            id: legId,
            description: `${team} ML`,
            americanOdds: price,
            oppositeOdds,
            gameId,
            team,
            sportKey,
            book: source,
          });
        }}
      />
    );
  }

  // Render one outcome of a spread or total
  function renderPointOutcome(
    market: "spread" | "total",
    outcome: PointOutcome,
    counterpart: PointOutcome | undefined,
  ) {
    const legId = `${gameId}:${market}:${outcome.name}`;
    const label =
      market === "spread"
        ? `${outcome.name} ${formatPoint(outcome.point)}`
        : `${outcome.name} ${outcome.point}`;
    const description = label;

    return (
      <PickButton
        key={legId}
        legId={legId}
        label={label}
        price={outcome.price}
        onAdd={() => {
          addLeg({
            id: legId,
            description,
            americanOdds: outcome.price,
            oppositeOdds: counterpart?.price,
            gameId,
            team: outcome.name,
            sportKey,
            book: source,
          });
        }}
      />
    );
  }

  const spreadCounterpart = (name: string) =>
    spreads.find((s) => s.name !== name);
  const totalCounterpart = (name: string) =>
    totals.find((t) => t.name !== name);

  return (
    <li className="bg-slate-800 p-4 rounded-lg">
      {/* Header */}
      <div className="flex justify-between items-center mb-3 text-xs text-slate-500">
        <span>
          {formatTime(commenceTime)} • {source}
        </span>
        {vig !== null && (
          <span className={vigBadgeClass(vig)}>
            Vig {(vig * 100).toFixed(2)}%
          </span>
        )}
      </div>

      {/* Moneyline */}
      <div className="mb-3">
        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1.5">
          Moneyline
        </div>
        <div className="grid grid-cols-2 gap-2">
          {renderH2H(awayTeam, homeTeam)}
          {renderH2H(homeTeam, awayTeam)}
        </div>
      </div>

      {/* Spread */}
      {spreads.length === 2 && (
        <div className="mb-3">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1.5">
            Spread
          </div>
          <div className="grid grid-cols-2 gap-2">
            {spreads.map((s) =>
              renderPointOutcome("spread", s, spreadCounterpart(s.name)),
            )}
          </div>
        </div>
      )}

      {/* Total */}
      {totals.length === 2 && (
        <div>
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1.5">
            Total
          </div>
          <div className="grid grid-cols-2 gap-2">
            {totals.map((t) =>
              renderPointOutcome("total", t, totalCounterpart(t.name)),
            )}
          </div>
        </div>
      )}
    </li>
  );
}
