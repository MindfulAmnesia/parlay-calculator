"""
parlay.py — Joint probability calculator for sports betting parlays.
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
    """Remove the bookmaker's vig from a two-way market."""
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

