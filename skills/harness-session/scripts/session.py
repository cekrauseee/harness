#!/usr/bin/env python3
"""Manage semantic Harness handoff sessions for any local project."""

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
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Invalid Harness session: {path}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"Invalid Harness session: {path}")
    return value


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


def git(path: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), *args], capture_output=True, text=True, check=False
        )
    except OSError:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def valid_project_id(value: str) -> str:
    try:
        return str(uuid.UUID(value))
    except (ValueError, AttributeError) as exc:
        raise RuntimeError(f"Invalid Harness project id: {value}") from exc


def resolve(
    project: str,
    project_id: str = "",
    host: str = "",
    host_project_id: str = "",
) -> tuple[str, Path]:
    if project_id:
        identifier = valid_project_id(project_id)
        base = home() / "projects" / identifier
        if not (base / "manifest.json").is_file():
            raise RuntimeError("Harness project does not exist")
        return identifier, base
    target = Path(project).expanduser().resolve()
    matches: list[tuple[int, str, Path]] = []
    host_matches: set[tuple[str, Path]] = set()
    for manifest_path in sorted((home() / "projects").glob("*/manifest.json")):
        try:
            manifest = load(manifest_path)
            identifier = valid_project_id(manifest["id"])
        except (RuntimeError, KeyError):
            continue
        bindings = [item for item in manifest.get("bindings", []) if isinstance(item, dict)]
        bindings.extend(
            {"type": "path", "value": value}
            for value in manifest.get("repository_paths", [])
            if isinstance(value, str)
        )
        if host and host_project_id and any(
            item.get("type") == "host"
            and item.get("host") == host.lower()
            and item.get("value") == host_project_id
            for item in bindings
        ):
            host_matches.add((identifier, manifest_path.parent))
        for item in bindings:
            if item.get("type") != "path":
                continue
            try:
                bound = Path(str(item["value"])).expanduser().resolve()
                target.relative_to(bound)
            except (KeyError, ValueError):
                continue
            matches.append((len(bound.parts), identifier, manifest_path.parent))
    path_match: tuple[str, Path] | None = None
    if matches:
        matches.sort(key=lambda item: (-item[0], item[1]))
        if len(matches) > 1 and matches[0][0] == matches[1][0] and matches[0][1] != matches[1][1]:
            raise RuntimeError("Ambiguous Harness path binding")
        path_match = (matches[0][1], matches[0][2])
    if len(host_matches) > 1:
        raise RuntimeError("Ambiguous Harness host binding")
    if host_matches:
        host_match = next(iter(host_matches))
        if path_match and path_match[0] != host_match[0]:
            raise RuntimeError("Host and path resolve to different Harness projects")
        return host_match
    if path_match:
        return path_match
    root = git(target, "rev-parse", "--show-toplevel")
    legacy = git(Path(root), "config", "--local", "--get", "harness.project-id") if root else ""
    if legacy:
        identifier = valid_project_id(legacy)
        base = home() / "projects" / identifier
        if (base / "manifest.json").is_file():
            return identifier, base
    raise RuntimeError("Project is not linked to Harness; run harness-init")


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


def clean_list(values: list[str] | None, limit: int, field: str) -> list[str]:
    result = sorted({bounded(value, limit, field) for value in (values or []) if value.strip()})
    return result


def fallback_title(task: str) -> str:
    return " ".join(task.split())[:120]


def catalog_row(kind: str, status: str, path: Path, base: Path, item: dict) -> dict:
    row = {
        "artifact_refs": [
            str(value) for value in item.get("artifact_refs", []) if str(value).strip()
        ],
        "id": str(item.get("id", path.stem)),
        "kind": kind,
        "path": str(path.relative_to(base)),
        "read_when": str(item.get("read_when", "")),
        "schema_version": 2,
        "status": str(item.get("status") or status),
        "summary": str(item.get("summary") or item.get("task") or "")[:320],
        "tags": [str(value) for value in item.get("tags", []) if str(value).strip()],
        "title": str(
            item.get("title")
            or item.get("topic")
            or item.get("task")
            or f"{kind} {str(item.get('id', ''))[:8]}"
        )[:160],
        "updated_at": str(item.get("updated_at", "")),
    }
    if kind == "memory":
        row.update(
            {
                "confidence": str(item.get("confidence", "medium")),
                "review_after": str(item.get("review_after", "")),
                "topic": str(item.get("topic", "")),
            }
        )
    return row


def rebuild_catalog(base: Path) -> None:
    rows: list[dict] = []
    for status in ("active", "dormant", "closed"):
        for path in sorted((base / "sessions" / status).glob("*.json")):
            item = load(path)
            rows.append(catalog_row("session", status, path, base, item))
    for path in sorted((base / "memory/topics").glob("*/*.json")):
        item = load(path)
        if item.get("status") == "active":
            rows.append(catalog_row("memory", "active", path, base, item))
    rows.sort(key=lambda item: (item["kind"], item["path"]))
    content = "".join(
        json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows
    )
    atomic_write(base / "memory/catalog.jsonl", content)


def start(base: Path, args: argparse.Namespace) -> dict:
    task = bounded(args.task, 1000, "task")
    if not task:
        raise RuntimeError("Task cannot be empty; create sessions only for material work")
    identifier = session_id(args.session_id)
    path = base / "sessions/active" / f"{identifier}.json"
    timestamp = now()
    title = bounded(args.title or fallback_title(task), 160, "title")
    item = {
        "artifact_refs": clean_list(args.artifact_ref, 1000, "artifact reference"),
        "branch": bounded(args.branch, 250, "branch"),
        "created_at": timestamp,
        "host": bounded(args.host_name, 80, "host"),
        "id": identifier,
        "last_seen_at": timestamp,
        "next_step": "",
        "read_when": bounded(
            args.read_when or f"when continuing {title}", 300, "read when"
        ),
        "schema_version": 2,
        "status": "active",
        "summary": bounded(args.summary, 1000, "summary"),
        "tags": clean_list(args.tag, 80, "tag"),
        "task": task,
        "title": title,
        "updated_at": timestamp,
        "worktree": bounded(args.worktree, 1000, "worktree"),
    }
    with lock(base / ".lock"):
        existing_paths = [
            candidate
            for status in ("active", "dormant", "closed")
            if (candidate := base / "sessions" / status / f"{identifier}.json").exists()
        ]
        if existing_paths:
            existing = load(existing_paths[0])
            if existing_paths[0] == path and existing.get("task") == item["task"]:
                return existing
            raise RuntimeError(f"Session id already exists: {identifier}")
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, item)
        rebuild_catalog(base)
    return item


def locate(base: Path, identifier: str) -> tuple[Path, dict]:
    matches = [
        path
        for status in ("active", "dormant")
        if (path := base / "sessions" / status / f"{identifier}.json").is_file()
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Open session was not found: {identifier}")
    return matches[0], load(matches[0])


def update_fields(item: dict, args: argparse.Namespace) -> None:
    for argument, field, limit, label in (
        ("title", "title", 160, "title"),
        ("summary", "summary", 4000, "summary"),
        ("next_step", "next_step", 1000, "next step"),
        ("read_when", "read_when", 300, "read when"),
    ):
        value = getattr(args, argument, None)
        if value is not None:
            item[field] = bounded(value, limit, label)
    if getattr(args, "tag", None) is not None:
        item["tags"] = clean_list(args.tag, 80, "tag")
    if getattr(args, "artifact_ref", None) is not None:
        item["artifact_refs"] = clean_list(
            args.artifact_ref, 1000, "artifact reference"
        )
    item["schema_version"] = 2
    item["last_seen_at"] = now()
    item["updated_at"] = now()


def transition(base: Path, args: argparse.Namespace, status: str) -> dict:
    identifier = session_id(args.session_id)
    with lock(base / ".lock"):
        source, item = locate(base, identifier)
        update_fields(item, args)
        destination = base / "sessions" / status / f"{identifier}.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination != source and destination.exists():
            raise RuntimeError(f"Session transition target already exists: {identifier}")
        item["status"] = status
        if status == "closed":
            item["closed_at"] = now()
        elif status == "dormant":
            item["dormant_at"] = now()
        write_json(destination, item)
        if source != destination:
            source.unlink()
        rebuild_catalog(base)
    return item


def update(base: Path, args: argparse.Namespace) -> dict:
    identifier = session_id(args.session_id)
    with lock(base / ".lock"):
        path, item = locate(base, identifier)
        update_fields(item, args)
        write_json(path, item)
        rebuild_catalog(base)
    return item


def list_sessions(base: Path, status: str) -> list[dict]:
    statuses = ("active", "dormant", "closed") if status == "all" else (status,)
    paths = [
        path
        for current in statuses
        for path in (base / "sessions" / current).glob("*.json")
    ]
    return [load(path) for path in sorted(paths, key=str)]


def add_update_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--title")
    parser.add_argument("--summary")
    parser.add_argument("--next-step")
    parser.add_argument("--read-when")
    parser.add_argument("--tag", action="append")
    parser.add_argument("--artifact-ref", action="append")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", "--repo", dest="project", default=".")
    parser.add_argument("--project-id", default="")
    parser.add_argument("--host", default="")
    parser.add_argument("--host-project-id", default="")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    p_start = sub.add_parser("start")
    p_start.add_argument("--task", required=True)
    p_start.add_argument("--title", default="")
    p_start.add_argument("--summary", default="")
    p_start.add_argument("--read-when", default="")
    p_start.add_argument("--tag", action="append", default=[])
    p_start.add_argument("--artifact-ref", action="append", default=[])
    p_start.add_argument("--session-id")
    p_start.add_argument("--branch", default="")
    p_start.add_argument("--worktree", default="")
    p_start.add_argument("--host", dest="host_name", default="")
    for command in ("update", "dormant", "close"):
        add_update_arguments(sub.add_parser(command))
    p_list = sub.add_parser("list")
    p_list.add_argument(
        "--status", choices=("active", "dormant", "closed", "all"), default="active"
    )
    args = parser.parse_args()
    try:
        project_id, base = resolve(
            args.project, args.project_id, args.host, args.host_project_id
        )
        if args.command == "start":
            result = start(base, args)
        elif args.command == "update":
            result = update(base, args)
        elif args.command == "dormant":
            result = transition(base, args, "dormant")
        elif args.command == "close":
            result = transition(base, args, "closed")
        else:
            result = {"sessions": list_sessions(base, args.status)}
        output = {"project_id": project_id, "result": result}
        print(
            json.dumps(output, sort_keys=True, ensure_ascii=False)
            if args.json
            else json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False)
        )
        return 0
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
