import Link from "next/link";
import BookSelector from "./BookSelector";

interface Prices {
  [team: string]: number;
}

interface Game {
  id: string;
  home_team: string;
  away_team: string;
  commence_time: string;
  prices: Prices;
  source: string;
}

async function fetchGames(sportKey: string, book?: string): Promise<Game[]> {
  const url = book
    ? `http://localhost:8000/odds/${sportKey}?book=${book}`
    : `http://localhost:8000/odds/${sportKey}`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Backend returned ${res.status}`);
  }
  return res.json();
}

function formatOdds(odds: number): string {
  return odds > 0 ? `+${odds}` : `${odds}`;
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export default async function SportPage({
  params,
  searchParams,
}: {
  params: Promise<{ key: string }>;
  searchParams: Promise<{ book?: string }>;
}) {
  const { key } = await params;
  const { book } = await searchParams;
  const games = await fetchGames(key, book);

  return (
    <main className="min-h-screen bg-slate-900 text-slate-100 p-8">
      <div className="max-w-3xl mx-auto">
        <Link href="/" className="text-sm text-slate-400 hover:text-slate-200">
          ← All sports
        </Link>
        <h1 className="text-3xl font-bold mt-2 mb-2">{key}</h1>
        <p className="text-slate-400 mb-6">
          {games.length} upcoming game{games.length === 1 ? "" : "s"}
        </p>

        <BookSelector currentBook={book} />

        {games.length === 0 ? (
          <p className="text-slate-500 italic">
            No upcoming games for this sport.
          </p>
        ) : (
          <ul className="space-y-3">
            {games.map((game) => (
              <li key={game.id} className="bg-slate-800 p-4 rounded-lg">
                <div className="text-xs text-slate-500 mb-2">
                  {formatTime(game.commence_time)} • {game.source}
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex justify-between">
                    <span>{game.away_team}</span>
                    <span className="font-mono text-slate-300">
                      {game.prices[game.away_team] !== undefined
                        ? formatOdds(game.prices[game.away_team])
                        : "—"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>{game.home_team}</span>
                    <span className="font-mono text-slate-300">
                      {game.prices[game.home_team] !== undefined
                        ? formatOdds(game.prices[game.home_team])
                        : "—"}
                    </span>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  );
}