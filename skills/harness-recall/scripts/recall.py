#!/usr/bin/env python3
"""Recall scoped Harness context under an explicit approximate token budget."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unicodedata
import uuid


def home() -> Path:
    return Path(os.environ.get("HARNESS_HOME", "~/.harness")).expanduser().resolve()


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


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Invalid Harness record: {path}") from exc


def terms(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    result = set(re.findall(r"[a-z0-9]+", normalized))
    try:
        aliases = load(home() / "standards/query-aliases.json")
    except RuntimeError:
        aliases = {}
    try:
        aliases.update(load(home() / "overrides/standards/query-aliases.json"))
    except RuntimeError:
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


def estimated_tokens(value: str) -> int:
    return max(1, (len(value) + 3) // 4)


def collect(base: Path, query: str, include_all: bool) -> list[dict]:
    query_terms = terms(query)
    records: list[dict] = []
    sources: list[tuple[str, Path]] = []
    sources.extend(("session", path) for path in (base / "sessions/active").glob("*.json"))
    sources.extend(("memory", path) for path in (base / "memory/topics").glob("*/*.json"))
    for kind, path in sorted(sources, key=lambda item: str(item[1])):
        item = load(path)
        if item.get("status", "active") != "active":
            continue
        if kind == "memory" and stale(item) and not include_all:
            continue
        searchable = " ".join(str(item.get(key, "")) for key in ("topic", "task", "summary", "content", "next_step", "read_when", "tags"))
        overlap = len(query_terms.intersection(terms(searchable)))
        if query_terms and overlap == 0 and not include_all:
            continue
        content = item.get("content") or item.get("summary") or item.get("task") or ""
        if kind == "session" and item.get("next_step"):
            content += f"\n\nNext step: {item['next_step']}"
        records.append({
            "content": content,
            "kind": kind,
            "score": overlap * 10 + (5 if kind == "session" else 0),
            "source": str(path.relative_to(base)),
            "stale": kind == "memory" and stale(item),
            "topic": item.get("topic", ""),
        })
    records.sort(key=lambda item: (-item["score"], item["kind"], item["source"]))
    return records


def pack(records: list[dict], budget: int) -> tuple[list[dict], int]:
    selected: list[dict] = []
    used = 0
    for record in records:
        cost = estimated_tokens(record["content"])
        if used + cost > budget:
            continue
        result = dict(record)
        result["estimated_tokens"] = cost
        selected.append(result)
        used += cost
    return selected, used


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--query", required=True)
    parser.add_argument("--budget-tokens", type=int, required=True)
    parser.add_argument("--include-all", action="store_true", help="Include zero-overlap entries for diagnostic recall")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.budget_tokens < 1:
        parser.error("--budget-tokens must be positive")
    try:
        project_id, base = resolve(args.repo)
        selected, used = pack(collect(base, args.query, args.include_all), args.budget_tokens)
        result = {
            "budget_tokens": args.budget_tokens,
            "entries": selected,
            "estimated_tokens": used,
            "project_id": project_id,
            "query": args.query,
        }
        if args.json:
            print(json.dumps(result, sort_keys=True, ensure_ascii=False))
        else:
            print(f"# Harness recall ({used}/{args.budget_tokens} estimated tokens)")
            for entry in selected:
                print(f"\n## {entry['source']}\n\n{entry['content']}")
        return 0
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
