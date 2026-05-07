"""
cli.py — Interactive parlay builder.

Usage:
    python cli.py <sport_key> [--book BOOK_KEY] [--offline]

Examples:
    python cli.py baseball_mlb                       # consensus across books
    python cli.py baseball_mlb --book draftkings     # DraftKings only
    python cli.py --offline --book lowvig            # cached data, LowVig only

Each leg is entered as '<event number> home' or '<event number> away'.
Press Return on a blank line to compute the joint probability.
"""

import argparse
import json
import sys
from pathlib import Path

from odds_client import consensus_moneyline, get_moneyline_odds
from parlay import (
    Leg,
    american_to_implied_probability,
    devig_two_way,
    implied_to_american,
    parlay_probability,
)

CACHE_FILE = Path("data") / "sample_odds.json"


def book_moneyline(event: dict, book_key: str) -> dict[str, int]:
    """Return {team_name: american_odds} for a specific bookmaker."""
    for book in event.get("bookmakers", []):
        if book.get("key") != book_key:
            continue
        for market in book.get("markets", []):
            if market.get("key") != "h2h":
                continue
            return {o["name"]: int(o["price"]) for o in market.get("outcomes", [])}
    return {}


def get_prices(event: dict, book_key: str | None) -> dict[str, int]:
    """Get prices either from a specific book or aggregated consensus."""
    if book_key:
        return book_moneyline(event, book_key)
    return {name: int(price) for name, price in consensus_moneyline(event).items()}


def load_events(sport_key: str, offline: bool) -> list[dict]:
    """Either fetch fresh from the API or load cached JSON."""
    if offline:
        if not CACHE_FILE.exists():
            print(f"No cached data at {CACHE_FILE}. Run without --offline first.")
            sys.exit(1)
        return json.loads(CACHE_FILE.read_text())
    return get_moneyline_odds(sport_key)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sport_key", nargs="?", default="baseball_mlb")
    parser.add_argument(
        "--book",
        help="Bookmaker key (e.g. draftkings, fanduel, betmgm, lowvig). "
             "Defaults to consensus across all books.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use cached data/sample_odds.json instead of hitting the API",
    )
    args = parser.parse_args()

    book_key = args.book.lower() if args.book else None
    book_label = book_key or "consensus (all books)"

    events = load_events(args.sport_key, args.offline)
    if not events:
        print("No events with current odds.")
        return

    print(f"\nPricing source: {book_label}\n")

    # Build a flat table; mark events lacking prices from the chosen source
    rows: list[tuple[str, str, int, int] | None] = []
    for i, ev in enumerate(events, 1):
        away = ev.get("away_team", "?")
        home = ev.get("home_team", "?")
        prices = get_prices(ev, book_key)
        ao = prices.get(away)
        ho = prices.get(home)
        if ao is None or ho is None:
            print(f"  {i:>2}.  {away}  @  {home}   [no prices from {book_label}]")
            rows.append(None)
        else:
            rows.append((away, home, int(ao), int(ho)))
            print(f"  {i:>2}.  {away} ({int(ao):+d})  @  {home} ({int(ho):+d})")

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
        if not (0 <= idx < len(rows)) or rows[idx] is None:
            print("    invalid event number or no prices available there")
            continue
        if side not in ("home", "h", "away", "a"):
            print("    side must be 'home' or 'away'")
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

    print("\n" + "=" * 64)
    print(f"Your parlay  ({book_label}):")
    for leg in legs:
        p = american_to_implied_probability(leg.american_odds)
        print(f"  {leg.american_odds:+6}  {leg.description}  ({p*100:.2f}%)")
    print("-" * 64)
    print(f"  Raw joint probability:        {raw*100:7.3f}%   ({implied_to_american(raw):+d})")
    print(f"  Fair (de-vigged) probability: {fair*100:7.3f}%   ({implied_to_american(fair):+d})")
    print("=" * 64)

if __name__ == "__main__":
    main()
