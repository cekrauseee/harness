"""Bind managed operations to a participant; the OS user remains trusted."""

from __future__ import annotations

import hashlib
import hmac
import json
import os

from .database import connect
from .errors import require


def digest(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


class Actor:
    def __init__(self, participant, run):
        self.participant = dict(participant)
        self.run = dict(run)
        self.id = participant["id"]

    @classmethod
    def current(cls, home):
        values = [
            os.environ.get(k) for k in ("HARNESS_RUN", "HARNESS_ACTOR", "HARNESS_ACTOR_TOKEN")
        ]
        if not any(values):
            return None
        require(all(values), "invalid_identity", "Managed execution identity is incomplete.")
        run_id, actor_id, token = values
        with connect(home) as db:
            participant = db.execute(
                "SELECT * FROM participants WHERE id=? AND run_id=?", (actor_id, run_id)
            ).fetchone()
            require(
                participant is not None
                and hmac.compare_digest(participant["token_hash"], digest(token)),
                "invalid_identity",
                "Managed execution identity could not be verified.",
            )
            run = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        return cls(participant, run)

    def check_run(self, run_id):
        require(
            self.run["id"] == run_id,
            "scope_denied",
            "This execution is outside the participant's scope.",
        )

    def check_write(self):
        require(
            not json.loads(self.participant["profile_json"]).get("read_only"),
            "scope_denied",
            "This assignment has read-only context access.",
        )

    def check_record(self, relative, write=False):
        if write:
            self.check_write()
        env = self.run["environment"]
        baseline = ["memory/", f"environments/{env}/memory/", f"environments/{env}/environment.md"]
        if self.run["work"]:
            baseline.append(f"environments/{env}/work/{self.run['work']}/work.md")
            baseline.append(f"environments/{env}/work/{self.run['work']}/artifacts/{self.id}/")
        allowed = baseline + json.loads(self.participant["context_json"])
        require(
            any(relative.startswith(p) if p.endswith("/") else relative == p for p in allowed),
            "scope_denied",
            "This record is outside the assigned context.",
            "Request the missing context from the parent.",
        )


def operator_only(actor):
    require(actor is None, "scope_denied", "This operation belongs to the supervising operator.")
