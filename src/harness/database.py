"""SQLite stores operational truth, never a second copy of human knowledge."""

from __future__ import annotations

import contextlib
import sqlite3

# profile_json retains its storage name for existing executions; it now holds
# the agent's frozen launch settings, without a named-profile lookup.
SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
 id TEXT PRIMARY KEY, environment TEXT NOT NULL, work TEXT, kind TEXT NOT NULL,
 state TEXT NOT NULL, created REAL NOT NULL, deadline REAL NOT NULL,
 limits_json TEXT NOT NULL, definition_json TEXT NOT NULL,
 revision INTEGER NOT NULL DEFAULT 0, supervisor_pid INTEGER, supervisor_identity TEXT,
 reason TEXT, authorization TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS participants (
 id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id), module TEXT NOT NULL,
 role TEXT NOT NULL, profile_json TEXT NOT NULL, context_json TEXT NOT NULL,
 cwd TEXT NOT NULL, state TEXT NOT NULL, token_hash TEXT NOT NULL,
 prompt TEXT NOT NULL, rounds INTEGER NOT NULL DEFAULT 0,
 parent_id TEXT REFERENCES participants(id), next_state TEXT
);
CREATE TABLE IF NOT EXISTS attempts (
 id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id), participant_id TEXT NOT NULL REFERENCES participants(id),
 state TEXT NOT NULL, created REAL NOT NULL, started REAL, ended REAL,
 pid INTEGER, identity TEXT, deadline REAL NOT NULL, exit_code INTEGER,
 reason TEXT, output_path TEXT NOT NULL, usage_json TEXT
);
CREATE TABLE IF NOT EXISTS decisions (
 id INTEGER PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id), participant_id TEXT,
 event TEXT NOT NULL, target TEXT, reason TEXT NOT NULL, created REAL NOT NULL, revision INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
 id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id), sender TEXT NOT NULL,
 recipient TEXT NOT NULL, body TEXT NOT NULL, created REAL NOT NULL,
 notified REAL, read_at REAL, acknowledged REAL
);
CREATE INDEX IF NOT EXISTS messages_inbox ON messages(run_id, recipient, created);
CREATE INDEX IF NOT EXISTS attempts_run ON attempts(run_id, state);
PRAGMA user_version = 1;
"""


class Connection(sqlite3.Connection):
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()


def connect(home):
    home.ensure()
    db = sqlite3.connect(
        home.path / "state.sqlite", timeout=15, isolation_level=None, factory=Connection
    )
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=15000")
    version = db.execute("PRAGMA user_version").fetchone()[0]
    if version not in (0, 1):
        from .errors import HarnessError

        db.close()
        raise HarnessError("unsupported_version", "Unsupported operational database version.")
    if version == 0:
        db.execute("PRAGMA journal_mode=WAL")
        db.executescript(SCHEMA)
    return db


@contextlib.contextmanager
def transaction(db):
    db.execute("BEGIN IMMEDIATE")
    try:
        yield db
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise
