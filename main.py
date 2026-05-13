"""
main.py — FastAPI HTTP service exposing the parlay calculator.

Run locally with:
    uvicorn main:app --reload

Then open http://localhost:8000/docs for the interactive API docs.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from odds_client import (
    OddsAPIError,
    book_moneyline,
    consensus_moneyline,
    get_moneyline_odds,
    list_sports,
)
from parlay import (
    american_to_implied_probability,
    devig_two_way,
    implied_to_american,
)

app = FastAPI(
    title="Parlay Calculator API",
    description="Live joint probability for sports betting parlays.",
    version="0.1.0",
)


# ---------- Pydantic models for /parlay ----------


class ParlayLeg(BaseModel):
    """One leg of a parlay."""

    description: str = Field(..., description="Human-readable name, e.g. 'Yankees ML'")
    american_odds: int = Field(..., description="American moneyline, e.g. -150 or +250")
    opposite_odds: int | None = Field(
        None,
        description="The opposing side's odds, for de-vigging. Optional.",
    )


class ParlayRequest(BaseModel):
    """Request body for POST /parlay."""

    legs: list[ParlayLeg]


class ParlayResponse(BaseModel):
    """Response body for POST /parlay."""

    leg_count: int
    raw_probability: float
    raw_american_odds: int
    fair_probability: float | None = None
    fair_american_odds: int | None = None
    legs: list[ParlayLeg]


# ---------- Routes ----------


@app.get("/")
def root() -> dict:
    """Health check / friendly greeting."""
    return {"message": "Parlay Calculator API is running. See /docs for the API."}


@app.get("/sports")
def get_sports() -> list[dict]:
    """List active sports the Odds API tracks. Free — no quota cost."""
    try:
        return list_sports()
    except OddsAPIError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@app.get("/odds/{sport_key}")
def get_event_odds(sport_key: str, book: str | None = None) -> list[dict]:
    """Fetch live moneyline odds for all events in a sport.

    Costs 1 quota credit on the Odds API per call.

    - If `book` is provided (e.g. ?book=draftkings), only that book's
      prices are returned for each event.
    - Otherwise the consensus (median across all books) is returned.
    """
    try:
        events = get_moneyline_odds(sport_key)
    except OddsAPIError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    output = []
    for event in events:
        if book:
            prices = book_moneyline(event, book.lower())
        else:
            prices = {name: int(price) for name, price in consensus_moneyline(event).items()}
        output.append(
            {
                "id": event.get("id"),
                "home_team": event.get("home_team"),
                "away_team": event.get("away_team"),
                "commence_time": event.get("commence_time"),
                "prices": prices,
                "source": book.lower() if book else "consensus",
            }
        )
    return output


@app.post("/parlay")
def calculate_parlay(request: ParlayRequest) -> ParlayResponse:
    """Compute the joint probability of a parlay.

    Costs zero quota — this is pure math, no Odds API call.

    - `raw_probability` multiplies implied probabilities directly
      (vig included). This is what a sportsbook's quoted odds imply.
    - `fair_probability` is included when every leg supplies
      `opposite_odds`; it de-vigs each leg and returns the result.
    """
    if not request.legs:
        raise HTTPException(status_code=400, detail="Parlay must contain at least one leg.")

    raw = 1.0
    for leg in request.legs:
        raw *= american_to_implied_probability(leg.american_odds)

    fair: float | None = None
    if all(leg.opposite_odds is not None for leg in request.legs):
        fair = 1.0
        for leg in request.legs:
            own_p = american_to_implied_probability(leg.american_odds)
            assert leg.opposite_odds is not None
            opp_p = american_to_implied_probability(leg.opposite_odds)
            fair *= devig_two_way(own_p, opp_p)[0]

    return ParlayResponse(
        leg_count=len(request.legs),
        raw_probability=raw,
        raw_american_odds=implied_to_american(raw),
        fair_probability=fair,
        fair_american_odds=implied_to_american(fair) if fair is not None else None,
        legs=request.legs,
    )
