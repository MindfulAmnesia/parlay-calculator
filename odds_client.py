"""
odds_client.py — Thin client for The Odds API with in-memory caching.
"""

import os
from statistics import median
from threading import Lock
from typing import Any

import requests
from cachetools import TTLCache
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ODDS_API_KEY")
BASE_URL = "https://api.the-odds-api.com/v4"


class OddsAPIError(Exception):
    """Raised when the API returns an error or unexpected response."""


def _get(path: str, params: dict[str, Any] | None = None) -> Any:
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
    """Return the catalog of sports the API tracks. Free, no quota use."""
    sports = _get("/sports")
    return [s for s in sports if s.get("active")] if active_only else sports


def get_odds(
    sport_key: str,
    markets: list[str] | None = None,
    regions: str = "us",
) -> list[dict]:
    """Fetch live odds. Quota cost: len(markets) * number of regions per call."""
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


def _market_outcomes(event: dict, book_key: str, market_key: str) -> list[dict]:
    """Return raw outcomes list for one (book, market) combo, or [] if absent."""
    for book in event.get("bookmakers", []):
        if book.get("key") != book_key:
            continue
        for market in book.get("markets", []):
            if market.get("key") == market_key:
                return market.get("outcomes", [])
    return []


def book_moneyline(event: dict, book_key: str) -> dict[str, int]:
    """Return {team_name: american_odds} for one specific bookmaker's h2h."""
    outcomes = _market_outcomes(event, book_key, "h2h")
    return {o["name"]: int(o["price"]) for o in outcomes if "price" in o}


def book_spreads(event: dict, book_key: str) -> list[dict]:
    """Return [{name, price, point}, ...] for one book's spreads, or []."""
    outcomes = _market_outcomes(event, book_key, "spreads")
    return [
        {
            "name": o["name"],
            "price": int(o["price"]),
            "point": float(o["point"]),
        }
        for o in outcomes
        if "price" in o and "point" in o
    ]


def book_totals(event: dict, book_key: str) -> list[dict]:
    """Return [{name, price, point}, ...] for one book's totals, or []."""
    outcomes = _market_outcomes(event, book_key, "totals")
    return [
        {
            "name": o["name"],
            "price": int(o["price"]),
            "point": float(o["point"]),
        }
        for o in outcomes
        if "price" in o and "point" in o
    ]


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


# ---------- In-memory caching layer ----------
# First call fetches and caches; subsequent calls within the TTL window
# serve the cached value. Caches reset on server restart.

_odds_cache: TTLCache = TTLCache(maxsize=64, ttl=60)
_odds_cache_lock = Lock()

_sports_cache: TTLCache = TTLCache(maxsize=2, ttl=300)
_sports_cache_lock = Lock()


def get_odds_cached(
    sport_key: str,
    markets: list[str] | None = None,
    regions: str = "us",
) -> list[dict]:
    """Cached wrapper around get_odds. TTL: 60 seconds."""
    if markets is None:
        markets = ["h2h"]
    cache_key = (sport_key, tuple(markets), regions)

    with _odds_cache_lock:
        if cache_key in _odds_cache:
            print(f"[cache] HIT  odds {cache_key}")
            return _odds_cache[cache_key]

    print(f"[cache] MISS odds {cache_key}")
    events = get_odds(sport_key, markets=markets, regions=regions)

    with _odds_cache_lock:
        _odds_cache[cache_key] = events

    return events


def list_sports_cached(active_only: bool = True) -> list[dict]:
    """Cached wrapper around list_sports. TTL: 300 seconds (5 minutes)."""
    cache_key = ("active_only", active_only)

    with _sports_cache_lock:
        if cache_key in _sports_cache:
            print(f"[cache] HIT  sports active_only={active_only}")
            return _sports_cache[cache_key]

    print(f"[cache] MISS sports active_only={active_only}")
    sports = list_sports(active_only=active_only)

    with _sports_cache_lock:
        _sports_cache[cache_key] = sports

    return sports
