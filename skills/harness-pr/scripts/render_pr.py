#!/usr/bin/env python3
"""Validate a Harness pull request and render compact reviewer context."""

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
GOAL_MAX_CHARS = 600
ITEM_MAX_CHARS = 400
SECTION_MAX_ITEMS = 12
BODY_MAX_CHARS = 8_000


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


def clean_item(value: str, section: str) -> str:
    value = value.strip()
    if value.startswith("- "):
        value = value[2:].strip()
    if not value:
        raise ValueError(f"{section} items must not be empty")
    if "\n" in value or "\r" in value:
        raise ValueError(f"{section} items must stay on one line")
    if len(value) > ITEM_MAX_CHARS:
        raise ValueError(
            f"{section} items must be {ITEM_MAX_CHARS} characters or fewer"
        )
    return value


def validate_item_count(values: list[str], section: str) -> None:
    if len(values) > SECTION_MAX_ITEMS:
        raise ValueError(
            f"{section} must contain {SECTION_MAX_ITEMS} items or fewer"
        )


def bullets(values: list[str], section: str) -> str:
    validate_item_count(values, section)
    return "\n".join(f"- {clean_item(value, section)}" for value in values)


def routed_bullets(values: list[str], section: str) -> str:
    validate_item_count(values, section)
    rendered: list[str] = []
    for value in values:
        item = clean_item(value, section)
        target, separator, description = item.partition("=")
        target = target.strip()
        description = description.strip()
        if not separator or not target or not description:
            raise ValueError(f"{section} items must use target=description")
        if "`" in target:
            raise ValueError(f"{section} targets must not contain backticks")
        rendered.append(f"- `{target}`: {description}")
    return "\n".join(rendered)


def render_body(args: argparse.Namespace) -> str:
    goal = args.goal.strip()
    if not goal:
        raise ValueError("goal must not be empty")
    if "\n" in goal or "\r" in goal:
        raise ValueError("goal must be one paragraph")
    if len(goal) > GOAL_MAX_CHARS:
        raise ValueError(f"goal must be {GOAL_MAX_CHARS} characters or fewer")
    body = (
        f"## Goal\n\n{goal}\n\n"
        f"## Desired behavior\n\n{bullets(args.behavior, 'behavior')}\n\n"
        f"## Change map\n\n{routed_bullets(args.change, 'change')}\n\n"
        f"## Verification\n\n{bullets(args.verification, 'verification')}\n\n"
        f"## Review focus\n\n{routed_bullets(args.review, 'review')}\n\n"
        f"## Risks\n\n{bullets(args.risk, 'risk')}\n"
    )
    if len(body) > BODY_MAX_CHARS:
        raise ValueError(f"body must be {BODY_MAX_CHARS} characters or fewer")
    return body


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--branch",
        default="",
        help="Optional head task branch; validates semantic naming and title alignment",
    )
    parser.add_argument("--title", required=True)
    parser.add_argument(
        "--goal",
        "--summary",
        dest="goal",
        required=True,
        help="One-paragraph outcome; --summary remains a compatibility alias",
    )
    parser.add_argument("--behavior", action="append", required=True)
    parser.add_argument(
        "--change",
        action="append",
        required=True,
        help="Changed path or area and responsibility as target=description",
    )
    parser.add_argument("--verification", action="append", required=True)
    parser.add_argument(
        "--review",
        action="append",
        required=True,
        help="Review target and question or risk as target=description",
    )
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
