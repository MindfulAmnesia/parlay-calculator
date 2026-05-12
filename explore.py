"""
explore.py — Inspect the structure of an Odds API response.

Modes:
    python explore.py [sport_key] [--markets h2h,spreads,totals]
    python explore.py --offline

Quota cost: (number of markets) × (number of regions) per fresh fetch;
zero for --offline.
"""

# argparse handles command-line arguments like --markets and --offline.
import argparse
# json lets us read and write JSON files.
import json
# sys lets us call sys.exit() to stop the program with an error code.
import sys
# Counter is a special dict that counts how many times each value appears.
from collections import Counter
# Path is a clean, object-oriented way to work with file system paths.
from pathlib import Path

# Import our own function that calls the Odds API.
from odds_client import get_odds

# The file where we cache API responses so we can re-inspect them without
# spending API quota credits.
CACHE_FILE = Path("data") / "sample_odds.json"


def book_market(event: dict, book_key: str, market_key: str) -> list[dict]:
    """Return outcomes for a specific (book, market) pair, or empty list."""
    # Dig into the nested event structure:
    #   event → bookmakers list → markets list → outcomes list
    for book in event.get("bookmakers", []):
        if book.get("key") != book_key:
            continue   # skip books that don't match
        for market in book.get("markets", []):
            if market.get("key") == market_key:
                # Found the right book AND market — return the outcomes.
                return market.get("outcomes", [])
    # Nothing matched.
    return []


def format_outcome(outcome: dict) -> str:
    """Format an outcome line, including 'point' for spreads/totals."""
    name = outcome.get("name", "?")
    price = outcome.get("price")
    # Spreads and totals have a "point" value (like +3.5 or 47.5).
    # Moneyline (h2h) outcomes don't have one.
    point = outcome.get("point")

    # Format the price: if it's an integer show the sign (+/-), otherwise
    # just convert it to a string using str().
    price_s = f"{price:+d}" if isinstance(price, int) else str(price)

    if point is not None:
        # :<26 left-aligns the name in 26 characters; :>6 right-aligns the price
        # in 6 characters; :+g shows the point with its sign and no trailing zeros.
        return f"{name:<26} {price_s:>6}  (point: {point:+g})"
    return f"{name:<26} {price_s:>6}"


def load_events(sport_key: str, markets: list[str], offline: bool) -> list[dict]:
    """Either fetch fresh from API or load from cache."""
    if offline:
        if not CACHE_FILE.exists():
            print(f"No cached data at {CACHE_FILE}. Run without --offline first.")
            sys.exit(1)
        print(f"Reading cached data from {CACHE_FILE} (no quota use)\n")
        # Read the entire file as text and parse it from JSON format.
        return json.loads(CACHE_FILE.read_text())

    # Online mode: fetch from the API and also save a local copy for later.
    print(f"Fetching {','.join(markets)} for {sport_key}...")
    events = get_odds(sport_key, markets=markets)

    # Create the "data" folder if it doesn't exist yet.
    # exist_ok=True means "don't raise an error if it already exists."
    CACHE_FILE.parent.mkdir(exist_ok=True)

    # Write the events as formatted JSON to the cache file.
    # json.dumps() converts Python objects → a JSON string; indent=2 makes it readable.
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

    # Split the markets string on commas and strip spaces:
    #   "h2h, spreads" → ["h2h", "spreads"]
    markets = [m.strip() for m in args.markets.split(",")]

    events = load_events(args.sport_key, markets, args.offline)
    if not events:
        return

    # ── Summary statistics ─────────────────────────────────────────────────────
    # Counter() is like a dict but automatically initialises counts to 0.
    # We'll count how many events each book and market type appeared in.
    book_counter: Counter[str] = Counter()
    market_counter: Counter[str] = Counter()

    for ev in events:
        for book in ev.get("bookmakers", []):
            # += 1 increments the count for this book key.
            book_counter[book.get("key", "?")] += 1
            for market in book.get("markets", []):
                market_counter[market.get("key", "?")] += 1

    print(f"Events returned: {len(events)}")

    print(f"\nBookmakers seen ({len(book_counter)} unique):")
    # .most_common() returns items sorted by count, highest first.
    for key, count in book_counter.most_common():
        print(f"  {key:<25}  in {count} events")

    print(f"\nMarket types seen ({len(market_counter)} unique):")
    for key, count in market_counter.most_common():
        print(f"  {key:<25}  {count} occurrences")

    # Build a histogram of how many books covered each event.
    # len(ev.get("bookmakers", [])) counts the number of books for one event.
    # The Counter counts how many events had exactly 1 book, 2 books, etc.
    coverage = Counter(len(ev.get("bookmakers", [])) for ev in events)

    print("\nBook-coverage histogram:")
    for n_books in sorted(coverage):
        # Draw a simple bar chart using block characters (█).
        # "█" * 3 produces "███".
        bar = "█" * coverage[n_books]
        print(f"  {n_books:>2} book(s):  {bar}  ({coverage[n_books]} events)")

    # ── Detail view ────────────────────────────────────────────────────────────
    # Find the single event with the most bookmakers covering it.
    # max() with key= picks the item that gives the largest value for that function.
    # lambda ev: ... is an anonymous one-line function — it takes ev and returns
    # the number of bookmakers for that event.
    richest = max(events, key=lambda ev: len(ev.get("bookmakers", [])))
    away = richest.get("away_team", "?")
    home = richest.get("home_team", "?")
    n_books = len(richest.get("bookmakers", []))

    # "─" * 64 draws a horizontal divider line 64 characters wide.
    print(f"\n{'─' * 64}")
    print(f"Best-covered event ({n_books} books): {away} @ {home}")
    print(f"  Event ID:      {richest.get('id')}")
    print(f"  Commence time: {richest.get('commence_time')}")
    print(f"{'─' * 64}")

    if not richest.get("bookmakers"):
        return

    # Show every market from the first bookmaker in detail.
    # richest["bookmakers"][0] gets the first item in the bookmakers list.
    first_book = richest["bookmakers"][0]
    print(f"\nAll markets, in full, from {first_book.get('title', '?')}:")
    for market in first_book.get("markets", []):
        print(f"\n  [{market.get('key')}]")
        for outcome in market.get("outcomes", []):
            print(f"    {format_outcome(outcome)}")

    # ── Per-book h2h comparison ────────────────────────────────────────────────
    # Check whether any bookmaker has h2h data for this event.
    # `any()` returns True if at least one item in the iterable is True.
    # This is a "generator expression" — like a list comprehension but lazy.
    has_h2h = any(
        m.get("key") == "h2h"
        for b in richest.get("bookmakers", [])
        for m in b.get("markets", [])
    )

    if has_h2h:
        print(f"\n{'─' * 64}")
        print("h2h prices across all books for this event:")
        # Print the table header, aligning columns.
        print(f"  {'Book':<16} {away:<22} {home:<22}")

        for book in richest.get("bookmakers", []):
            # Get the h2h outcomes for this book and build a name→price lookup dict.
            outs = book_market(richest, book["key"], "h2h")
            prices = {o["name"]: o["price"] for o in outs}

            a = prices.get(away)
            h = prices.get(home)
            # Format odds with sign if they're integers; use "—" if missing.
            a_s = f"{a:+d}" if isinstance(a, int) else "—"
            h_s = f"{h:+d}" if isinstance(h, int) else "—"
            print(f"  {book['title']:<16} {a_s:<22} {h_s:<22}")


if __name__ == "__main__":
    main()
