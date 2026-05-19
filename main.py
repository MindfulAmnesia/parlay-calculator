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
    book_moneyline,
    book_spreads,
    book_totals,
    consensus_moneyline,
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
    version="0.2.0",
)

# Comma-separated list of permitted frontend origins.
# Local dev defaults to localhost:3000; production sets this via env var.
_frontend_urls_env = os.getenv("FRONTEND_URLS", "http://localhost:3000")
_allow_origins = [u.strip() for u in _frontend_urls_env.split(",") if u.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
