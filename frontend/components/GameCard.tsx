"use client";

import { ParlayLeg, useParlay } from "@/lib/ParlayContext";
import { calculateVig } from "@/lib/parlay-math";

interface Prices {
  [team: string]: number;
}

interface GameCardProps {
  gameId: string;
  homeTeam: string;
  awayTeam: string;
  commenceTime: string;
  prices: Prices;
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
  source,
  sportKey,
}: GameCardProps) {
  const { addLeg, removeLeg, hasLeg } = useParlay();
  const vig = calculateVig(prices);

  const handleClick = (team: string, americanOdds: number, opposingTeam: string) => {
    const legId = `${gameId}:${team}`;
    if (hasLeg(legId)) {
      removeLeg(legId);
      return;
    }
    const oppositeOdds = prices[opposingTeam];
    const leg: ParlayLeg = {
      id: legId,
      description: `${team} ML`,
      americanOdds,
      oppositeOdds,
      gameId,
      team,
      sportKey,
      book: source,
    };
    addLeg(leg);
  };

  const renderRow = (team: string, opposingTeam: string) => {
    const price = prices[team];
    const legId = `${gameId}:${team}`;
    const selected = hasLeg(legId);

    if (price === undefined) {
      return (
        <div className="flex justify-between items-center p-2 opacity-50">
          <span>{team}</span>
          <span className="font-mono text-slate-500">—</span>
        </div>
      );
    }

    return (
      <button
        type="button"
        onClick={() => handleClick(team, price, opposingTeam)}
        className={`flex justify-between items-center w-full p-2 rounded transition ${
          selected
            ? "bg-emerald-700 hover:bg-emerald-600"
            : "bg-slate-900 hover:bg-slate-700"
        }`}
      >
        <span>{team}</span>
        <span className="font-mono text-slate-200">{formatOdds(price)}</span>
      </button>
    );
  };

  return (
    <li className="bg-slate-800 p-4 rounded-lg">
      <div className="flex justify-between items-center mb-2 text-xs text-slate-500">
        <span>
          {formatTime(commenceTime)} • {source}
        </span>
        {vig !== null && (
          <span className={vigBadgeClass(vig)}>
            Vig {(vig * 100).toFixed(2)}%
          </span>
        )}
      </div>
      <div className="grid grid-cols-2 gap-2">
        {renderRow(awayTeam, homeTeam)}
        {renderRow(homeTeam, awayTeam)}
      </div>
    </li>
  );
}
