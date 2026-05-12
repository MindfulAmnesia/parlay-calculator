"""
cli.py — Interactive parlay builder.
Usage: python cli.py <sport_key> [--book BOOK_KEY] [--offline]
Examples:
    python cli.py baseball_mlb                       # consensus across books
    python cli.py baseball_mlb --book draftkings     # DraftKings only
    python cli.py --offline --book lowvig            # cached data, LowVig only
Each leg is entered as '<event number> home' or '<event number> away'.
Press Return on a blank line to compute the joint probability.
"""

# ── Imports ───────────────────────────────────────────────────────────────────

# argparse lets us accept command-line arguments like --book and --offline.
import argparse
# json lets us read/write JSON files (a common data format that looks like Python dicts).
import json
# sys gives us access to system-level functions, like sys.exit() which stops the program.
import sys
# Path is a modern way to work with file paths — it's safer and cleaner than plain strings.
from pathlib import Path

# Import specific functions from our own modules (files in this project).
from odds_client import consensus_moneyline, get_moneyline_odds
from parlay import (
    Leg,
    american_to_implied_probability,
    devig_two_way,
    implied_to_american,
    parlay_probability,
)

# Path("data") / "sample_odds.json" builds a file path: data/sample_odds.json
# The / operator on Path objects joins folders and filenames together.
CACHE_FILE = Path("data") / "sample_odds.json"


def book_moneyline(event: dict, book_key: str) -> dict[str, int]:
    """Return {team_name: american_odds} for a specific bookmaker."""
    # Loop through every bookmaker attached to this event.
    for book in event.get("bookmakers", []):
        # Skip books that don't match the one the user asked for.
        if book.get("key") != book_key:
            continue
        # Loop through each market type (e.g. h2h, spreads).
        for market in book.get("markets", []):
            # We only want head-to-head (moneyline) odds here.
            if market.get("key") != "h2h":
                continue
            # Build a dict mapping team name → integer odds for every outcome.
            return {o["name"]: int(o["price"]) for o in market.get("outcomes", [])}
    # If nothing matched, return an empty dict instead of crashing.
    return {}


def get_prices(event: dict, book_key: str | None) -> dict[str, int]:
    """Get prices either from a specific book or aggregated consensus."""
    if book_key:
        # The user specified a particular sportsbook — use that book's prices.
        return book_moneyline(event, book_key)
    # No specific book requested — use the median across all books.
    # The dict comprehension converts each price to an int (whole number).
    return {name: int(price) for name, price in consensus_moneyline(event).items()}


def load_events(sport_key: str, offline: bool) -> list[dict]:
    """Either fetch fresh from the API or load cached JSON."""
    if offline:
        # In offline mode, read from the local cache file instead of the API.
        # This lets you test without using up your API quota.
        if not CACHE_FILE.exists():
            # If the cache file doesn't exist yet, tell the user and quit.
            print(f"No cached data at {CACHE_FILE}. Run without --offline first.")
            sys.exit(1)  # sys.exit(1) stops the program; the 1 signals an error.
        # read_text() reads the whole file as a string; json.loads() parses it.
        return json.loads(CACHE_FILE.read_text())
    # Online mode: fetch fresh data from the Odds API.
    return get_moneyline_odds(sport_key)


def main() -> None:
    # argparse reads the words typed after "python cli.py" and turns them into
    # a nice Python object we can query.
    parser = argparse.ArgumentParser(description=__doc__)

    # A positional argument — the user just types it without a flag name.
    # nargs="?" means it's optional; default="baseball_mlb" is used if omitted.
    parser.add_argument("sport_key", nargs="?", default="baseball_mlb")

    # --book is an optional flag. The user writes: --book draftkings
    parser.add_argument(
        "--book",
        help="Bookmaker key (e.g. draftkings, fanduel, betmgm, lowvig). "
             "Defaults to consensus across all books.",
    )

    # --offline is a "flag" argument — it's either present (True) or absent (False).
    # action="store_true" means: if --offline appears, set args.offline = True.
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use cached data/sample_odds.json instead of hitting the API",
    )

    # Actually parse the command line and store results in `args`.
    args = parser.parse_args()

    # Normalize the book key to lowercase so "DraftKings" == "draftkings".
    # If --book wasn't given, args.book is None, so we keep it as None.
    book_key = args.book.lower() if args.book else None
    book_label = book_key or "consensus (all books)"  # human-readable label

    events = load_events(args.sport_key, args.offline)
    if not events:
        print("No events with current odds.")
        return

    print(f"\nPricing source: {book_label}\n")

    # Build a flat table of events. Each row is either:
    #   (away_name, home_name, away_odds, home_odds)  — if prices were found
    #   None  — if this book didn't have prices for this event
    rows: list[tuple[str, str, int, int] | None] = []

    # enumerate(events, 1) gives us (1, event1), (2, event2), ...
    # The second argument sets the starting counter value to 1 instead of 0.
    for i, ev in enumerate(events, 1):
        away = ev.get("away_team", "?")
        home = ev.get("home_team", "?")
        prices = get_prices(ev, book_key)
        ao = prices.get(away)   # away team's odds (None if not found)
        ho = prices.get(home)   # home team's odds (None if not found)

        if ao is None or ho is None:
            # No prices available from the chosen book for this event.
            print(f"  {i:>2}.  {away}  @  {home}   [no prices from {book_label}]")
            rows.append(None)   # placeholder so the index still matches
        else:
            rows.append((away, home, int(ao), int(ho)))
            # :>2 right-aligns the number in 2 characters.
            # :+d always shows the sign (+150 or -200).
            print(f"  {i:>2}.  {away} ({int(ao):+d})  @  {home} ({int(ho):+d})")

    print("\nEnter legs as '<number> home' or '<number> away'. Blank line to finish.\n")

    legs: list[Leg] = []            # list of Leg objects the user builds up
    opposite_odds: list[int] = []   # the OTHER team's odds for each leg (for de-vig)

    # Keep asking for legs until the user presses Enter on a blank line.
    while True:
        # input() displays a prompt and waits for the user to type something.
        # .strip() removes leading/trailing whitespace.
        # .lower() converts to lowercase so "Home" == "home".
        # .split() breaks the string into a list of words: "3 home" → ["3", "home"]
        line = input(f"  Leg {len(legs)+1}: ").strip().lower().split()

        if not line:
            # Empty line — the user is done entering legs.
            break

        # Validate: we need exactly two words and the first must be a number.
        if len(line) != 2 or not line[0].isdigit():
            print("    format: '3 home' or '5 away'")
            continue   # `continue` skips back to the top of the while loop

        # Convert the first word from a string to an integer, then subtract 1
        # because our list uses 0-based indexing but the user sees 1-based numbers.
        idx, side = int(line[0]) - 1, line[1]

        # Make sure the index is within range and that this event has prices.
        if not (0 <= idx < len(rows)) or rows[idx] is None:
            print("    invalid event number or no prices available there")
            continue

        if side not in ("home", "h", "away", "a"):
            print("    side must be 'home' or 'away'")
            continue

        # Unpack the four values from the row tuple.
        away, home, ao, ho = rows[idx]

        if side in ("home", "h"):
            # User picked the home team — store its odds and the away team's odds.
            legs.append(Leg(f"{home} (vs {away})", ho))
            opposite_odds.append(ao)
        else:
            # User picked the away team.
            legs.append(Leg(f"{away} (@ {home})", ao))
            opposite_odds.append(ho)

    if not legs:
        # User pressed Enter immediately without adding any legs — nothing to show.
        return

    # Calculate raw parlay probability (just multiplying the book's implied odds).
    raw = parlay_probability(legs)

    # Calculate the "fair" probability after removing the vig.
    # We start at 1.0 and multiply in each leg's de-vigged probability.
    fair = 1.0
    for leg, opp in zip(legs, opposite_odds):
        # zip() pairs up matching items from two lists:
        #   zip([leg1, leg2], [opp1, opp2]) → [(leg1, opp1), (leg2, opp2)]
        own_p = american_to_implied_probability(leg.american_odds)
        opp_p = american_to_implied_probability(opp)
        # devig_two_way returns (fair_own, fair_opp); we only need the first one [0].
        fair *= devig_two_way(own_p, opp_p)[0]

    # Print the summary table.
    print("\n" + "=" * 64)
    print(f"Your parlay  ({book_label}):")
    for leg in legs:
        p = american_to_implied_probability(leg.american_odds)
        # Show each leg with its odds and the implied probability as a percentage.
        print(f"  {leg.american_odds:+6}  {leg.description}  ({p*100:.2f}%)")
    print("-" * 64)
    # Show both the raw (with vig) and fair (without vig) parlay probabilities,
    # plus their equivalent American odds.
    print(f"  Raw joint probability:        {raw*100:7.3f}%   ({implied_to_american(raw):+d})")
    print(f"  Fair (de-vigged) probability: {fair*100:7.3f}%   ({implied_to_american(fair):+d})")
    print("=" * 64)


# Only run main() when this file is executed directly.
# If another file imports cli.py, this block is skipped.
if __name__ == "__main__":
    main()
