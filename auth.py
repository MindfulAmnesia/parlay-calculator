"""
auth.py — Password hashing and session-token primitives.

Security choices:
- Passwords are hashed with bcrypt (deliberately slow, individually salted)
  and never stored in plaintext.
- Session tokens are random 256-bit values. Only their SHA-256 hash is
  stored, so a database leak cannot be replayed to impersonate a user.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt

SESSION_TTL_DAYS = 30


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt. Returns a storable string."""
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Check a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"), password_hash.encode("utf-8")
        )
    except ValueError:
        return False


def generate_session_token() -> str:
    """Return a cryptographically strong, URL-safe session token.

    This is the raw value handed to the client; it is never stored as-is.
    """
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """SHA-256 a session token for storage and lookup."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def session_expiry() -> datetime:
    """Expiry timestamp for a newly created session."""
    return datetime.now(UTC) + timedelta(days=SESSION_TTL_DAYS)

