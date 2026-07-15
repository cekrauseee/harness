#!/usr/bin/env python3
"""Audit global Harness state and optionally rebuild derived memory catalogs."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid


REQUIRED_DIRS = (
    "memory/candidates", "memory/topics", "memory/archive",
    "sessions/active", "sessions/closed", "references/product",
    "references/technical", "references/operations", "references/investigations",
    "workspace", "worktrees",
)
REQUIRED_FILES = ("index.md", "project.md", "decisions.md", "manifest.json", "memory/catalog.jsonl", "workspace/policy.json", "worktrees/policy.toml")


def home() -> Path:
    return Path(os.environ.get("HARNESS_HOME", "~/.harness")).expanduser().resolve()


def atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Git command failed")
    return result.stdout.strip()


def current_project(repo_path: str) -> Path:
    repo = Path(git(Path(repo_path).expanduser().resolve(), "rev-parse", "--show-toplevel")).resolve()
    project_id = git(repo, "config", "--local", "--get", "harness.project-id")
    if not project_id:
        raise RuntimeError("Repository is not linked to Harness")
    project_id = str(uuid.UUID(project_id))
    return home() / "projects" / project_id


def expected_catalog(base: Path, findings: list[dict]) -> str:
    rows: list[dict] = []
    for path in sorted((base / "memory/topics").glob("*/*.json")):
        try:
            item = load(path)
        except (OSError, json.JSONDecodeError) as exc:
            findings.append({"severity": "error", "code": "invalid-json", "path": str(path), "message": str(exc)})
            continue
        if item.get("status") != "active":
            findings.append({"severity": "warning", "code": "inactive-topic-record", "path": str(path), "message": "Non-active memory belongs in archive"})
            continue
        for field in ("last_verified_at", "read_when", "review_after"):
            if not item.get(field):
                findings.append({"severity": "error", "code": "missing-memory-field", "path": str(path), "message": f"Active memory is missing {field}"})
        review_age = age_days(item.get("review_after", ""))
        if review_age is not None and review_age >= 0:
            findings.append({"severity": "warning", "code": "stale-memory", "path": str(path), "message": f"Memory review date passed {review_age} days ago"})
        rows.append({
            "confidence": item.get("confidence", "medium"), "id": item.get("id", ""),
            "last_verified_at": item.get("last_verified_at", ""), "path": str(path.relative_to(base)),
            "read_when": item.get("read_when", ""), "review_after": item.get("review_after", ""),
            "source_session": item.get("source_session", ""),
            "status": "active", "topic": item.get("topic", ""), "updated_at": item.get("updated_at", ""),
        })
    rows.sort(key=lambda row: (row["topic"], row["id"]))
    return "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows)


def age_days(timestamp: str) -> int | None:
    try:
        value = dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return (dt.datetime.now(dt.timezone.utc) - value).days
    except (ValueError, TypeError):
        return None


def audit_project(base: Path, repair_catalog: bool, stale_days: int) -> dict:
    findings: list[dict] = []
    try:
        manifest = load(base / "manifest.json")
        manifest_id = str(uuid.UUID(manifest.get("id", "")))
        if manifest_id != base.name:
            findings.append({"severity": "error", "code": "identity-mismatch", "path": str(base), "message": "Manifest id does not match directory"})
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        manifest = {}
        findings.append({"severity": "error", "code": "invalid-manifest", "path": str(base / "manifest.json"), "message": str(exc)})

    for relative in REQUIRED_DIRS:
        if not (base / relative).is_dir():
            findings.append({"severity": "error", "code": "missing-directory", "path": str(base / relative), "message": "Required directory is missing"})
    for relative in REQUIRED_FILES:
        if not (base / relative).is_file():
            findings.append({"severity": "error", "code": "missing-file", "path": str(base / relative), "message": "Required file is missing"})

    for registered in manifest.get("repository_paths", []):
        repo = Path(registered)
        if not repo.exists():
            findings.append({"severity": "warning", "code": "missing-repository", "path": registered, "message": "Registered repository path no longer exists"})
        for forbidden in (".harness", ".project-harness"):
            if (repo / forbidden).exists():
                findings.append({"severity": "warning", "code": "repository-footprint", "path": str(repo / forbidden), "message": "Harness-owned state must remain global"})

    for area in ("memory/candidates", "memory/archive", "sessions/active", "sessions/closed"):
        for path in sorted((base / area).glob("*.json")):
            try:
                item = load(path)
            except (OSError, json.JSONDecodeError) as exc:
                findings.append({"severity": "error", "code": "invalid-json", "path": str(path), "message": str(exc)})
                continue
            if area == "sessions/active":
                age = age_days(item.get("last_seen_at") or item.get("updated_at", ""))
                if age is None:
                    findings.append({"severity": "error", "code": "invalid-session-time", "path": str(path), "message": "Session timestamp is invalid"})
                elif age >= stale_days:
                    findings.append({"severity": "warning", "code": "stale-session", "path": str(path), "message": f"Session has not been seen for {age} days"})

    workspace = base / "workspace"
    try:
        policy = load(workspace / "policy.json")
        local_policy = workspace / "policy.local.json"
        if local_policy.is_file():
            policy.update(load(local_policy))
        max_age_days = max(1, int(policy.get("max_age_days", 7)))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        max_age_days = 7
        findings.append({"severity": "error", "code": "invalid-workspace-policy", "path": str(workspace / "policy.json"), "message": str(exc)})
    cutoff = dt.datetime.now().timestamp() - max_age_days * 86400
    for path in sorted(workspace.rglob("*")):
        if path in (workspace / "policy.json", workspace / "policy.local.json") or path.is_dir():
            continue
        with contextlib.suppress(OSError):
            if path.stat().st_mtime < cutoff:
                findings.append({"severity": "warning", "code": "expired-workspace-file", "path": str(path), "message": "Workspace file is past the cleanup age"})

    expected = expected_catalog(base, findings)
    catalog = base / "memory/catalog.jsonl"
    actual = catalog.read_text(encoding="utf-8") if catalog.is_file() else ""
    if actual != expected:
        severity = "info" if repair_catalog else "error"
        findings.append({"severity": severity, "code": "catalog-drift", "path": str(catalog), "message": "Catalog was rebuilt" if repair_catalog else "Catalog differs from active topic memory"})
        if repair_catalog:
            atomic_write(catalog, expected)

    lock_path = base / ".lock"
    if lock_path.exists():
        age_seconds = max(0, dt.datetime.now().timestamp() - lock_path.stat().st_mtime)
        if age_seconds > 300:
            findings.append({"severity": "warning", "code": "stale-lock", "path": str(lock_path), "message": "Lock is older than five minutes"})

    counts = {
        "active_memory": len(list((base / "memory/topics").glob("*/*.json"))),
        "active_sessions": len(list((base / "sessions/active").glob("*.json"))),
        "archived_memory": len(list((base / "memory/archive").glob("*.json"))),
        "candidates": len(list((base / "memory/candidates").glob("*.json"))),
    }
    findings.sort(key=lambda item: ({"error": 0, "warning": 1, "info": 2}[item["severity"]], item["code"], item["path"]))
    return {"counts": counts, "findings": findings, "project_id": base.name}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--repo")
    target.add_argument("--all", action="store_true")
    parser.add_argument("--repair-catalog", action="store_true")
    parser.add_argument("--stale-session-days", type=int, default=14)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        bases = sorted((home() / "projects").glob("*")) if args.all else [current_project(args.repo)]
        projects = [audit_project(base, args.repair_catalog, args.stale_session_days) for base in bases if base.is_dir()]
        errors = sum(1 for project in projects for finding in project["findings"] if finding["severity"] == "error")
        result = {"errors": errors, "harness_home": str(home()), "projects": projects}
        print(json.dumps(result, sort_keys=True, ensure_ascii=False) if args.json else json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
        return 1 if errors else 0
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
