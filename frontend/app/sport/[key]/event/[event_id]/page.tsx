import Link from "next/link";
import { API_URL } from "@/lib/api";
import EventPropsList from "@/components/EventPropsList";

interface Prop {
  market: string;
  player: string;
  side: string;
  price: number | null;
  point: number | null;
  book: string;
}

interface PropsResponse {
  event_id: string;
  sport_key: string;
  home_team: string;
  away_team: string;
  commence_time: string;
  book: string;
  available_books: string[];
  props: Prop[];
}

async function fetchProps(
  sportKey: string,
  eventId: string,
  book: string,
): Promise<PropsResponse> {
  const url = `${API_URL}/odds/${sportKey}/events/${eventId}/props?book=${book}`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Backend returned ${res.status}`);
  }
  return res.json();
}

export default async function EventPage({
  params,
  searchParams,
}: {
  params: Promise<{ key: string; event_id: string }>;
  searchParams: Promise<{ book?: string }>;
}) {
  const { key, event_id } = await params;
  const { book } = await searchParams;
  const data = await fetchProps(key, event_id, book ?? "draftkings");

  return (
    <main className="min-h-screen bg-slate-900 text-slate-100 p-8 pb-64">
      <div className="max-w-3xl mx-auto">
        <Link
          href={`/sport/${key}`}
          className="text-sm text-slate-400 hover:text-slate-200"
        >
          ← Back to games
        </Link>
        <h1 className="text-3xl font-bold mt-2 mb-1">
          {data.away_team} @ {data.home_team}
        </h1>
        <p className="text-sm text-slate-500 mb-6">
          Player Props • {data.book}
        </p>

        <EventPropsList props={data.props} eventId={event_id} sportKey={key} />
      </div>
    </main>
  );
}
