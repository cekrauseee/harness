#!/usr/bin/env python3
"""Resolve a Harness worktree plan without mutating Git or the filesystem."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unicodedata
import uuid


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
SHORT_ID_RE = re.compile(r"^[a-z0-9]{4,12}$")
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


def resolve_project_id(project: Path, explicit: str | None, harness_home: Path) -> str:
    project_id = explicit or os.environ.get("HARNESS_PROJECT_ID")
    if not project_id and project.exists():
        result = run_git(project, "config", "--local", "--get", "harness.project-id")
        if result.returncode == 0:
            project_id = result.stdout.strip()
    if not project_id:
        raise ResolutionError(
            "project ID is unavailable; pass --project-id or initialize/link Harness first"
        )
    try:
        project_id = str(uuid.UUID(project_id))
    except ValueError as exc:
        raise ResolutionError("project ID must be an opaque UUID") from exc
    if not (harness_home / "projects" / project_id / "manifest.json").is_file():
        raise ResolutionError("Harness project container does not exist")
    return project_id


def branch_exists(project: Path, branch: str) -> bool:
    if not project.exists():
        return False
    result = run_git(project, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}")
    return result.returncode == 0


def valid_commit(project: Path, revision: str) -> bool:
    return run_git(project, "rev-parse", "--verify", "--quiet", f"{revision}^{{commit}}").returncode == 0


def resolve_base(project: Path, explicit: str | None) -> str:
    if explicit:
        validate_branch_name(explicit)
        if not valid_commit(project, explicit):
            raise ResolutionError(f"base revision does not resolve to a commit: {explicit}")
        return explicit
    remote_head = run_git(project, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
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
    harness_home = Path(
        args.harness_home or os.environ.get("HARNESS_HOME", "~/.harness")
    ).expanduser().resolve()
    project_id = resolve_project_id(project, args.project_id, harness_home)
    base = resolve_base(project, args.base)
    slug = slugify(args.slug)
    branch = f"{args.type}/{slug}"
    validate_branch_name(branch)

    short_id = args.short_id or hashlib.sha256(
        f"{project_id}\0{branch}".encode("utf-8")
    ).hexdigest()[:8]
    if not SHORT_ID_RE.fullmatch(short_id):
        raise ResolutionError("short ID must contain 4-12 lowercase letters or digits")

    worktree_id = f"{args.type}-{slug}-{short_id}"
    path = harness_home / "projects" / project_id / "worktrees" / worktree_id
    exists_branch = branch_exists(project, branch)
    exists_path = path.exists()

    if args.require_available and (exists_branch or exists_path):
        collisions = []
        if exists_branch:
            collisions.append(f"branch {branch!r}")
        if exists_path:
            collisions.append(f"path {str(path)!r}")
        raise ResolutionError("worktree plan collides with existing " + " and ".join(collisions))

    return {
        "project_id": project_id,
        "type": args.type,
        "slug": slug,
        "branch": branch,
        "path": str(path),
        "base": base,
        "worktree_id": worktree_id,
        "branch_exists": exists_branch,
        "path_exists": exists_path,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=".", help="Repository checkout used for resolution")
    parser.add_argument("--project-id", help="Harness project ID; otherwise resolve from Git config")
    parser.add_argument("--type", required=True, choices=ALLOWED_TYPES)
    parser.add_argument("--slug", required=True, help="Short task description; normalized to kebab-case")
    parser.add_argument("--base", help="Planned base revision; derived from the repository when omitted")
    parser.add_argument("--short-id", help="Stable directory suffix; derived when omitted")
    parser.add_argument("--harness-home", help="Override HARNESS_HOME")
    parser.add_argument(
        "--require-available",
        action="store_true",
        help="Fail when the planned branch or path already exists",
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
