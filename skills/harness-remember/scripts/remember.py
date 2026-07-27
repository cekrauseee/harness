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
    for status in ("active", "dormant", "closed"):
        for path in sorted((base / "sessions" / status).glob("*.json")):
            item = load(path)
            rows.append({
                "artifact_refs": item.get("artifact_refs", []),
                "id": item.get("id", path.stem),
                "kind": "session",
                "path": str(path.relative_to(base)),
                "read_when": item.get("read_when", ""),
                "schema_version": 2,
                "status": item.get("status", status),
                "summary": (item.get("summary") or item.get("task") or "")[:320],
                "tags": item.get("tags", []),
                "title": (
                    item.get("title")
                    or item.get("task")
                    or f"session {str(item.get('id', ''))[:8]}"
                )[:160],
                "updated_at": item.get("updated_at", ""),
            })
    for path in sorted((base / "memory/topics").glob("*/*.json")):
        item = load(path)
        if item.get("status") != "active":
            continue
        rows.append({
            "artifact_refs": item.get("artifact_refs", []),
            "confidence": item.get("confidence", "medium"),
            "id": item["id"],
            "kind": "memory",
            "path": str(path.relative_to(base)),
            "read_when": item.get("read_when", ""),
            "review_after": item.get("review_after", ""),
            "schema_version": 2,
            "status": "active",
            "summary": item.get("summary", ""),
            "tags": item.get("tags", []),
            "title": item.get("title", item.get("topic", "")),
            "topic": item["topic"],
            "updated_at": item["updated_at"],
        })
    rows.sort(key=lambda row: (row["kind"], row["path"]))
    content = "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows)
    atomic_write(base / "memory/catalog.jsonl", content)


def candidate(base: Path, args: argparse.Namespace) -> dict:
    candidate_id = record_id(args.id)
    path = base / "memory/candidates" / f"{candidate_id}.json"
    if not args.content.strip():
        raise RuntimeError("Candidate content cannot be empty")
    topic = slug(args.topic)
    content = args.content.strip()
    summary = args.summary.strip() or " ".join(content.split())[:320]
    title = args.title.strip() or topic.replace("-", " ")
    item = {
        "artifact_refs": sorted(set(args.artifact_ref)),
        "confidence": args.confidence,
        "content": content,
        "created_at": now(),
        "id": candidate_id,
        "read_when": args.read_when.strip() or f"when work involves {topic}",
        "review_after_days": args.review_after_days,
        "schema_version": 2,
        "source_session": args.source_session,
        "status": "candidate",
        "summary": summary[:500],
        "tags": sorted(set(args.tag)),
        "title": title[:160],
        "topic": topic,
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
        if not source.is_file():
            promoted = list(
                (base / "memory/topics").glob(f"*/{candidate_id}.json")
            )
            if args.classification == "topic" and len(promoted) == 1:
                return {
                    "classification": "topic",
                    "idempotent": True,
                    "memory": load(promoted[0]),
                }
            archived_path = base / "memory/archive" / f"candidate-{candidate_id}.json"
            if archived_path.is_file():
                return {
                    "archived": load(archived_path),
                    "classification": args.classification,
                    "idempotent": True,
                }
            raise RuntimeError(f"Memory candidate was not found: {candidate_id}")
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
            if str(existing.get("id")) == candidate_id:
                continue
            if existing.get("status") == "active" and " ".join(existing.get("content", "").split()).casefold() == normalized:
                archived = archive_candidate(base, source, item, "duplicate")
                rebuild_catalog(base)
                return {"classification": "topic", "duplicate_of": existing["id"], "archived": archived}

        supersedes = record_id(args.supersedes) if args.supersedes else ""
        if supersedes == candidate_id:
            raise RuntimeError("A memory cannot supersede itself")
        old_path: Path | None = None
        old: dict | None = None
        if supersedes:
            matches = list((base / "memory/topics").glob(f"*/{supersedes}.json"))
            archived_old = base / "memory/archive" / f"memory-{supersedes}.json"
            if len(matches) == 1:
                old_path = matches[0]
                old = load(old_path)
            elif archived_old.is_file():
                archived = load(archived_old)
                if archived.get("superseded_by") != candidate_id:
                    raise RuntimeError(
                        f"Memory was superseded by another record: {supersedes}"
                    )
            else:
                raise RuntimeError(f"Memory to supersede was not found: {supersedes}")

        verified_at = now()
        memory = {
            "artifact_refs": item.get("artifact_refs", []),
            "confidence": item.get("confidence", "medium"),
            "content": item["content"],
            "created_at": verified_at,
            "id": candidate_id,
            "last_verified_at": verified_at,
            "read_when": item.get("read_when") or f"when work involves {topic}",
            "review_after": review_after(int(item.get("review_after_days", 90))),
            "schema_version": 2,
            "source_session": item.get("source_session", ""),
            "status": "active",
            "summary": item.get("summary") or " ".join(item["content"].split())[:320],
            "supersedes": supersedes,
            "tags": item.get("tags", []),
            "title": item.get("title") or topic.replace("-", " "),
            "topic": topic,
            "updated_at": now(),
        }
        target = base / "memory/topics" / topic / f"{candidate_id}.json"
        if target.is_file():
            existing_target = load(target)
            if (
                existing_target.get("id") != candidate_id
                or existing_target.get("supersedes", "") != supersedes
                or existing_target.get("content") != item["content"]
            ):
                raise RuntimeError(
                    f"Memory target already exists with different content: {candidate_id}"
                )
            memory = existing_target
        else:
            write_json(target, memory)
        if old_path is not None and old is not None:
            archived_old = dict(old)
            archived_old.update({
                "archived_at": now(),
                "status": "superseded",
                "superseded_by": candidate_id,
            })
            write_json(
                base / "memory/archive" / f"memory-{supersedes}.json",
                archived_old,
            )
            old_path.unlink()
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
    parser.add_argument("--project", "--repo", dest="project", default=".")
    parser.add_argument("--project-id", default="")
    parser.add_argument("--host", default="")
    parser.add_argument("--host-project-id", default="")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    p_candidate = sub.add_parser("candidate")
    p_candidate.add_argument("--topic", required=True)
    p_candidate.add_argument("--content", required=True)
    p_candidate.add_argument("--title", default="")
    p_candidate.add_argument("--summary", default="")
    p_candidate.add_argument("--source-session", default="")
    p_candidate.add_argument("--confidence", choices=("low", "medium", "high"), default="medium")
    p_candidate.add_argument("--tag", action="append", default=[])
    p_candidate.add_argument("--artifact-ref", action="append", default=[])
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
        project_id, base = resolve(
            args.project, args.project_id, args.host, args.host_project_id
        )
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
