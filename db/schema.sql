-- ---------------------------------------------------------------------------
-- SCAM JOSE PAUL — SQLite schema (Stage 0)
--
-- This is the additive migration target for the existing JSON save file.
-- Everything here is CREATE ... IF NOT EXISTS, so running it against an
-- existing database never destroys player data.
--
-- The JSON save is NEVER deleted or rewritten by db/migrate.py.
-- ---------------------------------------------------------------------------

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- Records which schema revisions have been applied, so future migrations can
-- upgrade old databases in order without resetting anyone's progress.
CREATE TABLE IF NOT EXISTS schema_migrations (
    version    INTEGER PRIMARY KEY,
    applied_at REAL NOT NULL
);

-- ---------------------------------------------------------------------------
-- Accounts
-- password_hash keeps the existing "salt$sha256hex" format from
-- game_core.hash_password so old logins keep working unchanged.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    username      TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    created_at    REAL NOT NULL,
    last_active   REAL
);

-- ---------------------------------------------------------------------------
-- Per-player state
-- profile_json holds the full legacy profile dict verbatim (inventory, bank,
-- pets, loans, daily streaks...). A few hot fields are promoted to columns for
-- querying, but the JSON blob stays the source of truth during migration.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS player_state (
    username     TEXT PRIMARY KEY REFERENCES users(username) ON DELETE CASCADE,
    current_city TEXT,
    character_id TEXT,
    level        INTEGER NOT NULL DEFAULT 1,
    xp           INTEGER NOT NULL DEFAULT 0,
    job          TEXT,
    profile_json TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- Cities / multiplayer rooms (legacy "rooms" in the JSON save)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cities (
    code       TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    host       TEXT,
    preset     TEXT,
    is_public  INTEGER NOT NULL DEFAULT 0,
    created_at REAL,
    heist_json TEXT
);

CREATE TABLE IF NOT EXISTS city_members (
    city_code TEXT NOT NULL REFERENCES cities(code) ON DELETE CASCADE,
    username  TEXT NOT NULL,
    joined_at REAL,
    PRIMARY KEY (city_code, username)
);

CREATE INDEX IF NOT EXISTS idx_cities_public       ON cities(is_public);
CREATE INDEX IF NOT EXISTS idx_city_members_user   ON city_members(username);
