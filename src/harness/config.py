"""Small configuration contracts; unknown fields survive tool updates."""

from __future__ import annotations

import copy
import os
from pathlib import Path

from .errors import require
from .files import locked, read_json, write_json

LIMITS = {
    "seconds": 3600,
    "attempt_seconds": 1200,
    "concurrency": 2,
    "max_attempts": 12,
    "max_rounds": 3,
}


def defaults():
    profiles = {}
    for provider, models in {
        "codex": ("gpt-6-luna", "gpt-6.1-sol", "gpt-6-astra"),
        "claude": ("haiku", "sonnet", "opus"),
    }.items():
        for role, model, effort in zip(
            ("scout", "worker", "coordinator"), models, ("low", "medium", "high")
        ):
            profiles[f"{provider}-{role}"] = {
                "provider": provider,
                "model": model,
                "effort": effort,
                "autonomous": role == "scout",
                "read_only": role == "scout",
                "seconds": 180 if role == "scout" else 1200,
            }
    return {
        "version": 1,
        "profiles": profiles,
        "defaults": {role: f"codex-{role}" for role in ("scout", "worker", "coordinator")},
        "limits": copy.deepcopy(LIMITS),
    }


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
        config = read_json(self.path / "config.json")
        require(
            config is not None,
            "not_initialized",
            "Harness has not been prepared.",
            "Run harness setup.",
        )
        require(
            isinstance(config, dict), "invalid_config", "Harness configuration must be an object."
        )
        require(
            config.get("version") == 1,
            "unsupported_version",
            "Unsupported Harness configuration version.",
        )
        require(
            isinstance(config.get("profiles"), dict) and isinstance(config.get("defaults"), dict),
            "invalid_config",
            "Configuration needs profiles and defaults objects.",
        )
        validate_limits(config.get("limits"))
        return config

    def profile(self, name: str, config=None):
        require(isinstance(name, str), "invalid_profile", "A profile name must be a string.")
        value = (config or self.config())["profiles"].get(name)
        require(value is not None, "unknown_profile", f"Unknown profile: {name}.")
        validate_profile(value)
        return copy.deepcopy(value)

    def set_profile(self, name: str, value):
        from .files import identifier

        identifier(name)
        validate_profile(value)
        self.ensure()
        with locked(self.path, "config.json"):
            config = self.config()
            config["profiles"][name] = value
            write_json(self.path / "config.json", config)
        return {"profile": name, "settings": value}


def validate_profile(value):
    require(isinstance(value, dict), "invalid_profile", "A profile must be a JSON object.")
    require(
        value.get("provider") in ("codex", "claude"),
        "invalid_profile",
        "Provider must be codex or claude.",
    )
    require(
        isinstance(value.get("model"), str) and bool(value["model"].strip()),
        "invalid_profile",
        "A profile needs an explicit model.",
    )
    require(
        value.get("effort") in ("low", "medium", "high", "xhigh", "max"),
        "invalid_profile",
        "Unsupported reasoning effort.",
    )
    require(
        type(value.get("seconds")) is int and 1 <= value["seconds"] <= 86400,
        "invalid_profile",
        "Profile seconds must be between 1 and 86400.",
    )
    require(
        isinstance(value.get("autonomous", False), bool)
        and isinstance(value.get("read_only", False), bool),
        "invalid_profile",
        "Profile permission fields must be booleans.",
    )


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
