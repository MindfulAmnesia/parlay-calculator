"""Tests for main.py FastAPI service. Uses TestClient — no real HTTP server."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from main import app
from odds_client import OddsAPIError

client = TestClient(app)


# A sample Odds-API-shaped event used by /odds tests
SAMPLE_EVENT = {
    "id": "abc123",
    "home_team": "Yankees",
    "away_team": "Red Sox",
    "commence_time": "2026-05-08T19:00:00Z",
    "bookmakers": [
        {
            "key": "draftkings",
            "markets": [{
                "key": "h2h",
                "outcomes": [
                    {"name": "Yankees", "price": -150},
                    {"name": "Red Sox", "price":  130},
                ],
            }],
        },
        {
            "key": "fanduel",
            "markets": [{
                "key": "h2h",
                "outcomes": [
                    {"name": "Yankees", "price": -145},
                    {"name": "Red Sox", "price":  125},
                ],
            }],
        },
    ],
}


# --- GET / ----------------------------------------------------------------

def test_root_returns_friendly_message():
    response = client.get("/")
    assert response.status_code == 200
    assert "Parlay Calculator API" in response.json()["message"]


# --- GET /sports ----------------------------------------------------------

@patch("main.list_sports")
def test_get_sports_returns_list(mock_list_sports):
    mock_list_sports.return_value = [
        {"key": "basketball_nba", "active": True, "title": "NBA"},
        {"key": "baseball_mlb",   "active": True, "title": "MLB"},
    ]
    response = client.get("/sports")
    assert response.status_code == 200
    sports = response.json()
    assert len(sports) == 2
    assert sports[0]["key"] == "basketball_nba"


@patch("main.list_sports")
def test_get_sports_handles_upstream_error(mock_list_sports):
    mock_list_sports.side_effect = OddsAPIError("Upstream API timed out")
    response = client.get("/sports")
    assert response.status_code == 502
    assert "Upstream API timed out" in response.json()["detail"]


# --- GET /odds/{sport_key} ------------------------------------------------

@patch("main.get_moneyline_odds")
def test_get_odds_consensus(mock_get_moneyline_odds):
    mock_get_moneyline_odds.return_value = [SAMPLE_EVENT]
    response = client.get("/odds/baseball_mlb")
    assert response.status_code == 200
    event = response.json()[0]
    assert event["source"] == "consensus"
    assert event["home_team"] == "Yankees"
    # Yankees prices from two books: -150 and -145; median is -147.5,
    # int() in Python truncates toward zero, yielding -147.
    assert event["prices"]["Yankees"] == -147


@patch("main.get_moneyline_odds")
def test_get_odds_specific_book(mock_get_moneyline_odds):
    mock_get_moneyline_odds.return_value = [SAMPLE_EVENT]
    response = client.get("/odds/baseball_mlb?book=draftkings")
    assert response.status_code == 200
    event = response.json()[0]
    assert event["source"] == "draftkings"
    assert event["prices"]["Yankees"] == -150


@patch("main.get_moneyline_odds")
def test_get_odds_unknown_book_returns_empty_prices(mock_get_moneyline_odds):
    mock_get_moneyline_odds.return_value = [SAMPLE_EVENT]
    response = client.get("/odds/baseball_mlb?book=nonexistent")
    assert response.status_code == 200
    event = response.json()[0]
    assert event["source"] == "nonexistent"
    assert event["prices"] == {}


# --- POST /parlay ---------------------------------------------------------

def test_post_parlay_three_favorites_raw_only():
    body = {
        "legs": [
            {"description": "Yankees ML",  "american_odds": -150},
            {"description": "Dodgers ML",  "american_odds": -120},
            {"description": "Phillies ML", "american_odds": -140},
        ]
    }
    response = client.post("/parlay", json=body)
    assert response.status_code == 200
    data = response.json()
    assert data["leg_count"] == 3
    # 0.6 * 0.5455 * 0.5833 = 0.1909
    assert data["raw_probability"] == pytest.approx(0.1909, abs=0.001)
    assert data["fair_probability"] is None


def test_post_parlay_with_devig_returns_fair():
    body = {
        "legs": [
            {"description": "Yankees ML",  "american_odds": -150, "opposite_odds": 130},
            {"description": "Dodgers ML",  "american_odds": -120, "opposite_odds": 100},
            {"description": "Phillies ML", "american_odds": -140, "opposite_odds": 120},
        ]
    }
    response = client.post("/parlay", json=body)
    assert response.status_code == 200
    data = response.json()
    assert data["fair_probability"] is not None
    # De-vigging removes the book's margin, so fair < raw.
    assert data["fair_probability"] < data["raw_probability"]


def test_post_parlay_empty_legs_returns_400():
    response = client.post("/parlay", json={"legs": []})
    assert response.status_code == 400


def test_post_parlay_invalid_input_returns_422():
    # Missing required field 'american_odds' — Pydantic should reject.
    response = client.post("/parlay", json={"legs": [{"description": "no odds field"}]})
    assert response.status_code == 422
    