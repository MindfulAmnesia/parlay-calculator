import Link from "next/link";
import GameCard from "@/components/GameCard";
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

interface Sport {
  key: string;
  title: string;
  description: string;
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

async function fetchSportMeta(
  key: string,
): Promise<{ title: string; description: string }> {
  try {
    const res = await fetch("http://localhost:8000/sports", { cache: "no-store" });
    if (!res.ok) throw new Error("sports fetch failed");
    const sports: Sport[] = await res.json();
    const sport = sports.find((s) => s.key === key);
    if (sport) return { title: sport.title, description: sport.description };
  } catch {
    // fall through to safe default
  }
  return { title: key, description: "" };
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

  const [{ title, description }, games] = await Promise.all([
    fetchSportMeta(key),
    fetchGames(key, book),
  ]);

  return (
    <main className="min-h-screen bg-slate-900 text-slate-100 p-8 pb-64">
      <div className="max-w-3xl mx-auto">
        <Link href="/" className="text-sm text-slate-400 hover:text-slate-200">
          ← All sports
        </Link>
        <h1 className="text-3xl font-bold mt-2 mb-1">{title}</h1>
        {description && (
          <p className="text-sm text-slate-500 mb-2">{description}</p>
        )}
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
              <GameCard
                key={game.id}
                gameId={game.id}
                homeTeam={game.home_team}
                awayTeam={game.away_team}
                commenceTime={game.commence_time}
                prices={game.prices}
                source={game.source}
                sportKey={key}
              />
            ))}
          </ul>
        )}
      </div>
    </main>
  );
}
