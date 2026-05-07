"""
explore.py — Inspect the structure of an Odds API response.

Modes:
    python explore.py [sport_key] [--markets h2h,spreads,totals]
    python explore.py --offline

Quota cost: (number of markets) × (number of regions) per fresh fetch;
zero for --offline.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from odds_client import get_odds

CACHE_FILE = Path("data") / "sample_odds.json"


def book_market(event: dict, book_key: str, market_key: str) -> list[dict]:
    """Return outcomes for a specific (book, market) pair, or empty list."""
    for book in event.get("bookmakers", []):
        if book.get("key") != book_key:
            continue
        for market in book.get("markets", []):
            if market.get("key") == market_key:
                return market.get("outcomes", [])
    return []


def format_outcome(outcome: dict) -> str:
    """Format an outcome line, including 'point' for spreads/totals."""
    name = outcome.get("name", "?")
    price = outcome.get("price")
    point = outcome.get("point")
    price_s = f"{price:+d}" if isinstance(price, int) else str(price)
    if point is not None:
        return f"{name:<26} {price_s:>6}  (point: {point:+g})"
    return f"{name:<26} {price_s:>6}"


def load_events(sport_key: str, markets: list[str], offline: bool) -> list[dict]:
    """Either fetch fresh from API or load from cache."""
    if offline:
        if not CACHE_FILE.exists():
            print(f"No cached data at {CACHE_FILE}. Run without --offline first.")
            sys.exit(1)
        print(f"Reading cached data from {CACHE_FILE} (no quota use)\n")
        return json.loads(CACHE_FILE.read_text())

    print(f"Fetching {','.join(markets)} for {sport_key}...")
    events = get_odds(sport_key, markets=markets)
    CACHE_FILE.parent.mkdir(exist_ok=True)
    CACHE_FILE.write_text(json.dumps(events, indent=2))
    print(f"\nSaved raw JSON to {CACHE_FILE}\n")
    return events


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sport_key", nargs="?", default="baseball_mlb")
    parser.add_argument(
        "--markets",
        default="h2h",
        help="Comma-separated markets, e.g. h2h,spreads,totals. Default: h2h",
    )
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()

    markets = [m.strip() for m in args.markets.split(",")]
    events = load_events(args.sport_key, markets, args.offline)
    if not events:
        return

    # Aggregate counts
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

    coverage = Counter(len(ev.get("bookmakers", [])) for ev in events)
    print("\nBook-coverage histogram:")
    for n_books in sorted(coverage):
        bar = "█" * coverage[n_books]
        print(f"  {n_books:>2} book(s):  {bar}  ({coverage[n_books]} events)")

    # Detail view: best-covered event
    richest = max(events, key=lambda ev: len(ev.get("bookmakers", [])))
    away = richest.get("away_team", "?")
    home = richest.get("home_team", "?")
    n_books = len(richest.get("bookmakers", []))

    print(f"\n{'─' * 64}")
    print(f"Best-covered event ({n_books} books): {away} @ {home}")
    print(f"  Event ID:      {richest.get('id')}")
    print(f"  Commence time: {richest.get('commence_time')}")
    print(f"{'─' * 64}")

    if not richest.get("bookmakers"):
        return

    # All markets, in full, from the first bookmaker
    first_book = richest["bookmakers"][0]
    print(f"\nAll markets, in full, from {first_book.get('title', '?')}:")
    for market in first_book.get("markets", []):
        print(f"\n  [{market.get('key')}]")
        for outcome in market.get("outcomes", []):
            print(f"    {format_outcome(outcome)}")

    # Per-book h2h comparison (preserved from previous version)
    has_h2h = any(
        m.get("key") == "h2h"
        for b in richest.get("bookmakers", [])
        for m in b.get("markets", [])
    )
    if has_h2h:
        print(f"\n{'─' * 64}")
        print(f"h2h prices across all books for this event:")
        print(f"  {'Book':<16} {away:<22} {home:<22}")
        for book in richest.get("bookmakers", []):
            outs = book_market(richest, book["key"], "h2h")
            prices = {o["name"]: o["price"] for o in outs}
            a = prices.get(away)
            h = prices.get(home)
            a_s = f"{a:+d}" if isinstance(a, int) else "—"
            h_s = f"{h:+d}" if isinstance(h, int) else "—"
            print(f"  {book['title']:<16} {a_s:<22} {h_s:<22}")


if __name__ == "__main__":
    main()
