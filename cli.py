"""
cli.py — Interactive parlay builder.

Usage:
    python cli.py <sport_key>     # e.g. python cli.py baseball_mlb

Lists upcoming events with consensus moneylines. Build a parlay by
entering '<event number> home' or '<event number> away' one leg at a time.
Press Return on a blank line to compute the joint probability —
both raw (vig included) and de-vigged (fair).
"""

import sys

from odds_client import consensus_moneyline, get_moneyline_odds
from parlay import (
    Leg,
    american_to_implied_probability,
    devig_two_way,
    implied_to_american,
    parlay_probability,
)


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python cli.py <sport_key>")
        sys.exit(1)

    events = get_moneyline_odds(sys.argv[1])
    if not events:
        print("No events with current odds.")
        return

    # Build a flat table of (away, home, away_odds, home_odds) per event.
    rows = []
    print()
    for i, ev in enumerate(events, 1):
        away, home = ev.get("away_team", "?"), ev.get("home_team", "?")
        c = consensus_moneyline(ev)
        ao, ho = int(c.get(away, 0)), int(c.get(home, 0))
        rows.append((away, home, ao, ho))
        print(f"  {i:>2}.  {away} ({ao:+d})  @  {home} ({ho:+d})")

    print("\nEnter legs as '<number> home' or '<number> away'. Blank line to finish.\n")

    legs: list[Leg] = []
    opposite_odds: list[int] = []
    while True:
        line = input(f"  Leg {len(legs)+1}: ").strip().lower().split()
        if not line:
            break
        if len(line) != 2 or not line[0].isdigit():
            print("    format: '3 home' or '5 away'")
            continue
        idx, side = int(line[0]) - 1, line[1]
        if not (0 <= idx < len(rows)) or side not in ("home", "h", "away", "a"):
            print("    invalid number or side")
            continue
        away, home, ao, ho = rows[idx]
        if side in ("home", "h"):
            legs.append(Leg(f"{home} (vs {away})", ho))
            opposite_odds.append(ao)
        else:
            legs.append(Leg(f"{away} (@ {home})", ao))
            opposite_odds.append(ho)

    if not legs:
        return

    raw = parlay_probability(legs)
    fair = 1.0
    for leg, opp in zip(legs, opposite_odds):
        own_p = american_to_implied_probability(leg.american_odds)
        opp_p = american_to_implied_probability(opp)
        fair *= devig_two_way(own_p, opp_p)[0]

    print("\n" + "=" * 60)
    print("Your parlay:")
    for leg in legs:
        p = american_to_implied_probability(leg.american_odds)
        print(f"  {leg.american_odds:+6}  {leg.description}  ({p*100:.2f}%)")
    print("-" * 60)
    print(f"  Raw joint probability:        {raw*100:7.3f}%   ({implied_to_american(raw):+d})")
    print(f"  Fair (de-vigged) probability: {fair*100:7.3f}%   ({implied_to_american(fair):+d})")
    print("=" * 60)


if __name__ == "__main__":
    main()
