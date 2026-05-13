"""Tests for parlay.py. Run with:  pytest -v"""

# pytest is the testing framework — it finds functions starting with "test_"
# and runs them automatically, reporting which pass and which fail.
import pytest

# Import everything from parlay.py that we want to test.
from parlay import (
    Leg,
    american_to_implied_probability,
    devig_two_way,
    implied_to_american,
    parlay_probability,
)

# ── Tests for american_to_implied_probability ─────────────────────────────────
# Each function below is a single test case. pytest finds them because their
# names start with "test_".


def test_negative_odds_favorite():
    # -200 means "risk $200 to win $100" — a favourite.
    # The implied probability formula: 200 / (200 + 100) = 200/300 = 2/3 ≈ 66.7%
    # pytest.approx() allows for tiny floating-point rounding differences.
    # Without it, 0.6666... != 0.6666... could fail due to decimal precision.
    assert american_to_implied_probability(-200) == pytest.approx(2 / 3)


def test_positive_odds_underdog():
    # +250 means "risk $100 to win $250" — an underdog.
    # Implied probability: 100 / (250 + 100) = 100/350 ≈ 28.6%
    assert american_to_implied_probability(+250) == pytest.approx(100 / 350)


def test_pickem_at_plus_100():
    # +100 is a "pick'em" — both sides are equally likely.
    # Implied probability: 100 / (100 + 100) = 0.5 = 50%
    assert american_to_implied_probability(+100) == pytest.approx(0.5)


def test_zero_odds_raises():
    # Passing 0 should raise a ValueError because 0 is not valid American odds.
    # pytest.raises(ValueError) means: this test PASSES only if a ValueError
    # is raised inside the `with` block. If no error is raised, the test fails.
    with pytest.raises(ValueError):
        american_to_implied_probability(0)


# ── Tests for implied_to_american ─────────────────────────────────────────────


def test_round_trip_favorite():
    # Converting 2/3 → American odds should give -200.
    # This is the "inverse" of the favourite formula.
    assert implied_to_american(2 / 3) == -200


def test_round_trip_underdog():
    # Converting 100/350 → American odds should give +250.
    assert implied_to_american(100 / 350) == +250


def test_invalid_probability_raises():
    # Probability must be strictly between 0 and 1.
    # 0 means "impossible" and 1 means "certain" — neither can be expressed
    # as finite American odds, so we raise a ValueError for both.
    with pytest.raises(ValueError):
        implied_to_american(0)
    with pytest.raises(ValueError):
        implied_to_american(1)


# ── Tests for devig_two_way ───────────────────────────────────────────────────


def test_devig_normalizes_to_one():
    # -110 / -110 is the standard NFL spread line.
    # Each side implies: 110 / (110 + 100) ≈ 52.38%
    # Together: ≈ 104.76% — the excess is the sportsbook's vig (profit margin).
    # After de-vigging, both sides should be exactly 50%.
    p = american_to_implied_probability(-110)
    fair_a, fair_b = devig_two_way(p, p)
    assert fair_a == pytest.approx(0.5)
    assert fair_b == pytest.approx(0.5)
    # The two fair probabilities must add up to exactly 1.0 (100%).
    assert fair_a + fair_b == pytest.approx(1.0)


def test_devig_passthrough_when_no_vig():
    # If the inputs already sum to ≤ 1.0, there's no vig to remove.
    # The function should return the values unchanged.
    assert devig_two_way(0.4, 0.5) == (0.4, 0.5)


# ── Tests for parlay_probability ──────────────────────────────────────────────


def test_johns_three_leg_parlay():
    # Build the same three-leg parlay used in parlay.py's demo.
    legs = [
        Leg("Team A to win", -200),
        Leg("Player A to score a touchdown", +250),
        Leg("Player B to catch at least 5 passes", +240),
    ]
    # Calculate the expected result by hand:
    #   -200 → 2/3       +250 → 100/350      +240 → 100/340
    # Joint probability = (2/3) × (100/350) × (100/340)
    expected = (2 / 3) * (100 / 350) * (100 / 340)
    assert parlay_probability(legs) == pytest.approx(expected)


def test_empty_parlay_is_certain():
    # An empty parlay (no legs) has a joint probability of 1.0.
    # Mathematically, the product of zero numbers is the "empty product" = 1.
    # This is a valid edge case even if you'd never actually bet on it.
    assert parlay_probability([]) == 1.0
