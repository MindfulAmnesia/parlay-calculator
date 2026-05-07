"""
explore.py — Inspect the structure of an Odds API response.

Modes:
    python explore.py [sport_key]              # fresh fetch (1+ credits)
    python explore.py --offline [sport_key]    # re-analyze saved JSON (free)

Quota cost: (number of markets) × (number of regions) per fresh fetch;
zero for --offline.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from odds_client import get_moneyline_odds

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


def load_events(sport_key: str, offline: bool) -> list[dict]:
    """Either fetch fresh from the API or read from the cached JSON file."""
    if offline:
        if not CACHE_FILE.exists():
            print(f"No cached data at {CACHE_FILE}. Run without --offline first.")
            sys.exit(1)
        print(f"Reading cached data from {CACHE_FILE} (no quota use)\n")
        return json.loads(CACHE_FILE.read_text())

    print(f"Fetching odds for {sport_key}...")
    events = get_moneyline_odds(sport_key)
    CACHE_FILE.parent.mkdir(exist_ok=True)
    CACHE_FILE.write_text(json.dumps(events, indent=2))
    print(f"\nSaved raw JSON to {CACHE_FILE}\n")
    return events


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sport_key", nargs="?", default="baseball_mlb")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Read from data/sample_odds.json instead of hitting the API",
    )
    args = parser.parse_args()

    events = load_events(args.sport_key, args.offline)
    if not events:
        print("No events.")
        return

    # Aggregate counts across all events
    book_counter: Counter[str] = Counter()
    market_counter: Counter[str] = Counter()
    for ev in events:
        for book in ev.get("bookmakers", []):
            book_counter[book.get("key", "?")] += 1
            for market in book.get("markets", []):
                market_counter[market.get("key", "?")] += 1

    print(f"Events returned: {len(events)}")

    print(f"\nBookmakers seen ({len(book_counter)} unique):")
    for key, count in book_counter.most_common():
        print(f"  {key:<25}  in {count} events")

    print(f"\nMarket types seen ({len(market_counter)} unique):")
    for key, count in market_counter.most_common():
        print(f"  {key:<25}  {count} occurrences")

    # How many books cover each event? (a histogram of market openness)
    coverage = Counter(len(ev.get("bookmakers", [])) for ev in events)
    print("\nBook-coverage histogram (books per event):")
    for n_books in sorted(coverage):
        bar = "█" * coverage[n_books]
        print(f"  {n_books:>2} book(s):  {bar}  ({coverage[n_books]} events)")

    # Detail view: pick the event with the *most* bookmakers, not the first one
    richest = max(events, key=lambda ev: len(ev.get("bookmakers", [])))
    away = richest.get("away_team", "?")
    home = richest.get("home_team", "?")
    n_books = len(richest.get("bookmakers", []))

    print(f"\n{'─' * 64}")
    print(f"Best-covered event ({n_books} books): {away} @ {home}")
    print(f"  Event ID:      {richest.get('id')}")
    print(f"  Commence time: {richest.get('commence_time')}")
    print(f"{'─' * 64}")
    print(f"  {'Book':<16} {away:<22} {home:<22}")
    print(f"{'─' * 64}")
    for book in richest.get("bookmakers", []):
        prices = book_moneyline(richest, book["key"])
        a = prices.get(away)
        h = prices.get(home)
        a_s = f"{a:+d}" if isinstance(a, int) else "—"
        h_s = f"{h:+d}" if isinstance(h, int) else "—"
        print(f"  {book['title']:<16} {a_s:<22} {h_s:<22}")


if __name__ == "__main__":
    main()
    