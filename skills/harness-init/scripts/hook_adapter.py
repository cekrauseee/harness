#!/usr/bin/env python3
"""Silent, fail-open housekeeping adapter for optional Harness hooks."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import uuid

from defaults import refresh_global, refresh_project


EVENTS = ("session-start", "post-compact", "pre-compact", "stop", "user-prompt")


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


def write_json(path: Path, value: object) -> None:
    atomic_write(path, json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_git(path: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), *args], capture_output=True, text=True, check=False
        )
    except OSError:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def registered_project(path: Path, host: str = "", host_project_id: str = "") -> Path | None:
    records: set[tuple[int, Path]] = set()
    host_matches: set[Path] = set()
    for manifest_path in sorted((home() / "projects").glob("*/manifest.json")):
        try:
            manifest = load_json(manifest_path)
            uuid.UUID(str(manifest["id"]))
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            continue
        bindings = list(manifest.get("bindings", []))
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
            if isinstance(item, dict)
        ):
            host_matches.add(manifest_path.parent)
        for item in bindings:
            if not isinstance(item, dict) or item.get("type") != "path":
                continue
            try:
                binding = Path(str(item["value"])).expanduser().resolve()
                path.relative_to(binding)
            except (KeyError, ValueError):
                continue
            records.add((len(binding.parts), manifest_path.parent))
    path_match: Path | None = None
    if records:
        ranked = sorted(records, key=lambda item: (-item[0], str(item[1])))
        if len(ranked) == 1 or ranked[0][0] > ranked[1][0]:
            path_match = ranked[0][1]
        else:
            return None
    if len(host_matches) > 1:
        return None
    if host_matches:
        host_match = next(iter(host_matches))
        return host_match if path_match in (None, host_match) else None
    if path_match:
        return path_match

    root = run_git(path, "rev-parse", "--show-toplevel")
    if root:
        project_id = run_git(Path(root), "config", "--local", "--get", "harness.project-id")
        try:
            base = home() / "projects" / str(uuid.UUID(project_id))
        except (ValueError, AttributeError):
            return None
        return base if (base / "manifest.json").is_file() else None
    return None


def make_layout(base: Path) -> None:
    refresh_global(home(), atomic_write)
    for relative in (
        "sessions/active",
        "sessions/dormant",
        "sessions/closed",
        "memory/candidates",
        "memory/topics",
        "memory/archive",
        "workspace",
        "worktrees",
    ):
        (base / relative).mkdir(parents=True, exist_ok=True)
    refresh_project(base, atomic_write)


def cleanup_workspace(base: Path) -> int:
    workspace = base / "workspace"
    try:
        policy = load_json(workspace / "policy.json")
        with contextlib.suppress(OSError, json.JSONDecodeError):
            policy.update(load_json(workspace / "policy.local.json"))
        cutoff = time.time() - max(1, int(policy.get("max_age_days", 7))) * 86400
    except (OSError, ValueError, json.JSONDecodeError):
        cutoff = time.time() - 7 * 86400
    removed = 0
    for path in sorted(workspace.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if path in (workspace / "policy.json", workspace / "policy.local.json"):
            continue
        with contextlib.suppress(FileNotFoundError, OSError):
            if path.is_symlink() or (path.is_file() and path.stat().st_mtime < cutoff):
                path.unlink()
                removed += 1
            elif path.is_dir() and not any(path.iterdir()):
                path.rmdir()
    return removed


def safe_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-.")[:96] or str(uuid.uuid4())


def install(host: str, entrypoint: str) -> dict:
    path = home() / "adapters" / f"{safe_id(host.lower())}.json"
    record = {
        "entrypoint": entrypoint,
        "events": ["session-start"],
        "host": host.lower(),
        "mode": "silent-housekeeping",
        "schema_version": 2,
    }
    previous = load_json(path) if path.exists() else None
    if previous != record:
        write_json(path, record)
    return {"changed": previous != record, "adapter": record, "path": str(path)}


def read_stdin_payload() -> dict:
    if sys.stdin.isatty():
        return {}
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    value = json.loads(raw)
    return value if isinstance(value, dict) else {}


def handle_event(path: Path, event: str, host: str, host_project_id: str) -> None:
    if event not in ("session-start", "post-compact"):
        return
    base = registered_project(path, host, host_project_id)
    if base is None:
        return
    make_layout(base)
    cleanup_workspace(base)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p_install = sub.add_parser("install")
    p_install.add_argument("--host", required=True)
    p_install.add_argument("--entrypoint", required=True)
    p_install.add_argument("--json", action="store_true")
    p_event = sub.add_parser("event")
    p_event.add_argument("event_name", nargs="?", choices=EVENTS)
    p_event.add_argument("--event", dest="event_option", choices=EVENTS)
    p_event.add_argument("--project", "--repo", dest="project")
    p_event.add_argument("--host", default="")
    p_event.add_argument("--host-project-id", default="")
    p_event.add_argument("--json", action="store_true")
    # Retained as ignored compatibility options for existing host commands.
    for option in (
        "--session-id",
        "--task",
        "--summary",
        "--next-step",
        "--budget-tokens",
    ):
        p_event.add_argument(option)
    p_event.add_argument("--capture-candidate", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "install":
            result = install(args.host, args.entrypoint)
            print(
                json.dumps(result, sort_keys=True, ensure_ascii=False)
                if args.json
                else result["path"]
            )
            return 0
        payload = read_stdin_payload()
        event = args.event_option or args.event_name
        if not event:
            raise RuntimeError("event name is required")
        path = Path(
            args.project or payload.get("cwd") or payload.get("project") or "."
        ).expanduser().resolve()
        handle_event(
            path,
            event,
            args.host or str(payload.get("host", "")),
            args.host_project_id or str(payload.get("host_project_id", "")),
        )
    except Exception:
        pass  # Lifecycle hooks must never interrupt or speak to the host.
    print(json.dumps({"continue": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
