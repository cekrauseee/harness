#!/usr/bin/env python3
"""Fail-open, host-neutral lifecycle adapter for Harness hooks."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
import unicodedata
import uuid
import sys

from defaults import refresh_global, refresh_project


EVENTS = ("session-start", "user-prompt", "pre-compact", "post-compact", "stop")
HOST_EVENTS = {
    "session-start": "SessionStart",
    "user-prompt": "UserPromptSubmit",
    "pre-compact": "PreCompact",
    "post-compact": "PostCompact",
    "stop": "Stop",
}


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


@contextlib.contextmanager
def lock(path: Path):
    deadline = time.monotonic() + 5
    while True:
        try:
            path.mkdir(parents=True)
            atomic_write(path / "owner", f"{os.getpid()} {time.time()}\n")
            break
        except FileExistsError:
            try:
                if time.time() - path.stat().st_mtime > 300:
                    for item in path.iterdir():
                        item.unlink()
                    path.rmdir()
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise RuntimeError(f"Harness lock unavailable: {path}")
            time.sleep(0.05)
    try:
        yield
    finally:
        with contextlib.suppress(FileNotFoundError):
            for item in path.iterdir():
                item.unlink()
            path.rmdir()


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if result.returncode:
        return ""
    return result.stdout.strip()


def repository(path: str) -> Path | None:
    candidate = Path(path).expanduser().resolve()
    root = run_git(candidate, "rev-parse", "--show-toplevel")
    return Path(root).resolve() if root else None


def remotes(repo: Path) -> set[str]:
    result: set[str] = set()
    for name in run_git(repo, "remote").splitlines():
        value = run_git(repo, "remote", "get-url", name)
        if value:
            result.add(value)
    return result


def project_base(project_id: str) -> Path:
    return home() / "projects" / str(uuid.UUID(project_id))


def seed(path: Path, content: str) -> None:
    if not path.exists():
        atomic_write(path, content.rstrip() + "\n")


def make_global_layout() -> None:
    root = home()
    refresh_global(root, atomic_write)


def make_layout(base: Path) -> None:
    for value in (
        "memory/candidates", "memory/topics", "memory/archive",
        "sessions/active", "sessions/closed", "workspace",
        "references/product", "references/technical", "references/operations",
        "references/investigations", "worktrees",
    ):
        (base / value).mkdir(parents=True, exist_ok=True)
    if not (base / "memory/catalog.jsonl").exists():
        atomic_write(base / "memory/catalog.jsonl", "")
    seed(base / "index.md", "# Harness project\n\nRead project orientation, decisions, active sessions, and topic memory only when relevant. Repository documentation is canonical.\n")
    seed(base / "project.md", "# Project\n\nRecord concise agent-facing orientation here.\n")
    seed(base / "decisions.md", "# Decisions\n\nRecord current provisional decisions here.\n")
    refresh_project(base, atomic_write)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_or_initialize(repo: Path) -> tuple[str, str]:
    make_global_layout()
    configured = run_git(repo, "config", "--local", "--get", "harness.project-id")
    if configured:
        try:
            base = project_base(configured)
        except ValueError:
            return "", "invalid local Harness project id"
        if (base / "manifest.json").is_file():
            return configured, "resolved"
        return "", "local Harness project does not exist"

    exact: list[str] = []
    remote_matches: list[str] = []
    current_remotes = remotes(repo)
    for manifest_path in sorted((home() / "projects").glob("*/manifest.json")):
        try:
            manifest = load_json(manifest_path)
            project_id = str(uuid.UUID(manifest["id"]))
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            continue
        if str(repo) in manifest.get("repository_paths", []):
            exact.append(project_id)
        if current_remotes and current_remotes.intersection(manifest.get("remote_urls", [])):
            remote_matches.append(project_id)

    matches = sorted(set(exact or remote_matches))
    if len(matches) > 1:
        return "", "ambiguous Harness identity; automatic linking skipped"
    if len(matches) == 1:
        project_id = matches[0]
        run = subprocess.run(
            ["git", "-C", str(repo), "config", "--local", "harness.project-id", project_id],
            capture_output=True, text=True,
        )
        if run.returncode:
            return "", "could not write local Harness identity"
        base = project_base(project_id)
        with lock(base / ".lock"):
            manifest = load_json(base / "manifest.json")
            manifest["repository_paths"] = sorted(set(manifest.get("repository_paths", [])) | {str(repo)})
            manifest["remote_urls"] = sorted(set(manifest.get("remote_urls", [])) | current_remotes)
            manifest["updated_at"] = now()
            write_json(base / "manifest.json", manifest)
        return project_id, "linked"

    project_id = str(uuid.uuid4())
    base = project_base(project_id)
    with lock(home() / ".lock"):
        make_layout(base)
        write_json(base / "manifest.json", {
            "created_at": now(), "display_name": repo.name, "id": project_id,
            "remote_urls": sorted(current_remotes), "repository_paths": [str(repo)],
            "schema_version": 1, "updated_at": now(),
        })
        result = subprocess.run(
            ["git", "-C", str(repo), "config", "--local", "harness.project-id", project_id],
            capture_output=True, text=True,
        )
        if result.returncode:
            return "", "could not write local Harness identity"
    return project_id, "initialized"


def tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def lexical_terms(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    result = set(re.findall(r"[a-z0-9]+", normalized))
    try:
        aliases = load_json(home() / "standards/query-aliases.json")
    except (OSError, json.JSONDecodeError):
        aliases = {}
    try:
        overrides = load_json(home() / "overrides/standards/query-aliases.json")
        aliases.update(overrides)
    except (OSError, json.JSONDecodeError):
        pass
    for term in list(result):
        result.update(str(alias) for alias in aliases.get(term, []))
    return result


def stale(item: dict) -> bool:
    value = item.get("review_after")
    if not value:
        return False
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")) <= dt.datetime.now(dt.timezone.utc)
    except (TypeError, ValueError):
        return True


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


def recall(base: Path, query: str, budget: int, include_orientation: bool = True) -> dict:
    terms = lexical_terms(query)
    rows: list[tuple[int, str, dict]] = []
    static_paths = ([home() / "charter.md", *sorted((home() / "standards").glob("*.md")), home() / "overrides/charter.md", *sorted((home() / "overrides/standards").glob("*.md")), base / "index.md", base / "project.md", base / "decisions.md"] if include_orientation else [])
    for path in static_paths:
        if path.is_file():
            content = path.read_text(encoding="utf-8").strip()
            rows.append((100, str(path), {"content": content, "kind": "orientation", "source": str(path)}))
    paths = list((base / "sessions/active").glob("*.json")) + list((base / "memory/topics").glob("*/*.json"))
    for path in sorted(paths):
        try:
            item = load_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        if item.get("status") not in ("active", None):
            continue
        kind = "session" if "/sessions/" in str(path) else "memory"
        if kind == "memory" and stale(item):
            continue
        content = item.get("summary") or item.get("content") or item.get("task") or ""
        haystack = " ".join(str(item.get(k, "")) for k in ("topic", "task", "summary", "content", "read_when", "tags"))
        overlap = len(terms.intersection(lexical_terms(haystack)))
        if not terms and kind == "memory":
            continue
        score = overlap * 10 + (5 if kind == "session" else 0)
        if terms and score == 0:
            continue
        rows.append((score, str(path.relative_to(base)), {"content": content, "kind": kind, "source": str(path.relative_to(base))}))
    rows.sort(key=lambda row: (-row[0], row[1]))
    selected: list[dict] = []
    used = 0
    for _, _, item in rows:
        cost = tokens(item["content"])
        if used + cost > budget:
            continue
        item["estimated_tokens"] = cost
        selected.append(item)
        used += cost
    return {"budget_tokens": budget, "entries": selected, "estimated_tokens": used}


def safe_id(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-.")
    return cleaned[:96] or str(uuid.uuid4())


def checkpoint(base: Path, session_id: str, task: str, summary: str, next_step: str, close: bool = False) -> None:
    session_id = safe_id(session_id)
    active = base / "sessions/active" / f"{session_id}.json"
    with lock(base / ".lock"):
        if active.exists():
            record = load_json(active)
        else:
            record = {"created_at": now(), "id": session_id, "status": "active", "task": task[:500]}
        if task:
            record["task"] = task[:500]
        if summary:
            record["summary"] = summary[:4000]
        if next_step:
            record["next_step"] = next_step[:1000]
        record["updated_at"] = now()
        if close:
            record["status"] = "closed"
            record["closed_at"] = now()
            write_json(base / "sessions/closed" / f"{session_id}.json", record)
            with contextlib.suppress(FileNotFoundError):
                active.unlink()
        else:
            write_json(active, record)


def add_candidate(base: Path, session_id: str, summary: str) -> str:
    candidate_id = str(uuid.uuid4())
    with lock(base / ".lock"):
        write_json(base / "memory/candidates" / f"{candidate_id}.json", {
            "content": summary[:4000], "created_at": now(), "id": candidate_id,
            "source_session": session_id, "status": "candidate", "topic": "session-observation",
        })
    return candidate_id


def install(host: str, entrypoint: str) -> dict:
    path = home() / "adapters" / f"{safe_id(host.lower())}.json"
    record = {"entrypoint": entrypoint, "events": list(EVENTS), "host": host.lower(), "schema_version": 1}
    previous = load_json(path) if path.exists() else None
    if previous != record:
        write_json(path, record)
    return {"changed": previous != record, "adapter": record, "path": str(path)}


def handle_event(args: argparse.Namespace) -> dict:
    repo = repository(args.repo)
    if repo is None:
        return {"continue": True, "status": "skipped"}
    project_id, resolution = resolve_or_initialize(repo)
    if not project_id:
        return {"continue": True, "status": "skipped", "warning": resolution}
    base = project_base(project_id)
    make_layout(base)
    result: dict = {"continue": True, "project_id": project_id, "resolution": resolution, "status": "ok"}
    if args.event in ("session-start", "post-compact"):
        result["workspace_files_removed"] = cleanup_workspace(base)
        result["context"] = recall(base, args.task or args.summary, args.budget_tokens, True)
        if args.session_id and args.event == "session-start":
            checkpoint(base, args.session_id, args.persist_task, args.summary, args.next_step, False)
    elif args.event == "user-prompt":
        result["context"] = recall(base, args.task, args.budget_tokens, False)
        if args.session_id:
            checkpoint(base, args.session_id, "", "", args.next_step, False)
    elif args.event == "pre-compact" and args.session_id:
        checkpoint(base, args.session_id, args.task, args.summary, args.next_step, False)
    elif args.event == "stop" and args.session_id:
        checkpoint(base, args.session_id, args.task, args.summary, args.next_step, False)
        if args.capture_candidate and args.summary:
            result["candidate_id"] = add_candidate(base, args.session_id, args.summary)
    return result


def read_stdin_payload() -> dict:
    if sys.stdin.isatty():
        return {}
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    value = json.loads(raw)
    return value if isinstance(value, dict) else {}


def context_text(context: dict) -> str:
    return "\n\n".join(f"## {item['source']}\n\n{item['content']}" for item in context.get("entries", []))


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
    p_event.add_argument("--repo")
    p_event.add_argument("--session-id", default="")
    p_event.add_argument("--task", default="")
    p_event.add_argument("--summary", default="")
    p_event.add_argument("--next-step", default="")
    p_event.add_argument("--budget-tokens", type=int, default=1200)
    p_event.add_argument("--capture-candidate", action="store_true")
    p_event.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "install":
            result = install(args.host, args.entrypoint)
        else:
            payload = read_stdin_payload()
            args.event = args.event_option or args.event_name
            if not args.event:
                raise RuntimeError("event name is required")
            args.repo = args.repo or payload.get("cwd") or payload.get("repo") or "."
            args.session_id = args.session_id or payload.get("session_id", "")
            explicit_task = args.task or payload.get("harness_task", "")
            args.task = explicit_task or payload.get("prompt", "")
            args.persist_task = explicit_task
            explicit_summary = args.summary or payload.get("harness_summary", "")
            args.summary = explicit_summary
            args.capture_candidate = args.capture_candidate or bool(explicit_summary)
            args.next_step = args.next_step or payload.get("next_step", "")
            result = handle_event(args)
    except Exception as exc:  # Hooks must never interrupt the host lifecycle.
        result = {"continue": True, "status": "failed-open", "warning": str(exc)}
    if args.command == "install":
        if args.json:
            print(json.dumps(result, sort_keys=True, ensure_ascii=False))
        else:
            print(result["path"])
    elif getattr(args, "json", False) or args.command == "event":
        output = {"continue": True}
        if result.get("context"):
            output["hookSpecificOutput"] = {
                "additionalContext": context_text(result["context"]),
                "hookEventName": HOST_EVENTS[args.event],
            }
        if result.get("warning"):
            output["systemMessage"] = f"Harness: {result['warning']}"
        print(json.dumps(output, sort_keys=True, ensure_ascii=False))
    elif "context" in result:
        for entry in result["context"]["entries"]:
            print(f"## {entry['source']}\n\n{entry['content']}\n")
    elif result.get("warning"):
        print(f"Harness: {result['warning']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
