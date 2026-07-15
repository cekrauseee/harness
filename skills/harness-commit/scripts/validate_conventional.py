#!/usr/bin/env python3
"""Validate Harness Conventional Commit messages and branch names."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


ALLOWED_TYPES = (
    "feat",
    "fix",
    "docs",
    "refactor",
    "perf",
    "test",
    "build",
    "ci",
    "style",
    "chore",
    "revert",
)
TYPE_PATTERN = "|".join(ALLOWED_TYPES)
HEADER_RE = re.compile(
    rf"^(?P<type>{TYPE_PATTERN})(?:\((?P<scope>[a-z0-9][a-z0-9.-]*)\))?"
    r"(?P<breaking>!)?: (?P<description>.+)$"
)
BRANCH_RE = re.compile(
    rf"^(?P<type>{TYPE_PATTERN})/(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)$"
)


def validate_message(message: str) -> list[str]:
    errors: list[str] = []
    if not message:
        return ["message is empty"]
    if not message.isascii():
        errors.append("message must use ASCII text")

    lines = message.splitlines()
    header = lines[0].strip() if lines else ""
    if len(header) > 72:
        errors.append("header must be 72 characters or fewer")
    match = HEADER_RE.fullmatch(header)
    if not match:
        errors.append(
            "header must match type(optional-scope)(optional-!): description using an allowed type"
        )
    else:
        description = match.group("description")
        first_alpha = next((char for char in description if char.isalpha()), None)
        if first_alpha and not first_alpha.islower():
            errors.append("description must start with lowercase text")
        if description.endswith("."):
            errors.append("description must not end with a period")
        if description != description.strip() or "  " in description:
            errors.append("description must not contain leading, trailing, or repeated spaces")

    if len(lines) > 1 and lines[1].strip():
        errors.append("body must be separated from the header by a blank line")
    return errors


def validate_branch(branch: str) -> list[str]:
    if not branch:
        return []
    errors: list[str] = []
    if not branch.isascii():
        errors.append("branch must use ASCII text")
    if not BRANCH_RE.fullmatch(branch):
        errors.append("branch must match allowed-type/short-kebab-case-slug")
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--message", help="Commit message to validate")
    source.add_argument("--message-file", type=Path, help="File containing the commit message")
    parser.add_argument("--branch", default="", help="Optional Harness branch to validate")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        message = args.message if args.message is not None else args.message_file.read_text()
    except OSError as error:
        print(str(error), file=sys.stderr)
        return 2

    errors = validate_message(message.rstrip("\n")) + validate_branch(args.branch)
    result = {"ok": not errors, "errors": errors}
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    elif errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
    else:
        print("valid")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
