#!/usr/bin/env python3
"""Capture and classify segmented Harness memory."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import os
from pathlib import Path
import re
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


def review_after(days: int) -> str:
    return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=days)).replace(microsecond=0).isoformat()


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
        raise RuntimeError(f"Invalid Harness record: {path}") from exc


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


def slug(value: str) -> str:
    result = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not result:
        raise RuntimeError("Topic must contain letters or digits")
    return result[:80]


def record_id(value: str | None = None) -> str:
    try:
        return str(uuid.UUID(value)) if value else str(uuid.uuid4())
    except ValueError as exc:
        raise RuntimeError(f"Invalid record id: {value}") from exc


def rebuild_catalog(base: Path) -> None:
    rows: list[dict] = []
    for path in sorted((base / "memory/topics").glob("*/*.json")):
        item = load(path)
        if item.get("status") != "active":
            continue
        rows.append({
            "confidence": item.get("confidence", "medium"),
            "id": item["id"],
            "last_verified_at": item.get("last_verified_at", ""),
            "path": str(path.relative_to(base)),
            "read_when": item.get("read_when", ""),
            "review_after": item.get("review_after", ""),
            "source_session": item.get("source_session", ""),
            "status": "active",
            "topic": item["topic"],
            "updated_at": item["updated_at"],
        })
    rows.sort(key=lambda row: (row["topic"], row["id"]))
    content = "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows)
    atomic_write(base / "memory/catalog.jsonl", content)


def candidate(base: Path, args: argparse.Namespace) -> dict:
    candidate_id = record_id(args.id)
    path = base / "memory/candidates" / f"{candidate_id}.json"
    if not args.content.strip():
        raise RuntimeError("Candidate content cannot be empty")
    item = {
        "confidence": args.confidence,
        "content": args.content.strip(),
        "created_at": now(),
        "id": candidate_id,
        "read_when": args.read_when.strip() or f"when work involves {slug(args.topic)}",
        "review_after_days": args.review_after_days,
        "source_session": args.source_session,
        "status": "candidate",
        "tags": sorted(set(args.tag)),
        "topic": slug(args.topic),
        "updated_at": now(),
    }
    with lock(base / ".lock"):
        if path.exists():
            raise RuntimeError(f"Candidate already exists: {candidate_id}")
        write_json(path, item)
    return item


def archive_candidate(base: Path, source: Path, item: dict, resolution: str, action: str = "") -> dict:
    archived = dict(item)
    archived.update({"archived_at": now(), "resolution": resolution, "status": "archived"})
    if action:
        archived["action_required"] = action
    write_json(base / "memory/archive" / f"candidate-{item['id']}.json", archived)
    source.unlink()
    return archived


def discard_candidate(base: Path, source: Path, item: dict) -> dict:
    tombstone = {
        "archived_at": now(),
        "created_at": item.get("created_at", ""),
        "id": item["id"],
        "resolution": "discard",
        "source_session": item.get("source_session", ""),
        "status": "archived",
        "topic": item.get("topic", ""),
    }
    write_json(base / "memory/archive" / f"candidate-{item['id']}.json", tombstone)
    source.unlink()
    return tombstone


def consolidate(base: Path, args: argparse.Namespace) -> dict:
    candidate_id = record_id(args.candidate_id)
    source = base / "memory/candidates" / f"{candidate_id}.json"
    with lock(base / ".lock"):
        item = load(source)
        classification = args.classification
        if classification == "discard":
            archived = discard_candidate(base, source, item)
            return {"classification": classification, "archived": archived}
        if classification != "topic":
            actions = {
                "documentation": "promote stable knowledge through the Harness documentation workflow",
                "rule": "promote mandatory behavior to project agent instructions",
            }
            archived = archive_candidate(base, source, item, classification, actions.get(classification, ""))
            return {"classification": classification, "archived": archived}

        topic = slug(args.topic or item["topic"])
        normalized = " ".join(item["content"].split()).casefold()
        for existing_path in sorted((base / "memory/topics" / topic).glob("*.json")):
            existing = load(existing_path)
            if existing.get("status") == "active" and " ".join(existing.get("content", "").split()).casefold() == normalized:
                archived = archive_candidate(base, source, item, "duplicate")
                rebuild_catalog(base)
                return {"classification": "topic", "duplicate_of": existing["id"], "archived": archived}

        supersedes = record_id(args.supersedes) if args.supersedes else ""
        if supersedes:
            matches = list((base / "memory/topics").glob(f"*/{supersedes}.json"))
            if len(matches) != 1:
                raise RuntimeError(f"Memory to supersede was not found: {supersedes}")
            old_path = matches[0]
            old = load(old_path)
            old.update({"archived_at": now(), "status": "superseded", "superseded_by": candidate_id})
            write_json(base / "memory/archive" / f"memory-{supersedes}.json", old)
            old_path.unlink()

        verified_at = now()
        memory = {
            "confidence": item.get("confidence", "medium"),
            "content": item["content"],
            "created_at": verified_at,
            "id": candidate_id,
            "last_verified_at": verified_at,
            "read_when": item.get("read_when") or f"when work involves {topic}",
            "review_after": review_after(int(item.get("review_after_days", 90))),
            "source_session": item.get("source_session", ""),
            "status": "active",
            "supersedes": supersedes,
            "tags": item.get("tags", []),
            "topic": topic,
            "updated_at": now(),
        }
        write_json(base / "memory/topics" / topic / f"{candidate_id}.json", memory)
        archive_candidate(base, source, item, "promoted-to-topic")
        rebuild_catalog(base)
        return {"classification": "topic", "memory": memory}


def list_records(base: Path, status: str) -> list[dict]:
    if status == "candidate":
        paths = (base / "memory/candidates").glob("*.json")
    elif status == "active":
        paths = (base / "memory/topics").glob("*/*.json")
    else:
        paths = (base / "memory/archive").glob("*.json")
    return [load(path) for path in sorted(paths)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    p_candidate = sub.add_parser("candidate")
    p_candidate.add_argument("--topic", required=True)
    p_candidate.add_argument("--content", required=True)
    p_candidate.add_argument("--source-session", default="")
    p_candidate.add_argument("--confidence", choices=("low", "medium", "high"), default="medium")
    p_candidate.add_argument("--tag", action="append", default=[])
    p_candidate.add_argument("--read-when", default="")
    p_candidate.add_argument("--review-after-days", type=int, default=90)
    p_candidate.add_argument("--id")
    p_consolidate = sub.add_parser("consolidate")
    p_consolidate.add_argument("--candidate-id", required=True)
    p_consolidate.add_argument("--classification", choices=("topic", "documentation", "rule", "archive", "discard"), required=True)
    p_consolidate.add_argument("--topic")
    p_consolidate.add_argument("--supersedes")
    p_list = sub.add_parser("list")
    p_list.add_argument("--status", choices=("candidate", "active", "archived"), default="candidate")
    args = parser.parse_args()
    if args.command == "candidate" and args.review_after_days < 1:
        parser.error("--review-after-days must be positive")
    try:
        project_id, base = resolve(args.repo)
        if args.command == "candidate":
            result = candidate(base, args)
        elif args.command == "consolidate":
            result = consolidate(base, args)
        else:
            result = {"records": list_records(base, args.status), "status": args.status}
        output = {"project_id": project_id, "result": result}
        if args.json:
            print(json.dumps(output, sort_keys=True, ensure_ascii=False))
        else:
            print(json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False))
        return 0
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
