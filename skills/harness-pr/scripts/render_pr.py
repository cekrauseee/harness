#!/usr/bin/env python3
"""Validate a Harness pull request title and render its standard body."""

from __future__ import annotations

import argparse
import json
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
TITLE_RE = re.compile(
    rf"^(?P<type>{'|'.join(ALLOWED_TYPES)})(?:\([a-z0-9][a-z0-9.-]*\))?!?: (?P<description>.+)$"
)
BRANCH_RE = re.compile(
    rf"^(?P<type>{'|'.join(ALLOWED_TYPES)})/(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)$"
)


def validate_title(title: str) -> list[str]:
    errors: list[str] = []
    if not title.isascii():
        errors.append("title must use ASCII text")
    if len(title) > 72:
        errors.append("title must be 72 characters or fewer")
    match = TITLE_RE.fullmatch(title)
    if not match:
        errors.append(
            "title must match type(optional-scope)(optional-!): description using an allowed type"
        )
        return errors
    description = match.group("description")
    first_alpha = next((char for char in description if char.isalpha()), None)
    if first_alpha and not first_alpha.islower():
        errors.append("description must start with lowercase text")
    if description.endswith("."):
        errors.append("description must not end with a period")
    if description != description.strip() or "  " in description:
        errors.append("description must not contain leading, trailing, or repeated spaces")
    return errors


def validate_branch(title: str, branch: str) -> list[str]:
    if not branch:
        return []
    errors: list[str] = []
    if not branch.isascii():
        errors.append("branch must use ASCII text")
    branch_match = BRANCH_RE.fullmatch(branch)
    if not branch_match:
        errors.append(
            "branch must match allowed-type/short-kebab-case-slug; "
            "host, agent, user, and machine prefixes are not allowed"
        )
        return errors
    title_match = TITLE_RE.fullmatch(title)
    if title_match and title_match.group("type") != branch_match.group("type"):
        errors.append("pull request title type must match head branch type")
    return errors


def clean_item(value: str) -> str:
    value = value.strip()
    if value.startswith("- "):
        value = value[2:].strip()
    if not value:
        raise ValueError("list items must not be empty")
    return value


def bullets(values: list[str]) -> str:
    return "\n".join(f"- {clean_item(value)}" for value in values)


def render_body(args: argparse.Namespace) -> str:
    summary = args.summary.strip()
    if not summary:
        raise ValueError("summary must not be empty")
    return (
        f"## Summary\n\n{summary}\n\n"
        f"## Changes\n\n{bullets(args.change)}\n\n"
        f"## Verification\n\n{bullets(args.verification)}\n\n"
        f"## Risks\n\n{bullets(args.risk)}\n"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--branch",
        default="",
        help="Optional head task branch; validates semantic naming and title alignment",
    )
    parser.add_argument("--title", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--change", action="append", required=True)
    parser.add_argument("--verification", action="append", required=True)
    parser.add_argument("--risk", action="append", required=True)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = validate_title(args.title) + validate_branch(args.title, args.branch)
    try:
        body = render_body(args)
    except ValueError as error:
        errors.append(str(error))
        body = ""
    if errors:
        if args.format == "json":
            print(json.dumps({"ok": False, "errors": errors}, indent=2, sort_keys=True))
        else:
            for error in errors:
                print(f"error: {error}", file=sys.stderr)
        return 1

    if args.format == "json":
        payload = {"ok": True, "title": args.title, "body": body}
        if args.branch:
            payload["branch"] = args.branch
        print(json.dumps(payload, indent=2))
    else:
        print(body, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
