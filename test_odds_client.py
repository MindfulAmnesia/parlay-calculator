"""Tests for odds_client.py using mocks — no real API calls."""

from unittest.mock import MagicMock, patch

import pytest

from odds_client import (
    OddsAPIError,
    book_moneyline,
    consensus_moneyline,
    get_odds,
    list_sports,
)


def fake_response(json_data, status_code=200, headers=None):
    """Build a MagicMock that quacks like a requests.Response object."""
    response = MagicMock()
    response.status_code = status_code
    response.reason = "OK" if status_code == 200 else "Error"
    response.headers = headers or {}
    response.json.return_value = json_data
    response.text = str(json_data)
    return response


# --- list_sports ----------------------------------------------------------

@patch("odds_client.requests.get")
def test_list_sports_filters_active_by_default(mock_get):
    mock_get.return_value = fake_response([
        {"key": "basketball_nba", "active": True, "title": "NBA"},
        {"key": "icehockey_nhl",  "active": False, "title": "NHL"},
    ])
    sports = list_sports()
    assert len(sports) == 1
    assert sports[0]["key"] == "basketball_nba"


@patch("odds_client.requests.get")
def test_list_sports_can_include_inactive(mock_get):
    mock_get.return_value = fake_response([
        {"key": "basketball_nba", "active": True},
        {"key": "icehockey_nhl",  "active": False},
    ])
    sports = list_sports(active_only=False)
    assert len(sports) == 2


# --- get_odds -------------------------------------------------------------

@patch("odds_client.requests.get")
def test_get_odds_sends_correct_params(mock_get):
    mock_get.return_value = fake_response([])
    get_odds("baseball_mlb", markets=["h2h", "spreads"], regions="us")

    # Inspect what get_odds actually sent to requests.get
    params = mock_get.call_args.kwargs["params"]
    assert params["markets"] == "h2h,spreads"
    assert params["regions"] == "us"
    assert params["oddsFormat"] == "american"


@patch("odds_client.requests.get")
def test_get_odds_defaults_to_h2h_only(mock_get):
    mock_get.return_value = fake_response([])
    get_odds("baseball_mlb")
    assert mock_get.call_args.kwargs["params"]["markets"] == "h2h"


# --- Error handling -------------------------------------------------------

@patch("odds_client.requests.get")
def test_non_200_response_raises_odds_api_error(mock_get):
    mock_get.return_value = fake_response({"message": "bad key"}, status_code=401)
    with pytest.raises(OddsAPIError):
        list_sports()


# --- book_moneyline (pure function, no mocking needed) --------------------

def test_book_moneyline_extracts_one_book_prices():
    event = {
        "bookmakers": [
            {
                "key": "draftkings",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Yankees", "price": -150},
                            {"name": "Red Sox", "price":  130},
                        ],
                    }
                ],
            }
        ]
    }
    assert book_moneyline(event, "draftkings") == {"Yankees": -150, "Red Sox": 130}


def test_book_moneyline_missing_book_returns_empty():
    event = {"bookmakers": [{"key": "fanduel", "markets": []}]}
    assert book_moneyline(event, "draftkings") == {}


# --- consensus_moneyline (pure function) ----------------------------------

def test_consensus_moneyline_returns_median_across_books():
    event = {
        "bookmakers": [
            {"markets": [{"key": "h2h", "outcomes": [
                {"name": "A", "price":  100}, {"name": "B", "price": -120},
            ]}]},
            {"markets": [{"key": "h2h", "outcomes": [
                {"name": "A", "price":  110}, {"name": "B", "price": -125},
            ]}]},
            {"markets": [{"key": "h2h", "outcomes": [
                {"name": "A", "price":  105}, {"name": "B", "price": -110},
            ]}]},
        ]
    }
    result = consensus_moneyline(event)
    assert result["A"] == 105   # median of [100, 110, 105]
    assert result["B"] == -120  # median of [-120, -125, -110]