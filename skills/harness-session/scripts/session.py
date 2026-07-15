#!/usr/bin/env python3
"""Manage concise Harness work sessions."""

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
import time
from typing import Iterator
import uuid


def home() -> Path:
    return Path(os.environ.get("HARNESS_HOME", "~/.harness")).expanduser().resolve()


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


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


def write_json(path: Path, value: object) -> None:
    atomic_write(path, json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Invalid Harness session: {path}") from exc


@contextlib.contextmanager
def lock(path: Path, timeout: float = 5.0) -> Iterator[None]:
    deadline = time.monotonic() + timeout
    while True:
        try:
            path.mkdir(parents=True)
            atomic_write(path / "owner", f"{os.getpid()} {time.time()}\n")
            break
        except FileExistsError:
            try:
                if time.time() - path.stat().st_mtime > 300:
                    for child in path.iterdir():
                        child.unlink()
                    path.rmdir()
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise RuntimeError(f"Timed out waiting for Harness lock: {path}")
            time.sleep(0.05)
    try:
        yield
    finally:
        with contextlib.suppress(FileNotFoundError):
            for child in path.iterdir():
                child.unlink()
            path.rmdir()


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Git command failed")
    return result.stdout.strip()


def resolve(repo_path: str) -> tuple[str, Path]:
    root = Path(git(Path(repo_path).expanduser().resolve(), "rev-parse", "--show-toplevel")).resolve()
    project_id = git(root, "config", "--local", "--get", "harness.project-id")
    if not project_id:
        raise RuntimeError("Repository is not linked to Harness; run harness-init")
    try:
        project_id = str(uuid.UUID(project_id))
    except ValueError as exc:
        raise RuntimeError("Repository has an invalid Harness project id") from exc
    base = home() / "projects" / project_id
    if not (base / "manifest.json").is_file():
        raise RuntimeError("Harness project does not exist; run harness-init")
    return project_id, base


def session_id(value: str | None = None) -> str:
    try:
        return str(uuid.UUID(value)) if value else str(uuid.uuid4())
    except ValueError as exc:
        raise RuntimeError(f"Invalid session id: {value}") from exc


def bounded(value: str, limit: int, field: str) -> str:
    value = value.strip()
    if len(value) > limit:
        raise RuntimeError(f"{field} exceeds {limit} characters")
    return value


def start(base: Path, args: argparse.Namespace) -> dict:
    identifier = session_id(args.session_id)
    path = base / "sessions/active" / f"{identifier}.json"
    item = {
        "branch": bounded(args.branch, 250, "branch"),
        "created_at": now(),
        "host": bounded(args.host, 80, "host"),
        "id": identifier,
        "last_seen_at": now(),
        "next_step": "",
        "status": "active",
        "summary": "",
        "task": bounded(args.task, 500, "task"),
        "updated_at": now(),
        "worktree": bounded(args.worktree, 1000, "worktree"),
    }
    if not item["task"]:
        raise RuntimeError("Task cannot be empty")
    with lock(base / ".lock"):
        if path.exists():
            existing = load(path)
            if existing["task"] == item["task"]:
                return existing
            raise RuntimeError(f"Active session already exists: {identifier}")
        write_json(path, item)
    return item


def update(base: Path, args: argparse.Namespace, close: bool = False) -> dict:
    identifier = session_id(args.session_id)
    active = base / "sessions/active" / f"{identifier}.json"
    with lock(base / ".lock"):
        item = load(active)
        if args.summary is not None:
            item["summary"] = bounded(args.summary, 4000, "summary")
        if args.next_step is not None:
            item["next_step"] = bounded(args.next_step, 1000, "next step")
        item["last_seen_at"] = now()
        item["updated_at"] = now()
        if close:
            item["closed_at"] = now()
            item["status"] = "closed"
            write_json(base / "sessions/closed" / f"{identifier}.json", item)
            active.unlink()
        else:
            write_json(active, item)
    return item


def list_sessions(base: Path, status: str) -> list[dict]:
    paths: list[Path] = []
    if status in ("active", "all"):
        paths.extend((base / "sessions/active").glob("*.json"))
    if status in ("closed", "all"):
        paths.extend((base / "sessions/closed").glob("*.json"))
    return [load(path) for path in sorted(paths, key=str)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    p_start = sub.add_parser("start")
    p_start.add_argument("--task", required=True)
    p_start.add_argument("--session-id")
    p_start.add_argument("--branch", default="")
    p_start.add_argument("--worktree", default="")
    p_start.add_argument("--host", default="")
    for command in ("update", "close"):
        child = sub.add_parser(command)
        child.add_argument("--session-id", required=True)
        child.add_argument("--summary")
        child.add_argument("--next-step")
    p_list = sub.add_parser("list")
    p_list.add_argument("--status", choices=("active", "closed", "all"), default="active")
    args = parser.parse_args()
    try:
        project_id, base = resolve(args.repo)
        if args.command == "start":
            result = start(base, args)
        elif args.command == "update":
            result = update(base, args)
        elif args.command == "close":
            result = update(base, args, close=True)
        else:
            result = {"sessions": list_sessions(base, args.status)}
        output = {"project_id": project_id, "result": result}
        print(json.dumps(output, sort_keys=True, ensure_ascii=False) if args.json else json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False))
        return 0
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
