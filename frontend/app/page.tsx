import Link from "next/link";
import { API_URL } from "@/lib/api";

interface Sport {
  key: string;
  active: boolean;
  group: string;
  title: string;
  description: string;
  has_outrights: boolean;
}

async function fetchSports(): Promise<Sport[]> {
  const res = await fetch(`${API_URL}/sports`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Backend returned ${res.status}`);
  }
  return res.json();
}

export default async function HomePage() {
  const sports = await fetchSports();

  return (
    <main className="min-h-screen bg-slate-900 text-slate-100 p-8 pb-32">
      <div className="max-w-3xl mx-auto">
        <div className="flex justify-between items-start mb-2">
          <h1 className="text-3xl font-bold">Parlay Calculator</h1>
          <Link
            href="/parlays"
            className="text-sm text-slate-400 hover:text-slate-200"
          >
            Saved Parlays →
          </Link>
        </div>
        <p className="text-slate-400 mb-8">
          {sports.length} active sports from The Odds API
        </p>

        <ul className="space-y-2">
          {sports.map((sport) => (
            <li key={sport.key}>
              <Link
                href={`/sport/${sport.key}`}
                className="bg-slate-800 hover:bg-slate-700 transition p-4 rounded-lg flex justify-between items-center"
              >
                <div>
                  <div className="font-semibold">{sport.title}</div>
                  <div className="text-sm text-slate-400">{sport.description}</div>
                </div>
                <div className="text-xs text-slate-500 font-mono">{sport.key}</div>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </main>
  );
}
