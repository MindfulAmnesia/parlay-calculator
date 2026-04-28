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

from dataclasses import dataclass


@dataclass
class Leg:
    """A single leg of a parlay."""
    description: str
    american_odds: int


def american_to_implied_probability(american_odds: int) -> float:
    """Convert American moneyline odds to an implied probability in [0, 1]."""
    if american_odds > 0:
        return 100 / (american_odds + 100)
    elif american_odds < 0:
        return -american_odds / (-american_odds + 100)
    else:
        raise ValueError("American odds cannot be zero.")


def implied_to_american(probability: float) -> int:
    """Convert an implied probability back to American moneyline odds."""
    if not 0 < probability < 1:
        raise ValueError("Probability must be strictly between 0 and 1.")
    if probability >= 0.5:
        return round(-100 * probability / (1 - probability))
    else:
        return round(100 * (1 - probability) / probability)


def devig_two_way(prob_a: float, prob_b: float) -> tuple[float, float]:
    """Remove the bookmaker's vig from a two-way market.

    Given the implied probabilities of two opposing outcomes (whose sum
    exceeds 1.0 because of the vig), return the fair probabilities that
    sum to exactly 1.0.
    """
    total = prob_a + prob_b
    if total <= 1:
        return prob_a, prob_b
    return prob_a / total, prob_b / total


def parlay_probability(legs: list[Leg]) -> float:
    """Joint probability that every leg of the parlay succeeds (independence)."""
    joint = 1.0
    for leg in legs:
        joint *= american_to_implied_probability(leg.american_odds)
    return joint


def main() -> None:
    """Demo using John's three-leg parlay from the project brief."""
    johns_parlay = [
        Leg("Team A to win",                       -200),
        Leg("Player A to score a touchdown",       +250),
        Leg("Player B to catch at least 5 passes", +240),
    ]

    print("John's parlay legs:")
    print(f"{'Description':<45} {'Odds':>6} {'Implied':>10}")
    print("-" * 65)
    for leg in johns_parlay:
        p = american_to_implied_probability(leg.american_odds)
        print(f"{leg.description:<45} {leg.american_odds:>+6} {p:>10.4f}")

    joint = parlay_probability(johns_parlay)
    payout_odds = implied_to_american(joint)
    print("-" * 65)
    print(f"Joint probability (independence assumed): {joint:.4f}  ({joint*100:.2f}%)")
    print(f"Equivalent American odds:                 {payout_odds:+d}")


if __name__ == "__main__":
    main()
    