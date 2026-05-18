import Link from "next/link";

interface SavedParlay {
  id: number;
  created_at: string;
  sport_key: string | null;
  book: string | null;
  raw_probability_at_save: number | null;
  fair_probability_at_save: number | null;
}

async function fetchSavedParlays(): Promise<SavedParlay[]> {
  const res = await fetch("http://localhost:8000/parlays", {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Backend returned ${res.status}`);
  }
  return res.json();
}

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  const weekday = WEEKDAYS[d.getDay()];
  const month = MONTHS[d.getMonth()];
  const day = d.getDate();
  let hour = d.getHours();
  const minute = String(d.getMinutes()).padStart(2, "0");
  const ampm = hour >= 12 ? "PM" : "AM";
  hour = hour % 12 || 12;
  return `${weekday}, ${month} ${day}, ${hour}:${minute} ${ampm}`;
}

function formatPercent(p: number): string {
  return `${(p * 100).toFixed(2)}%`;
}

export default async function ParlaysPage() {
  const parlays = await fetchSavedParlays();

  return (
    <main className="min-h-screen bg-slate-900 text-slate-100 p-8 pb-32">
      <div className="max-w-3xl mx-auto">
        <Link href="/" className="text-sm text-slate-400 hover:text-slate-200">
          ← Home
        </Link>
        <h1 className="text-3xl font-bold mt-2 mb-2">Saved Parlays</h1>
        <p className="text-slate-400 mb-6">
          {parlays.length} parlay{parlays.length === 1 ? "" : "s"} on record
        </p>

        {parlays.length === 0 ? (
          <p className="text-slate-500 italic">
            No parlays saved yet. Build one on any sport page and click "Save Parlay."
          </p>
        ) : (
          <ul className="space-y-2">
            {parlays.map((p) => (
              <li key={p.id} className="bg-slate-800 p-4 rounded-lg">
                <div className="flex justify-between items-start">
                  <div>
                    <div className="font-semibold">Parlay #{p.id}</div>
                    <div className="text-xs text-slate-400 mt-1">
                      {p.sport_key ?? "mixed"} • {p.book ?? "consensus"}
                    </div>
                  </div>
                  <div className="text-xs text-slate-500">
                    {formatDateTime(p.created_at)}
                  </div>
                </div>
                {p.raw_probability_at_save !== null && (
                  <div className="text-sm mt-2 font-mono space-x-4">
                    <span className="text-slate-400">
                      Raw: {formatPercent(p.raw_probability_at_save)}
                    </span>
                    {p.fair_probability_at_save !== null && (
                      <span className="text-emerald-300">
                        Fair: {formatPercent(p.fair_probability_at_save)}
                      </span>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  );
}
