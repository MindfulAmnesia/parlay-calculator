"""
parlay.py — Joint probability calculator for sports betting parlays.

This module converts American moneyline odds into implied probabilities and
computes the joint probability of a parlay (a wager that pays only if every
leg succeeds).

Notes on the math:
  - American moneyline odds:
        positive odds (+N):  p = 100 / (N + 100)
        negative odds (-N):  p = N / (N + 100)
  - Implied probabilities posted by sportsbooks include the book's margin
    (the "vig"). The two sides of a two-way market sum to more than 1.0;
    the excess is the vig. Dividing each side by the total recovers the
    book's "fair" estimate. We include devig_two_way() for later use when
    we have both sides of a market from the API.
  - parlay_probability() assumes legs are statistically independent. This is
    reasonable for legs across different games, but it OVERSTATES the joint
    probability for Same Game Parlays, where legs are correlated. A
    correlation model is a v2 problem.
"""

# `dataclass` is a Python shortcut for creating simple data-holding classes.
# Instead of writing a bunch of boilerplate, we just list the fields we want.
from dataclasses import dataclass


# @dataclass automatically gives this class an __init__ so we can write:
#   leg = Leg("Team A wins", -200)
# Without @dataclass we'd have to write an __init__ method manually.
@dataclass
class Leg:
    """A single leg of a parlay."""
    # description is the human-readable label for this bet, e.g. "Team A to win"
    description: str
    # american_odds is the moneyline number, e.g. -200 or +150
    american_odds: int


def american_to_implied_probability(american_odds: int) -> float:
    """Convert American moneyline odds to an implied probability in [0, 1]."""
    # American odds come in two flavours:
    #   Positive (+250): the underdog. You risk $100 to win $250.
    #   Negative (-200): the favourite. You risk $200 to win $100.

    if american_odds > 0:
        # For underdogs the formula is: 100 / (odds + 100)
        # Example: +250  →  100 / (250 + 100)  =  100 / 350  ≈  28.6%
        return 100 / (american_odds + 100)
    elif american_odds < 0:
        # For favourites we flip the sign first, then use: odds / (odds + 100)
        # Example: -200  →  200 / (200 + 100)  =  200 / 300  ≈  66.7%
        return -american_odds / (-american_odds + 100)
    else:
        # Odds of exactly 0 are not valid — raise an error to tell the caller.
        raise ValueError("American odds cannot be zero.")


def implied_to_american(probability: float) -> int:
    """Convert an implied probability back to American moneyline odds."""
    # Make sure the probability is a sensible number (must be between 0 and 1,
    # but not exactly 0 or 1, since those would mean "impossible" or "certain").
    if not 0 < probability < 1:
        raise ValueError("Probability must be strictly between 0 and 1.")

    if probability >= 0.5:
        # Favourite (more than 50% chance) → negative odds
        # Formula: round(-100 × p / (1 - p))
        # Example: p=0.667  →  -100 × 0.667 / 0.333  ≈  -200
        return round(-100 * probability / (1 - probability))
    else:
        # Underdog (less than 50% chance) → positive odds
        # Formula: round(100 × (1 - p) / p)
        # Example: p=0.286  →  100 × 0.714 / 0.286  ≈  +250
        return round(100 * (1 - probability) / probability)


def devig_two_way(prob_a: float, prob_b: float) -> tuple[float, float]:
    """Remove the bookmaker's vig from a two-way market.

    Given the implied probabilities of two opposing outcomes (whose sum
    exceeds 1.0 because of the vig), return the fair probabilities that
    sum to exactly 1.0.
    """
    # Add both sides together. If there's a vig, this will be > 1.0.
    # Example: -110 / -110 lines each imply ≈52.38%, so total ≈ 1.0476.
    total = prob_a + prob_b

    if total <= 1:
        # No vig detected — return the values unchanged.
        return prob_a, prob_b

    # Divide each side by the total to scale them back to a sum of 1.0.
    # This is called "normalization" — it's like finding each side's
    # percentage share of the combined total.
    return prob_a / total, prob_b / total


def parlay_probability(legs: list[Leg]) -> float:
    """Joint probability that every leg of the parlay succeeds (independence)."""
    # Start at 1.0 (100%). We'll multiply it by each leg's probability.
    # Multiplying probabilities together is how you find the chance that
    # ALL events happen (assuming they're independent of each other).
    # e.g. 50% × 50% = 25% chance that both coin flips land heads.
    joint = 1.0
    for leg in legs:
        joint *= american_to_implied_probability(leg.american_odds)
    return joint


def main() -> None:
    """Demo using John's three-leg parlay from the project brief."""
    # Build a list of three Leg objects to represent John's parlay.
    johns_parlay = [
        Leg("Team A to win",                       -200),
        Leg("Player A to score a touchdown",       +250),
        Leg("Player B to catch at least 5 passes", +240),
    ]

    # Print a nicely formatted table header.
    # The :<45 and :>6 parts are "format specs" that left- or right-align
    # the text and pad it to a fixed width so columns line up.
    print("John's parlay legs:")
    print(f"{'Description':<45} {'Odds':>6} {'Implied':>10}")
    print("-" * 65)
    for leg in johns_parlay:
        p = american_to_implied_probability(leg.american_odds)
        # :>+6 means right-align, always show the sign (+/-), pad to 6 chars.
        # :>10.4f means right-align, show 4 decimal places.
        print(f"{leg.description:<45} {leg.american_odds:>+6} {p:>10.4f}")

    # Calculate the overall parlay probability and convert it back to odds.
    joint = parlay_probability(johns_parlay)
    payout_odds = implied_to_american(joint)
    print("-" * 65)
    print(f"Joint probability (independence assumed): {joint:.4f}  ({joint*100:.2f}%)")
    print(f"Equivalent American odds:                 {payout_odds:+d}")


# This block only runs when you execute this file directly (python parlay.py).
# If another file imports parlay.py, this block is skipped.
if __name__ == "__main__":
    main()
