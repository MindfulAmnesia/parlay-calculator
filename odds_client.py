"""
odds_client.py — Thin client for The Odds API.
Reference: https://the-odds-api.com/liveapi/guides/v4/
"""

import os
from statistics import median
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ODDS_API_KEY")
BASE_URL = "https://api.the-odds-api.com/v4"

class OddsAPIError(Exception):
    """Raised when the API returns an error or unexpected response."""

def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    """Perform a GET against the API and return parsed JSON.

    Prints quota headers when present; raises OddsAPIError on non-200.
    """
    if not API_KEY:
        raise OddsAPIError("ODDS_API_KEY not set. Check your .env file.")

    response = requests.get(
        f"{BASE_URL}{path}",
        params={"apiKey": API_KEY, **(params or {})},
        timeout=10,
    )

    used = response.headers.get("x-requests-used")
    remaining = response.headers.get("x-requests-remaining")
    if remaining is not None:
        print(f"[quota] used={used}  remaining={remaining}")

    if response.status_code != 200:
        raise OddsAPIError(
            f"{response.status_code} {response.reason}: {response.text[:200]}"
        )
    return response.json()


def list_sports(active_only: bool = True) -> list[dict]:
    """Return the catalog of sports the API tracks. Free — no quota use."""
    sports = _get("/sports")
    return [s for s in sports if s.get("active")] if active_only else sports


def get_odds(
    sport_key: str,
    markets: list[str] | None = None,
    regions: str = "us",
) -> list[dict]:
    """Fetch live odds for the given sport, markets, and regions.

    Quota cost: len(markets) × number of regions per call.
    Defaults to ['h2h'] (1 credit per region).
    """
    if markets is None:
        markets = ["h2h"]
    return _get(
        f"/sports/{sport_key}/odds",
        params={
            "regions": regions,
            "markets": ",".join(markets),
            "oddsFormat": "american",
        },
    )


def get_moneyline_odds(sport_key: str, regions: str = "us") -> list[dict]:
    """Convenience wrapper: fetch h2h only. 1 credit per region."""
    return get_odds(sport_key, markets=["h2h"], regions=regions)


def book_moneyline(event: dict, book_key: str) -> dict[str, int]:
    """Return {team_name: american_odds} for one specific bookmaker."""
    for book in event.get("bookmakers", []):
        if book.get("key") != book_key:
            continue
        for market in book.get("markets", []):
            if market.get("key") != "h2h":
                continue
            return {o["name"]: int(o["price"]) for o in market.get("outcomes", [])}
    return {}

def book_moneyline(event: dict, book_key: str) -> dict[str, int]:
    """Return {team_name: american_odds} for one specific bookmaker."""
    for book in event.get("bookmakers", []):
        if book.get("key") != book_key:
            continue
        for market in book.get("markets", []):
            if market.get("key") != "h2h":
                continue
            return {o["name"]: int(o["price"]) for o in market.get("outcomes", [])}
    return {}

def consensus_moneyline(event: dict) -> dict[str, float]:
    """Median moneyline per outcome across all bookmakers in the event."""
    prices: dict[str, list[int]] = {}
    for book in event.get("bookmakers", []):
        for market in book.get("markets", []):
            if market.get("key") != "h2h":
                continue
            for outcome in market.get("outcomes", []):
                name = outcome.get("name")
                price = outcome.get("price")
                if name and price is not None:
                    prices.setdefault(name, []).append(price)
    return {name: median(odds_list) for name, odds_list in prices.items()}


def main() -> None:
    """Demo: list active sports, then show consensus moneylines for one."""
    sports = list_sports()
    print(f"\n{len(sports)} active sports:\n")
    for s in sports[:20]:
        print(f"  {s['key']:<42}  {s['title']}")
    if len(sports) > 20:
        print(f"  ... and {len(sports) - 20} more")

    sport_key = input("\nEnter a sport key: ").strip()
    if not sport_key:
        print("No sport entered.")
        return

    events = get_moneyline_odds(sport_key)
    if not events:
        print(f"No events with current odds for {sport_key}.")
        return

    print(f"\n{len(events)} events found. First 5:\n")
    for ev in events[:5]:
        print(f"  {ev.get('away_team')} @ {ev.get('home_team')}")
        for name, price in consensus_moneyline(ev).items():
            print(f"      {name:<30}  {int(price):+d}")
        print()


if __name__ == "__main__":
    main()