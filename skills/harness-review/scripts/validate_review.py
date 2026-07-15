#!/usr/bin/env python3
"""Validate structured Harness review findings without publishing them."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PRIORITIES = {"P0", "P1", "P2", "P3"}
REQUIRED_TEXT = ("title", "file", "evidence", "impact", "direction")


def validate_finding(finding: object, index: int) -> list[str]:
    prefix = f"findings[{index}]"
    if not isinstance(finding, dict):
        return [f"{prefix} must be an object"]
    errors: list[str] = []
    if finding.get("priority") not in PRIORITIES:
        errors.append(f"{prefix}.priority must be P0, P1, P2, or P3")

    for field in REQUIRED_TEXT:
        value = finding.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{prefix}.{field} must be a non-empty string")

    title = finding.get("title")
    if isinstance(title, str) and title.strip():
        if not title.isascii():
            errors.append(f"{prefix}.title must use ASCII text")
        if len(title) > 80:
            errors.append(f"{prefix}.title must be 80 characters or fewer")
        if title.endswith("."):
            errors.append(f"{prefix}.title must not end with a period")
        if title.startswith("["):
            errors.append(f"{prefix}.title must not duplicate the separate priority field")

    start = finding.get("start")
    end = finding.get("end", start)
    if not isinstance(start, int) or start < 1:
        errors.append(f"{prefix}.start must be a positive integer")
    if not isinstance(end, int) or end < 1:
        errors.append(f"{prefix}.end must be a positive integer")
    if isinstance(start, int) and isinstance(end, int):
        if end < start:
            errors.append(f"{prefix}.end must not precede start")
        elif end - start > 10:
            errors.append(f"{prefix} line range must be 11 lines or fewer")
    return errors


def validate_payload(payload: object) -> list[str]:
    findings = payload.get("findings") if isinstance(payload, dict) else payload
    if not isinstance(findings, list):
        return ["payload must be a findings array or an object with a findings array"]
    errors: list[str] = []
    for index, finding in enumerate(findings):
        errors.extend(validate_finding(finding, index))
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, help="JSON file; read stdin when omitted")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        raw = args.path.read_text() if args.path else sys.stdin.read()
        payload = json.loads(raw)
    except (OSError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    errors = validate_payload(payload)
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
