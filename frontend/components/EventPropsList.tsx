"use client";

import { useParlay } from "@/lib/ParlayContext";

interface Prop {
  market: string;
  player: string;
  side: string;
  price: number | null;
  point: number | null;
  book: string;
}

interface EventPropsListProps {
  props: Prop[];
  eventId: string;
  sportKey: string;
}

// Friendly display names for the raw market keys from the API
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
  player_anytime_td: "Anytime TD",
  player_goals: "Goals",
  player_total_saves: "Saves",
};

function marketName(key: string): string {
  return MARKET_NAMES[key] ?? key;
}

function formatOdds(odds: number): string {
  return odds > 0 ? `+${odds}` : `${odds}`;
}

interface PlayerProp {
  over?: Prop;
  under?: Prop;
}

type GroupedProps = Record<string, Record<string, PlayerProp>>;

function groupProps(props: Prop[]): GroupedProps {
  const grouped: GroupedProps = {};
  for (const p of props) {
    if (p.price === null) continue;
    if (!grouped[p.market]) grouped[p.market] = {};
    if (!grouped[p.market][p.player]) grouped[p.market][p.player] = {};
    const side = p.side.toLowerCase();
    if (side === "over") grouped[p.market][p.player].over = p;
    else if (side === "under") grouped[p.market][p.player].under = p;
  }
  return grouped;
}

export default function EventPropsList({
  props,
  eventId,
  sportKey,
}: EventPropsListProps) {
  const { addLeg, removeLeg, hasLeg } = useParlay();

  if (props.length === 0) {
    return (
      <p className="text-slate-500 italic">
        No player props available for this game yet. Books usually post props
        closer to game time — check back within a few hours of first pitch.
      </p>
    );
  }

  const grouped = groupProps(props);

  function PropButton({
    prop,
    counterpart,
  }: {
    prop: Prop;
    counterpart?: Prop;
  }) {
    if (prop.price === null) return null;
    const legId = `${eventId}:prop:${prop.market}:${prop.player}:${prop.side}`;
    const selected = hasLeg(legId);
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
                book: prop.book,
              })
        }
        className={`flex justify-between items-center w-full p-2 rounded transition ${
          selected
            ? "bg-emerald-700 hover:bg-emerald-600"
            : "bg-slate-900 hover:bg-slate-700"
        }`}
      >
        <span className="text-sm">{prop.side}</span>
        <span className="font-mono text-slate-200 text-sm">
          {formatOdds(prop.price)}
        </span>
      </button>
    );
  }

  return (
    <div className="space-y-6">
      {Object.entries(grouped).map(([market, players]) => (
        <div key={market}>
          <h2 className="text-lg font-semibold mb-2">{marketName(market)}</h2>
          <ul className="space-y-2">
            {Object.entries(players).map(([player, sides]) => {
              const point = sides.over?.point ?? sides.under?.point;
              return (
                <li key={player} className="bg-slate-800 p-3 rounded-lg">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-medium">{player}</span>
                    <span className="text-xs text-slate-500 font-mono">
                      {point !== null && point !== undefined ? point : ""}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    {sides.over && (
                      <PropButton prop={sides.over} counterpart={sides.under} />
                    )}
                    {sides.under && (
                      <PropButton prop={sides.under} counterpart={sides.over} />
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </div>
  );
}
