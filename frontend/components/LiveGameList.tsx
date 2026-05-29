"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import GameCard from "@/components/GameCard";
import { API_URL } from "@/lib/api";

const STORAGE_KEY = "parlay-calculator:book";

interface Prices {
  [team: string]: number;
}

interface PointOutcome {
  name: string;
  price: number;
  point: number;
}

interface Game {
  id: string;
  home_team: string;
  away_team: string;
  commence_time: string;
  prices: Prices;
  spreads: PointOutcome[];
  totals: PointOutcome[];
  source: string;
}

interface LiveGameListProps {
  initialGames: Game[];
  sportKey: string;
}

const POLL_INTERVAL_MS = 30_000;

function timeAgo(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 5) return "just now";
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes}m ago`;
}

function TimeAgo({ date }: { date: Date }) {
  const [, setTick] = useState(0);
  useEffect(() => {
    const interval = setInterval(() => setTick((t) => t + 1), 5000);
    return () => clearInterval(interval);
  }, []);
  return <>{timeAgo(date)}</>;
}

export default function LiveGameList({
  initialGames,
  sportKey,
}: LiveGameListProps) {
  const searchParams = useSearchParams();

  // Prefer the book in the URL; if absent, fall back to the saved choice so
  // games load for the right book even before the selector's redirect lands.
  const urlBook = searchParams.get("book") ?? undefined;
  const [book, setBook] = useState<string | undefined>(urlBook);

  useEffect(() => {
    if (urlBook) {
      setBook(urlBook);
      return;
    }
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      setBook(saved ?? undefined);
    } catch {
      setBook(undefined);
    }
  }, [urlBook]);

  const [games, setGames] = useState<Game[]>(initialGames);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  useEffect(() => {
    const fetchGames = async () => {
      try {
        const url = book
          ? `${API_URL}/odds/${sportKey}?book=${book}`
          : `${API_URL}/odds/${sportKey}`;
        const res = await fetch(url);
        if (res.ok) {
          const data: Game[] = await res.json();
          setGames(data);
          setLastUpdated(new Date());
        }
      } catch {
        // Network error — keep showing existing data rather than crashing
      }
    };

    fetchGames(); // fetch immediately when the sport or book changes
    const interval = setInterval(fetchGames, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [sportKey, book]);

  return (
    <>
      <div className="flex justify-between items-center mb-4 text-xs text-slate-500">
        <span>
          {games.length} upcoming game{games.length === 1 ? "" : "s"}
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          Live • Updated <TimeAgo date={lastUpdated} />
        </span>
      </div>

      {games.length === 0 ? (
        <p className="text-slate-500 italic">
          No upcoming games for this sport.
        </p>
      ) : (
        <ul className="space-y-3">
          {games.map((game) => (
            <GameCard
              key={game.id}
              gameId={game.id}
              homeTeam={game.home_team}
              awayTeam={game.away_team}
              commenceTime={game.commence_time}
              prices={game.prices}
              spreads={game.spreads}
              totals={game.totals}
              source={game.source}
              sportKey={sportKey}
            />
          ))}
        </ul>
      )}
    </>
  );
}
