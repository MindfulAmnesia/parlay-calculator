/**
 * parlay-math.ts — TypeScript port of parlay.py math functions.
 * Mirrors the Python implementation for instant client-side computation.
 */

export function americanToImpliedProbability(odds: number): number {
  if (odds === 0) {
    throw new Error("Invalid odds: 0");
  }
  if (odds > 0) {
    return 100 / (odds + 100);
  }
  return -odds / (-odds + 100);
}

export function impliedToAmerican(p: number): number {
  if (p <= 0 || p >= 1) {
    throw new Error(`Invalid probability: ${p}`);
  }
  if (p < 0.5) {
    return Math.round(100 / p - 100);
  }
  return Math.round(-((p * 100) / (1 - p)));
}

export function devigTwoWay(ownP: number, oppP: number): [number, number] {
  const total = ownP + oppP;
  return [ownP / total, oppP / total];
}

export interface ParlayMathLeg {
  americanOdds: number;
  oppositeOdds?: number;
}

export function parlayProbability(legs: ParlayMathLeg[]): {
  raw: number;
  fair: number | null;
} {
  let raw = 1;
  for (const leg of legs) {
    raw *= americanToImpliedProbability(leg.americanOdds);
  }

  let fair: number | null = null;
  if (legs.length > 0 && legs.every((l) => l.oppositeOdds !== undefined)) {
    fair = 1;
    for (const leg of legs) {
      const own = americanToImpliedProbability(leg.americanOdds);
      const opp = americanToImpliedProbability(leg.oppositeOdds!);
      fair *= devigTwoWay(own, opp)[0];
    }
  }

  return { raw, fair };
}

/**
 * Calculate the vig (bookmaker's margin) on a two-way moneyline.
 * Returns the excess over 100% as a fraction (0.0348 = 3.48% vig),
 * or null if prices aren't a valid two-way market.
 */
export function calculateVig(prices: Record<string, number>): number | null {
  const values = Object.values(prices);
  if (values.length !== 2) return null;
  const sum = values.reduce(
    (acc, odds) => acc + americanToImpliedProbability(odds),
    0,
  );
  return sum - 1;
}
