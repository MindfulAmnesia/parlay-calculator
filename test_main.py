"""Tests for main.py FastAPI service. Uses TestClient — no real HTTP server."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from main import app
from odds_client import OddsAPIError

client = TestClient(app)


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


def test_root_returns_friendly_message():
    response = client.get("/")
    assert response.status_code == 200
    assert "Parlay Calculator API" in response.json()["message"]


@patch("main.list_sports_cached")
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


@patch("main.list_sports_cached")
def test_get_sports_handles_upstream_error(mock_list_sports):
    mock_list_sports.side_effect = OddsAPIError("Upstream API timed out")
    response = client.get("/sports")
    assert response.status_code == 502
    assert "Upstream API timed out" in response.json()["detail"]


@patch("main.get_odds_cached")
def test_get_odds_consensus(mock_get_odds_cached):
    mock_get_odds_cached.return_value = [SAMPLE_EVENT]
    response = client.get("/odds/baseball_mlb")
    assert response.status_code == 200
    event = response.json()[0]
    assert event["source"] == "consensus"
    assert event["home_team"] == "Yankees"
    assert event["prices"]["Yankees"] == -147


@patch("main.get_odds_cached")
def test_get_odds_specific_book(mock_get_odds_cached):
    mock_get_odds_cached.return_value = [SAMPLE_EVENT]
    response = client.get("/odds/baseball_mlb?book=draftkings")
    assert response.status_code == 200
    event = response.json()[0]
    assert event["source"] == "draftkings"
    assert event["prices"]["Yankees"] == -150


@patch("main.get_odds_cached")
def test_get_odds_unknown_book_returns_empty_prices(mock_get_odds_cached):
    mock_get_odds_cached.return_value = [SAMPLE_EVENT]
    response = client.get("/odds/baseball_mlb?book=nonexistent")
    assert response.status_code == 200
    event = response.json()[0]
    assert event["source"] == "nonexistent"
    assert event["prices"] == {}


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
    assert data["fair_probability"] < data["raw_probability"]


def test_post_parlay_empty_legs_returns_400():
    response = client.post("/parlay", json={"legs": []})
    assert response.status_code == 400


def test_post_parlay_invalid_input_returns_422():
    response = client.post("/parlay", json={"legs": [{"description": "no odds"}]})
    assert response.status_code == 422


@patch("main.db_save_parlay")
def test_post_parlay_save_returns_id_and_probabilities(mock_save):
    mock_save.return_value = 42
    body = {
        "legs": [
            {"description": "Yankees ML", "american_odds": -150},
            {"description": "Dodgers ML", "american_odds": -120},
        ],
        "sport_key": "baseball_mlb",
        "book": "draftkings",
    }
    response = client.post("/parlay/save", json=body)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 42
    assert data["raw_probability"] > 0
    call_kwargs = mock_save.call_args.kwargs
    assert call_kwargs["sport_key"] == "baseball_mlb"
    assert call_kwargs["book"] == "draftkings"
    assert len(call_kwargs["legs"]) == 2


def test_post_parlay_save_empty_returns_400():
    response = client.post("/parlay/save", json={"legs": []})
    assert response.status_code == 400


@patch("main.db_load_parlay")
def test_get_parlay_returns_full_parlay(mock_load):
    mock_load.return_value = {
        "id": 1,
        "created_at": "2026-05-13T14:00:00-05:00",
        "sport_key": "baseball_mlb",
        "book": "draftkings",
        "raw_probability_at_save": 0.5,
        "fair_probability_at_save": 0.48,
        "legs": [
            {"description": "Test Leg", "american_odds": -150, "opposite_odds": None}
        ],
    }
    response = client.get("/parlay/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["sport_key"] == "baseball_mlb"
    assert len(data["legs"]) == 1


@patch("main.db_load_parlay")
def test_get_parlay_not_found_returns_404(mock_load):
    mock_load.return_value = None
    response = client.get("/parlay/9999")
    assert response.status_code == 404


@patch("main.db_list_parlays")
def test_get_parlays_returns_list(mock_list):
    mock_list.return_value = [
        {
            "id": 1,
            "created_at": "2026-05-13T14:00:00-05:00",
            "sport_key": "baseball_mlb",
            "book": "draftkings",
            "raw_probability_at_save": 0.5,
            "fair_probability_at_save": 0.48,
        },
    ]
    response = client.get("/parlays")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == 1
    