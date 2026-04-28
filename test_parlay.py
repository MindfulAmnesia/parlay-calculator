"""Tests for parlay.py. Run with:  pytest -v"""

import pytest

from parlay import (
    Leg,
    american_to_implied_probability,
    implied_to_american,
    devig_two_way,
    parlay_probability,
)


# --- american_to_implied_probability ---------------------------------------

def test_negative_odds_favorite():
    # -200 means "risk 200 to win 100" -> implied probability 200/300
    assert american_to_implied_probability(-200) == pytest.approx(2 / 3)


def test_positive_odds_underdog():
    # +250 means "risk 100 to win 250" -> implied probability 100/350
    assert american_to_implied_probability(+250) == pytest.approx(100 / 350)


def test_pickem_at_plus_100():
    assert american_to_implied_probability(+100) == pytest.approx(0.5)


def test_zero_odds_raises():
    with pytest.raises(ValueError):
        american_to_implied_probability(0)


# --- implied_to_american ---------------------------------------------------

def test_round_trip_favorite():
    assert implied_to_american(2 / 3) == -200


def test_round_trip_underdog():
    assert implied_to_american(100 / 350) == +250


def test_invalid_probability_raises():
    with pytest.raises(ValueError):
        implied_to_american(0)
    with pytest.raises(ValueError):
        implied_to_american(1)


# --- devig_two_way ---------------------------------------------------------

def test_devig_normalizes_to_one():
    # Two -110 lines: each side implies 0.5238, sum is ~1.0476 (the vig)
    p = american_to_implied_probability(-110)
    fair_a, fair_b = devig_two_way(p, p)
    assert fair_a == pytest.approx(0.5)
    assert fair_b == pytest.approx(0.5)
    assert fair_a + fair_b == pytest.approx(1.0)


def test_devig_passthrough_when_no_vig():
    # If the inputs already sum to <= 1, we return them unchanged.
    assert devig_two_way(0.4, 0.5) == (0.4, 0.5)


# --- parlay_probability ----------------------------------------------------

def test_johns_three_leg_parlay():
    legs = [
        Leg("Team A to win",                       -200),
        Leg("Player A to score a touchdown",       +250),
        Leg("Player B to catch at least 5 passes", +240),
    ]
    # (2/3) * (100/350) * (100/340)
    expected = (2 / 3) * (100 / 350) * (100 / 340)
    assert parlay_probability(legs) == pytest.approx(expected)


def test_empty_parlay_is_certain():
    # Multiplying zero probabilities together yields the identity, 1.0.
    # That's mathematically correct, even if it's a weird edge case.
    assert parlay_probability([]) == 1.0