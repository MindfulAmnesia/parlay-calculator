"""
db.py — PostgreSQL data access for the parlay calculator.
"""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime

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
    user_id: int,
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
                    (user_id, sport_key, book,
                     raw_probability_at_save, fair_probability_at_save)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (user_id, sport_key, book, raw_probability, fair_probability),
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


def load_parlay(parlay_id: int, user_id: int) -> dict | None:
    """Load a parlay by ID, but only if it belongs to user_id.

    Returns None if it doesn't exist OR isn't owned by this user — so a user
    can never read another user's parlay, and can't even tell it exists.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, created_at, sport_key, book,
                       raw_probability_at_save, fair_probability_at_save
                FROM parlays
                WHERE id = %s AND user_id = %s
                """,
                (parlay_id, user_id),
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


def list_parlays(user_id: int, limit: int = 50) -> list[dict]:
    """List a single user's recent parlays, newest first, without leg details."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, created_at, sport_key, book,
                       raw_probability_at_save, fair_probability_at_save
                FROM parlays
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id, limit),
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


# ---------- Users & sessions (authentication) ----------

def create_user(email: str, password_hash: str) -> dict:
    """Insert a new user. Returns the safe user record (no password hash)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (email, password_hash)
                VALUES (%s, %s)
                RETURNING id, email, tier, created_at
                """,
                (email, password_hash),
            )
            row = cur.fetchone()
            assert row is not None
        conn.commit()
    return {
        "id": row[0],
        "email": row[1],
        "tier": row[2],
        "created_at": row[3].isoformat() if row[3] else None,
    }


def get_user_by_email(email: str) -> dict | None:
    """Look up a user by email (case-insensitive). Includes password_hash
    because the login flow needs it to verify. Returns None if not found."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, email, password_hash, tier, created_at
                FROM users
                WHERE LOWER(email) = LOWER(%s)
                """,
                (email,),
            )
            row = cur.fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "email": row[1],
        "password_hash": row[2],
        "tier": row[3],
        "created_at": row[4].isoformat() if row[4] else None,
    }


def get_user_by_id(user_id: int) -> dict | None:
    """Look up a user by ID. Safe fields only (no password hash)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, email, tier, created_at
                FROM users
                WHERE id = %s
                """,
                (user_id,),
            )
            row = cur.fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "email": row[1],
        "tier": row[2],
        "created_at": row[3].isoformat() if row[3] else None,
    }


def create_session(user_id: int, token_hash: str, expires_at: datetime) -> None:
    """Store a new session row (the hashed token, not the raw token)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO sessions (user_id, token_hash, expires_at)
                VALUES (%s, %s, %s)
                """,
                (user_id, token_hash, expires_at),
            )
        conn.commit()


def get_session_user(token_hash: str) -> dict | None:
    """Return the user owning a valid, unexpired session, else None.
    Safe fields only (no password hash)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.id, u.email, u.tier, u.created_at
                FROM sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.token_hash = %s AND s.expires_at > NOW()
                """,
                (token_hash,),
            )
            row = cur.fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "email": row[1],
        "tier": row[2],
        "created_at": row[3].isoformat() if row[3] else None,
    }


def delete_session(token_hash: str) -> None:
    """Delete a session by its token hash (logout). Idempotent."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM sessions WHERE token_hash = %s",
                (token_hash,),
            )
        conn.commit()
        