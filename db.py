"""
db.py — PostgreSQL data access for the parlay calculator.
"""

import os
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://amnesia@localhost:5432/parlay_dev"
)


@contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    """Yield a database connection, closing it on exit."""
    conn = psycopg.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()


def save_parlay(
    legs: list[dict],
    sport_key: str | None = None,
    book: str | None = None,
    raw_probability: float | None = None,
    fair_probability: float | None = None,
) -> int:
    """Save a parlay and its legs atomically. Returns the new parlay ID."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO parlays
                    (sport_key, book, raw_probability_at_save, fair_probability_at_save)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (sport_key, book, raw_probability, fair_probability),
            )
            row = cur.fetchone()
            assert row is not None
            parlay_id = row[0]

            for leg in legs:
                cur.execute(
                    """
                    INSERT INTO parlay_legs
                        (parlay_id, description, american_odds, opposite_odds)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        parlay_id,
                        leg["description"],
                        leg["american_odds"],
                        leg.get("opposite_odds"),
                    ),
                )
        conn.commit()
        return parlay_id


def load_parlay(parlay_id: int) -> dict | None:
    """Load a parlay by ID, including its legs. Returns None if not found."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, created_at, sport_key, book,
                       raw_probability_at_save, fair_probability_at_save
                FROM parlays
                WHERE id = %s
                """,
                (parlay_id,),
            )
            parlay_row = cur.fetchone()
            if parlay_row is None:
                return None

            cur.execute(
                """
                SELECT description, american_odds, opposite_odds
                FROM parlay_legs
                WHERE parlay_id = %s
                ORDER BY id
                """,
                (parlay_id,),
            )
            leg_rows = cur.fetchall()

    return {
        "id": parlay_row[0],
        "created_at": parlay_row[1].isoformat() if parlay_row[1] else None,
        "sport_key": parlay_row[2],
        "book": parlay_row[3],
        "raw_probability_at_save": (
            float(parlay_row[4]) if parlay_row[4] is not None else None
        ),
        "fair_probability_at_save": (
            float(parlay_row[5]) if parlay_row[5] is not None else None
        ),
        "legs": [
            {
                "description": r[0],
                "american_odds": r[1],
                "opposite_odds": r[2],
            }
            for r in leg_rows
        ],
    }


def list_parlays(limit: int = 50) -> list[dict]:
    """List recent parlays, newest first, without leg details."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, created_at, sport_key, book,
                       raw_probability_at_save, fair_probability_at_save
                FROM parlays
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()

    return [
        {
            "id": r[0],
            "created_at": r[1].isoformat() if r[1] else None,
            "sport_key": r[2],
            "book": r[3],
            "raw_probability_at_save": float(r[4]) if r[4] is not None else None,
            "fair_probability_at_save": float(r[5]) if r[5] is not None else None,
        }
        for r in rows
    ]
