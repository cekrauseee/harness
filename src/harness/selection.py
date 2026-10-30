"""Validate an agent's model choice without choosing or ranking models."""

from __future__ import annotations

import re

from .errors import require

FIELDS = ("provider", "model", "effort", "reason")


def validate(value):
    require(
        isinstance(value, dict),
        "invalid_selection",
        "Choose a provider, model, effort, and concise reason for this assignment.",
    )
    require(
        set(value) == set(FIELDS),
        "invalid_selection",
        "A selection contains provider, model, effort, and reason.",
    )
    require(
        value.get("provider") in ("codex", "claude"),
        "invalid_selection",
        "Select a supported provider CLI: codex or claude.",
    )
    for field, maximum in (("model", 128), ("effort", 32)):
        item = value.get(field)
        require(
            isinstance(item, str)
            and 0 < len(item) <= maximum
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]*", item),
            "invalid_selection",
            f"Choose an explicit {field} supported by the selected provider.",
        )
    reason = value.get("reason")
    require(
        isinstance(reason, str) and 0 < len(reason.strip()) <= 2000,
        "invalid_selection",
        "Explain the capability and cost fit in a short selection reason.",
    )
    return dict(value)


def settings(choice, seconds, read_only=False):
    require(type(read_only) is bool, "invalid_selection", "read_only must be a boolean.")
    return dict(validate(choice), seconds=seconds, read_only=read_only)


def public(settings):
    # Existing executions can lack a reason; their chosen models remain inspectable.
    return {key: settings.get(key) for key in FIELDS}
