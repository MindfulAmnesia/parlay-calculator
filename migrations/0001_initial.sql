-- Initial schema for parlay storage; migrations/0001_initial.sql

CREATE TABLE IF NOT EXISTS parlays 
    (
    id                          SERIAL PRIMARY KEY,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sport_key                   TEXT,
    book                        TEXT,
    raw_probability_at_save     NUMERIC(8, 7),
    fair_probability_at_save    NUMERIC(8, 7)
    );

CREATE TABLE IF NOT EXISTS parlay_legs 
    (
    id              SERIAL PRIMARY KEY,
    parlay_id       INTEGER NOT NULL REFERENCES parlays(id) ON DELETE CASCADE,
    description     TEXT NOT NULL,
    american_odds   INTEGER NOT NULL,
    opposite_odds   INTEGER
    );

-- Index for the most common query: "Find All Legs for a Given Parlay."

CREATE INDEX IF NOT EXISTS idx_parlay_legs_parlay_id
    ON parlay_legs (parlay_id);