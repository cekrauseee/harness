#!/usr/bin/env python3
"""Resolve Harness branch semantics without choosing or creating a worktree."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import unicodedata


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
SAFE_BRANCH_RE = re.compile(r"^[a-z0-9][a-z0-9._/-]*[a-z0-9]$|^[a-z0-9]$")


class ResolutionError(ValueError):
    pass


def run_git(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(project), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def slugify(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
    slug = re.sub(r"-+", "-", slug)
    if not slug:
        raise ResolutionError("slug must contain at least one ASCII letter or digit")
    if len(slug) > 64:
        raise ResolutionError("slug must be 64 characters or fewer")
    return slug


def validate_branch_name(branch: str) -> None:
    if not SAFE_BRANCH_RE.fullmatch(branch):
        raise ResolutionError(f"unsafe branch name: {branch}")
    forbidden = ("..", "@{", "//", "\\", " ", "~", "^", ":", "?", "*", "[")
    if any(part in branch for part in forbidden) or branch.endswith(("/", ".", ".lock")):
        raise ResolutionError(f"unsafe branch name: {branch}")


def branch_exists(project: Path, branch: str) -> bool:
    result = run_git(project, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}")
    return result.returncode == 0


def valid_commit(project: Path, revision: str) -> bool:
    return run_git(
        project,
        "rev-parse",
        "--verify",
        "--quiet",
        f"{revision}^{{commit}}",
    ).returncode == 0


def resolve_base(project: Path, explicit: str | None) -> str:
    if explicit:
        validate_branch_name(explicit)
        if not valid_commit(project, explicit):
            raise ResolutionError(f"base revision does not resolve to a commit: {explicit}")
        return explicit
    remote_head = run_git(
        project,
        "symbolic-ref",
        "--quiet",
        "--short",
        "refs/remotes/origin/HEAD",
    )
    current = run_git(project, "symbolic-ref", "--quiet", "--short", "HEAD")
    candidates = [remote_head.stdout.strip(), current.stdout.strip(), "main", "master", "trunk"]
    for candidate in candidates:
        if candidate and valid_commit(project, candidate):
            return candidate
    raise ResolutionError("could not derive a valid base revision")


def resolve(args: argparse.Namespace) -> dict[str, object]:
    project = Path(args.project).expanduser().resolve()
    if run_git(project, "rev-parse", "--show-toplevel").returncode:
        raise ResolutionError(f"not a Git repository: {project}")
    base = resolve_base(project, args.base)
    slug = slugify(args.slug)
    branch = f"{args.type}/{slug}"
    validate_branch_name(branch)
    exists_branch = branch_exists(project, branch)

    if args.require_available and exists_branch:
        raise ResolutionError(f"branch {branch!r} already exists")

    return {
        "type": args.type,
        "slug": slug,
        "branch": branch,
        "base": base,
        "branch_exists": exists_branch,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=".", help="Repository checkout used for resolution")
    parser.add_argument("--type", required=True, choices=ALLOWED_TYPES)
    parser.add_argument("--slug", required=True, help="Short task description; normalized to kebab-case")
    parser.add_argument("--base", help="Planned base revision; derived from the repository when omitted")
    parser.add_argument(
        "--require-available",
        action="store_true",
        help="Fail when the planned local branch already exists",
    )
    return parser.parse_args()


def main() -> int:
    try:
        print(json.dumps(resolve(parse_args()), indent=2, sort_keys=True))
        return 0
    except (OSError, ResolutionError) as error:
        print(json.dumps({"ok": False, "errors": [str(error)]}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
