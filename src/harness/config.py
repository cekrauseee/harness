"""Small configuration contracts; unknown fields survive tool updates."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path

from .errors import require
from .files import locked, revision, write_json

LIMITS = {
    "seconds": 3600,
    "attempt_seconds": 1200,
    "concurrency": 2,
    "max_attempts": 12,
    "max_rounds": 3,
}


def defaults():
    return {"version": 1, "limits": copy.deepcopy(LIMITS)}


class Home:
    def __init__(self, root: str | Path | None = None):
        self.path = (
            Path(root or os.environ.get("HARNESS_ROOT", "~/.harness")).expanduser().resolve()
        )

    def ensure(self):
        self.path.mkdir(parents=True, exist_ok=True, mode=0o700)
        with locked(self.path, "config.json"):
            if not (self.path / "config.json").exists():
                write_json(self.path / "config.json", defaults())
        return self

    def config(self):
        return self.config_record()["settings"]

    def config_record(self):
        path = self.path / "config.json"
        require(
            path.is_file(),
            "not_initialized",
            "Harness has not been prepared.",
            "Run harness setup.",
        )
        data = path.read_bytes()
        config = json.loads(data)
        validate_config(config)
        return {"settings": config, "revision": revision(data)}

    def write_config(self, value, expected):
        validate_config(value)
        require(
            not {"profiles", "defaults"}.intersection(value),
            "obsolete_config",
            "Model profiles and role defaults are obsolete. Supply model choices at launch.",
        )
        self.ensure()
        with locked(self.path, "config.json"):
            path = self.path / "config.json"
            require(
                revision(path.read_bytes()) == expected,
                "conflict",
                "Configuration changed. Read its current revision before writing.",
            )
            write_json(path, value)
            return {"settings": value, "revision": revision(path.read_bytes())}


def validate_config(value):
    require(isinstance(value, dict), "invalid_config", "Harness configuration must be an object.")
    require(
        value.get("version") == 1,
        "unsupported_version",
        "Unsupported Harness configuration version.",
    )
    validate_limits(value.get("limits"))


def validate_limits(value):
    require(isinstance(value, dict), "invalid_limits", "Limits must be a JSON object.")
    for key in LIMITS:
        require(
            type(value.get(key)) is int and value[key] > 0,
            "invalid_limits",
            f"{key} must be a positive integer.",
        )
    require(
        value["seconds"] <= 86400 and value["attempt_seconds"] <= value["seconds"],
        "invalid_limits",
        "Execution duration is at most 24 hours; an attempt must fit its duration.",
    )
    require(
        value["concurrency"] <= 32 and value["max_attempts"] <= 1000 and value["max_rounds"] <= 100,
        "invalid_limits",
        "The configured execution limits exceed supported bounds.",
    )
    return value
