"""Persistent messages with distinct notification, read, and acknowledgment."""

from __future__ import annotations

import time
import uuid

from .database import connect, transaction
from .errors import require


def send(home, run_id, recipient, body, actor=None):
    require(
        0 < len(body.strip()) <= 16000,
        "invalid_message",
        "A message must contain 1–16000 characters.",
    )
    if actor:
        actor.check_run(run_id)
    with connect(home) as db, transaction(db):
        target = db.execute(
            "SELECT id FROM participants WHERE run_id=? AND id=?", (run_id, recipient)
        ).fetchone()
        require(
            target is not None or recipient == "operator",
            "not_found",
            "Message recipient not found in this execution.",
        )
        require(
            db.execute("SELECT id FROM runs WHERE id=?", (run_id,)).fetchone() is not None,
            "not_found",
            "Execution not found.",
        )
        key = "m-" + uuid.uuid4().hex[:16]
        db.execute(
            "INSERT INTO messages(id,run_id,sender,recipient,body,created) VALUES(?,?,?,?,?,?)",
            (key, run_id, actor.id if actor else "operator", recipient, body.strip(), time.time()),
        )
    return {"message": key, "recipient": recipient}


def inbox(home, run_id, recipient=None, actor=None, limit=20, unread=False):
    require(1 <= limit <= 100, "invalid_page", "Read at most 100 message headers at a time.")
    if actor:
        actor.check_run(run_id)
        require(recipient in (None, actor.id), "scope_denied", "Read your own inbox.")
    recipient = actor.id if actor else recipient or "operator"
    with connect(home) as db:
        rows = db.execute(
            "SELECT id,sender,recipient,created,notified,read_at,acknowledged FROM messages WHERE run_id=? AND recipient=?"
            + (" AND read_at IS NULL" if unread else "")
            + " ORDER BY created DESC LIMIT ?",
            (run_id, recipient, limit),
        ).fetchall()
    return {"messages": [dict(row) for row in rows]}


def read(home, message_id, actor=None, acknowledge=False):
    with connect(home) as db, transaction(db):
        row = db.execute("SELECT * FROM messages WHERE id=?", (message_id,)).fetchone()
        require(row is not None, "not_found", "Message not found.")
        if actor:
            actor.check_run(row["run_id"])
            require(
                row["recipient"] == actor.id,
                "scope_denied",
                "This message belongs to another participant.",
            )
        if acknowledge:
            require(
                row["read_at"] is not None, "not_read", "Read the message before acknowledging it."
            )
            db.execute(
                "UPDATE messages SET acknowledged=COALESCE(acknowledged,?) WHERE id=?",
                (time.time(), message_id),
            )
        else:
            db.execute(
                "UPDATE messages SET read_at=COALESCE(read_at,?) WHERE id=?",
                (time.time(), message_id),
            )
        result = dict(db.execute("SELECT * FROM messages WHERE id=?", (message_id,)).fetchone())
    result["authority"] = "context_only"
    return result


def notifications(home, actor):
    now = time.time()
    with connect(home) as db, transaction(db):
        rows = db.execute(
            "SELECT id FROM messages WHERE run_id=? AND recipient=? AND read_at IS NULL AND (notified IS NULL OR notified<?) ORDER BY created LIMIT 5",
            (actor.run["id"], actor.id, now - 60),
        ).fetchall()
        for row in rows:
            db.execute("UPDATE messages SET notified=? WHERE id=?", (now, row["id"]))
    return [row["id"] for row in rows]
