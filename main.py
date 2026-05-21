"""
main.py — FastAPI HTTP service exposing the parlay calculator.
"""

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from db import list_parlays as db_list_parlays
from db import load_parlay as db_load_parlay
from db import save_parlay as db_save_parlay
from odds_client import (
    OddsAPIError,
    book_alt_spreads,
    book_alt_totals,
    book_moneyline,
    book_spreads,
    book_totals,
    consensus_moneyline,
    get_event_props_cached,
    get_odds_cached,
    list_sports_cached,
)
from parlay import (
    american_to_implied_probability,
    devig_two_way,
    implied_to_american,
)

app = FastAPI(
    title="Parlay Calculator API",
    description="Live joint probability for sports betting parlays.",
    version="0.5.0",
)

_frontend_urls_env = os.getenv("FRONTEND_URLS", "http://localhost:3000")
_allow_origins = [u.strip() for u in _frontend_urls_env.split(",") if u.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Player-prop market keys, per sport. Each entry costs 1 quota credit per
# region per call. Coverage varies by sport; if the API has no data for a
# given (sport, market) the response simply omits it.
MARKETS_BY_SPORT: dict[str, list[str]] = {
    "baseball_mlb": [
        "batter_hits",
        "batter_home_runs",
        "batter_total_bases",
        "batter_rbis",
        "pitcher_strikeouts",
    ],
    "americanfootball_nfl": [
        "player_pass_yds",
        "player_pass_tds",
        "player_rush_yds",
        "player_reception_yds",
        "player_anytime_td",
    ],
    "basketball_nba": [
        "player_points",
        "player_rebounds",
        "player_assists",
        "player_threes",
    ],
    "icehockey_nhl": [
        "player_goals",
        "player_assists",
        "player_points",
        "player_total_saves",
    ],
}


# Alternate (milestone / "X+") player-prop market keys, per sport. Same base
# markets as above with the API's "_alternate" suffix. Note NFL anytime_td has
# no alternate ladder (it's a yes/no market), so it's omitted here. These are
# fetched on demand only, when a user expands the alternate-lines picker.
ALT_MARKETS_BY_SPORT: dict[str, list[str]] = {
    "baseball_mlb": [
        "batter_hits_alternate",
        "batter_home_runs_alternate",
        "batter_total_bases_alternate",
        "batter_rbis_alternate",
        "pitcher_strikeouts_alternate",
    ],
    "americanfootball_nfl": [
        "player_pass_yds_alternate",
        "player_pass_tds_alternate",
        "player_rush_yds_alternate",
        "player_reception_yds_alternate",
    ],
    "basketball_nba": [
        "player_points_alternate",
        "player_rebounds_alternate",
        "player_assists_alternate",
        "player_threes_alternate",
    ],
    "icehockey_nhl": [
        "player_goals_alternate",
        "player_assists_alternate",
        "player_points_alternate",
        "player_total_saves_alternate",
    ],
}


# ---------- Pydantic models ----------

class ParlayLeg(BaseModel):
    description: str = Field(..., description="Human-readable name, e.g. 'Yankees ML'")
    american_odds: int = Field(..., description="American moneyline, e.g. -150 or +250")
    opposite_odds: int | None = Field(
        None,
        description="The opposing side's odds, for de-vigging. Optional.",
    )


class ParlayRequest(BaseModel):
    legs: list[ParlayLeg]


class ParlayResponse(BaseModel):
    leg_count: int
    raw_probability: float
    raw_american_odds: int
    fair_probability: float | None = None
    fair_american_odds: int | None = None
    legs: list[ParlayLeg]


class SaveParlayRequest(BaseModel):
    legs: list[ParlayLeg]
    sport_key: str | None = None
    book: str | None = None


class SaveParlayResponse(BaseModel):
    id: int
    raw_probability: float
    raw_american_odds: int
    fair_probability: float | None = None
    fair_american_odds: int | None = None


class SavedParlayLeg(BaseModel):
    description: str
    american_odds: int
    opposite_odds: int | None = None


class SavedParlay(BaseModel):
    id: int
    created_at: str
    sport_key: str | None = None
    book: str | None = None
    raw_probability_at_save: float | None = None
    fair_probability_at_save: float | None = None
    legs: list[SavedParlayLeg]


class SavedParlaySummary(BaseModel):
    id: int
    created_at: str
    sport_key: str | None = None
    book: str | None = None
    raw_probability_at_save: float | None = None
    fair_probability_at_save: float | None = None


# ---------- Helpers ----------

def _compute_probabilities(legs: list[ParlayLeg]) -> tuple[float, float | None]:
    raw = 1.0
    for leg in legs:
        raw *= american_to_implied_probability(leg.american_odds)

    fair: float | None = None
    if all(leg.opposite_odds is not None for leg in legs):
        fair = 1.0
        for leg in legs:
            own_p = american_to_implied_probability(leg.american_odds)
            assert leg.opposite_odds is not None
            opp_p = american_to_implied_probability(leg.opposite_odds)
            fair *= devig_two_way(own_p, opp_p)[0]

    return raw, fair


def _merge_lines(main: list[dict], alt: list[dict]) -> list[dict]:
    """Combine featured + alternate lines into one ladder.

    Dedupes by (name, point) so a line that appears in both the featured
    and alternate markets isn't listed twice, then sorts by name and point
    so each team's (or Over/Under's) ladder is in ascending order.
    """
    seen: set[tuple[str, float]] = set()
    combined: list[dict] = []
    for entry in [*main, *alt]:
        key = (entry["name"], entry["point"])
        if key in seen:
            continue
        seen.add(key)
        combined.append(entry)
    combined.sort(key=lambda e: (e["name"], e["point"]))
    return combined


# ---------- Routes ----------

@app.get("/")
def root() -> dict:
    return {"message": "Parlay Calculator API is running. See /docs for the API."}


@app.get("/sports")
def get_sports() -> list[dict]:
    try:
        return list_sports_cached()
    except OddsAPIError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@app.get("/odds/{sport_key}")
def get_event_odds(sport_key: str, book: str | None = None) -> list[dict]:
    try:
        events = get_odds_cached(
            sport_key,
            markets=["h2h", "spreads", "totals"],
        )
    except OddsAPIError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    output = []
    for event in events:
        if book:
            book_lower = book.lower()
            prices = book_moneyline(event, book_lower)
            spreads = book_spreads(event, book_lower)
            totals = book_totals(event, book_lower)
        else:
            prices = {
                name: int(price)
                for name, price in consensus_moneyline(event).items()
            }
            spreads = []
            totals = []

        output.append({
            "id": event.get("id"),
            "home_team": event.get("home_team"),
            "away_team": event.get("away_team"),
            "commence_time": event.get("commence_time"),
            "prices": prices,
            "spreads": spreads,
            "totals": totals,
            "source": book.lower() if book else "consensus",
        })
    return output


@app.get("/odds/{sport_key}/events/{event_id}/props")
def get_event_props_endpoint(
    sport_key: str,
    event_id: str,
    book: str = "draftkings",
) -> dict:
    """Return player-prop outcomes for one specific game.

    Defaults to DraftKings since 'consensus' doesn't apply meaningfully to
    player props (different books may not cover the same players or markets).
    """
    markets = MARKETS_BY_SPORT.get(sport_key, [])
    if not markets:
        raise HTTPException(
            status_code=404,
            detail=f"Player props not configured for sport: {sport_key}",
        )

    try:
        data = get_event_props_cached(
            sport_key,
            event_id,
            markets=markets,
        )
    except OddsAPIError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    book_lower = book.lower()
    available_books: set[str] = set()
    props: list[dict] = []

    for bookmaker in data.get("bookmakers", []):
        book_key = bookmaker.get("key")
        if book_key:
            available_books.add(book_key)

        if book_key != book_lower:
            continue

        for market in bookmaker.get("markets", []):
            market_key = market.get("key", "")
            for outcome in market.get("outcomes", []):
                price = outcome.get("price")
                props.append({
                    "market": market_key,
                    "player": outcome.get("description") or "",
                    "side": outcome.get("name") or "",
                    "price": int(price) if price is not None else None,
                    "point": outcome.get("point"),
                    "book": book_key,
                })

    return {
        "event_id": event_id,
        "sport_key": sport_key,
        "home_team": data.get("home_team"),
        "away_team": data.get("away_team"),
        "commence_time": data.get("commence_time"),
        "book": book_lower,
        "available_books": sorted(available_books),
        "props": props,
    }


@app.get("/odds/{sport_key}/events/{event_id}/alternates")
def get_event_alternates_endpoint(
    sport_key: str,
    event_id: str,
    book: str = "draftkings",
) -> dict:
    """Return the full ladder of spread/total lines for one game.

    Fetches the featured lines (spreads, totals) AND the alternate ladders
    (alternate_spreads, alternate_totals) in a single per-event call, then
    merges them so the user sees the main line plus every published
    alternate as one continuous set of choices.

    On-demand only: called when a user expands a game's line picker, not on
    the main listing — so the extra markets (~4 credits per fresh call, per
    book) are spent only when actually needed. Cached 60s for repeat opens.

    Defaults to DraftKings; 'consensus' doesn't apply to point-bearing
    markets because the points differ across books.
    """
    book_lower = book.lower()

    try:
        # get_event_props_cached is the generic per-event odds fetcher;
        # here we point it at the spread/total markets instead of props.
        data = get_event_props_cached(
            sport_key,
            event_id,
            markets=[
                "spreads",
                "totals",
                "alternate_spreads",
                "alternate_totals",
            ],
        )
    except OddsAPIError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    available_books = sorted(
        b["key"] for b in data.get("bookmakers", []) if b.get("key")
    )

    spreads = _merge_lines(
        book_spreads(data, book_lower),
        book_alt_spreads(data, book_lower),
    )
    totals = _merge_lines(
        book_totals(data, book_lower),
        book_alt_totals(data, book_lower),
    )

    return {
        "event_id": event_id,
        "sport_key": sport_key,
        "home_team": data.get("home_team"),
        "away_team": data.get("away_team"),
        "commence_time": data.get("commence_time"),
        "book": book_lower,
        "available_books": available_books,
        "spreads": spreads,
        "totals": totals,
    }


@app.get("/odds/{sport_key}/events/{event_id}/altprops")
def get_event_alt_props_endpoint(
    sport_key: str,
    event_id: str,
    book: str = "draftkings",
) -> dict:
    """Return alternate / milestone player-prop lines for one game.

    Mirrors the /props endpoint but fetches the '_alternate' market keys
    (e.g. batter_home_runs_alternate) — the milestone ladders books publish
    (1+, 2+, 3+ home runs, each at its own price). On-demand only: called
    when a user expands the alternate-lines picker on the props page.

    The '_alternate' suffix is stripped from each returned market so the
    frontend can reuse the same friendly market names as standard props.
    """
    markets = ALT_MARKETS_BY_SPORT.get(sport_key, [])
    if not markets:
        raise HTTPException(
            status_code=404,
            detail=f"Alternate player props not configured for sport: {sport_key}",
        )

    try:
        data = get_event_props_cached(sport_key, event_id, markets=markets)
    except OddsAPIError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    book_lower = book.lower()
    available_books: set[str] = set()
    props: list[dict] = []
    suffix = "_alternate"

    for bookmaker in data.get("bookmakers", []):
        book_key = bookmaker.get("key")
        if book_key:
            available_books.add(book_key)

        if book_key != book_lower:
            continue

        for market in bookmaker.get("markets", []):
            market_key = market.get("key", "")
            if market_key.endswith(suffix):
                market_key = market_key[: -len(suffix)]
            for outcome in market.get("outcomes", []):
                price = outcome.get("price")
                props.append({
                    "market": market_key,
                    "player": outcome.get("description") or "",
                    "side": outcome.get("name") or "",
                    "price": int(price) if price is not None else None,
                    "point": outcome.get("point"),
                    "book": book_key,
                })

    return {
        "event_id": event_id,
        "sport_key": sport_key,
        "home_team": data.get("home_team"),
        "away_team": data.get("away_team"),
        "commence_time": data.get("commence_time"),
        "book": book_lower,
        "available_books": sorted(available_books),
        "props": props,
    }


@app.post("/parlay")
def calculate_parlay(request: ParlayRequest) -> ParlayResponse:
    if not request.legs:
        raise HTTPException(status_code=400, detail="Parlay must contain at least one leg.")

    raw, fair = _compute_probabilities(request.legs)
    return ParlayResponse(
        leg_count=len(request.legs),
        raw_probability=raw,
        raw_american_odds=implied_to_american(raw),
        fair_probability=fair,
        fair_american_odds=implied_to_american(fair) if fair is not None else None,
        legs=request.legs,
    )


@app.post("/parlay/save", status_code=201)
def post_save_parlay(request: SaveParlayRequest) -> SaveParlayResponse:
    if not request.legs:
        raise HTTPException(status_code=400, detail="Parlay must contain at least one leg.")

    raw, fair = _compute_probabilities(request.legs)
    legs_for_db = [leg.model_dump() for leg in request.legs]
    parlay_id = db_save_parlay(
        legs=legs_for_db,
        sport_key=request.sport_key,
        book=request.book,
        raw_probability=raw,
        fair_probability=fair,
    )

    return SaveParlayResponse(
        id=parlay_id,
        raw_probability=raw,
        raw_american_odds=implied_to_american(raw),
        fair_probability=fair,
        fair_american_odds=implied_to_american(fair) if fair is not None else None,
    )


@app.get("/parlay/{parlay_id}")
def get_parlay(parlay_id: int) -> SavedParlay:
    parlay = db_load_parlay(parlay_id)
    if parlay is None:
        raise HTTPException(status_code=404, detail=f"Parlay {parlay_id} not found.")
    return SavedParlay(**parlay)


@app.get("/parlays")
def get_parlays(limit: int = 50) -> list[SavedParlaySummary]:
    return [SavedParlaySummary(**p) for p in db_list_parlays(limit=limit)]
