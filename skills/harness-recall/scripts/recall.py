#!/usr/bin/env python3
"""Search semantic Harness cards, then hydrate only selected records."""

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
import unicodedata
import uuid


def home() -> Path:
    return Path(os.environ.get("HARNESS_HOME", "~/.harness")).expanduser().resolve()


def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Invalid Harness record: {path}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"Invalid Harness record: {path}")
    return value


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


def git(path: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), *args], capture_output=True, text=True, check=False
        )
    except OSError:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def valid_id(value: str) -> str:
    try:
        return str(uuid.UUID(value))
    except (ValueError, AttributeError) as exc:
        raise RuntimeError(f"Invalid Harness id: {value}") from exc


def manifest_bindings(manifest: dict) -> list[dict]:
    result = [item for item in manifest.get("bindings", []) if isinstance(item, dict)]
    result.extend(
        {"type": "path", "value": value}
        for value in manifest.get("repository_paths", [])
        if isinstance(value, str)
    )
    return result


def resolve(
    project: str,
    project_id: str = "",
    host: str = "",
    host_project_id: str = "",
) -> tuple[str, Path]:
    if project_id:
        identifier = valid_id(project_id)
        base = home() / "projects" / identifier
        if not (base / "manifest.json").is_file():
            raise RuntimeError("Harness project does not exist")
        return identifier, base

    target = Path(project).expanduser().resolve()
    candidates: list[tuple[int, str, Path]] = []
    host_matches: set[tuple[str, Path]] = set()
    for manifest_path in sorted((home() / "projects").glob("*/manifest.json")):
        try:
            manifest = load(manifest_path)
            identifier = valid_id(manifest["id"])
        except (RuntimeError, KeyError):
            continue
        bindings = manifest_bindings(manifest)
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
            candidates.append((len(bound.parts), identifier, manifest_path.parent))
    path_match: tuple[str, Path] | None = None
    if candidates:
        candidates.sort(key=lambda item: (-item[0], item[1]))
        if len(candidates) > 1 and candidates[0][0] == candidates[1][0] and candidates[0][1] != candidates[1][1]:
            raise RuntimeError("Ambiguous Harness path binding")
        path_match = (candidates[0][1], candidates[0][2])
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
        identifier = valid_id(legacy)
        base = home() / "projects" / identifier
        if (base / "manifest.json").is_file():
            return identifier, base
    raise RuntimeError("Project is not linked to Harness; run harness-init")


def terms(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    result = set(re.findall(r"[a-z0-9]+", normalized))
    aliases: dict = {}
    for path in (
        home() / "standards/query-aliases.json",
        home() / "overrides/standards/query-aliases.json",
    ):
        try:
            aliases.update(load(path))
        except RuntimeError:
            pass
    for term in list(result):
        result.update(str(alias).casefold() for alias in aliases.get(term, []))
    return result


def stale(item: dict) -> bool:
    value = item.get("review_after")
    if not value:
        return False
    try:
        return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00")) <= dt.datetime.now(dt.timezone.utc)
    except (TypeError, ValueError):
        return True


def estimated_tokens(value: str) -> int:
    return max(1, (len(value) + 3) // 4)


def record_sources(base: Path) -> list[tuple[str, str, Path]]:
    sources: list[tuple[str, str, Path]] = []
    for status in ("active", "dormant", "closed"):
        sources.extend(
            ("session", status, path)
            for path in (base / "sessions" / status).glob("*.json")
        )
    sources.extend(
        ("memory", "active", path)
        for path in (base / "memory/topics").glob("*/*.json")
    )
    return sorted(sources, key=lambda row: str(row[2]))


def string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def title_for(kind: str, item: dict) -> str:
    fallback = item.get("topic") if kind == "memory" else item.get("task")
    return str(item.get("title") or fallback or f"{kind} {item.get('id', '')[:8]}").strip()[:160]


def summary_for(item: dict) -> str:
    return str(item.get("summary") or item.get("task") or "").strip()[:320]


def token_phrase(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return " ".join(re.findall(r"[a-z0-9]+", normalized))


def recency_bonus(value: str) -> int:
    try:
        updated = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        days = max(0, (dt.datetime.now(dt.timezone.utc) - updated).days)
    except (TypeError, ValueError):
        return 0
    if days <= 7:
        return 3
    if days <= 30:
        return 2
    if days <= 90:
        return 1
    return 0


def score_record(query: str, query_terms: set[str], item: dict, kind: str, status: str) -> int:
    title = title_for(kind, item)
    summary = summary_for(item)
    read_when = str(item.get("read_when", ""))
    tags = " ".join(string_list(item.get("tags")))
    title_overlap = len(query_terms & terms(title))
    score = (
        title_overlap * 12
        + len(query_terms & terms(tags)) * 9
        + len(query_terms & terms(read_when)) * 7
        + len(query_terms & terms(summary)) * 4
    )
    query_phrase = token_phrase(query)
    if title_overlap and query_phrase and query_phrase in token_phrase(title):
        score += 24
    if score:
        score += recency_bonus(str(item.get("updated_at", "")))
        if status == "active":
            score += 2
        elif status == "dormant":
            score -= 2
        elif status == "closed":
            score -= 4
    return max(0, score)


def card(kind: str, status: str, path: Path, base: Path, item: dict, score: int) -> dict:
    return {
        "artifact_refs": string_list(item.get("artifact_refs")),
        "id": str(item.get("id", path.stem)),
        "kind": kind,
        "path": str(path.relative_to(base)),
        "read_when": str(item.get("read_when", "")),
        "score": score,
        "status": str(item.get("status") or status),
        "summary": summary_for(item),
        "tags": string_list(item.get("tags")),
        "title": title_for(kind, item),
        "updated_at": str(item.get("updated_at", "")),
    }


def catalog_card(kind: str, status: str, path: Path, base: Path, item: dict) -> dict:
    result = card(kind, status, path, base, item, 0)
    result.pop("score", None)
    result["schema_version"] = 2
    if kind == "memory":
        result["confidence"] = str(item.get("confidence", "medium"))
        result["review_after"] = str(item.get("review_after", ""))
        result["topic"] = str(item.get("topic", ""))
    return result


def rebuild_catalog(base: Path) -> list[dict]:
    rows = [
        catalog_card(kind, str(item.get("status") or status), path, base, item)
        for kind, status, path in record_sources(base)
        if (item := load(path)).get("status", status) in (
            "active", "dormant", "closed"
        )
    ]
    rows.sort(key=lambda item: (item["kind"], item["path"]))
    rendered = "".join(
        json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows
    )
    catalog = base / "memory/catalog.jsonl"
    try:
        current = catalog.read_text(encoding="utf-8")
    except OSError:
        current = ""
    if current != rendered:
        atomic_write(catalog, rendered)
    return rows


def search(
    base: Path,
    query: str,
    limit: int,
    include_all: bool,
    include_stale: bool,
    budget_tokens: int,
) -> tuple[list[dict], int]:
    query_terms = terms(query)
    if not query_terms and not include_all:
        return [], 0
    ranked: list[dict] = []
    for item in rebuild_catalog(base):
        kind = str(item["kind"])
        record_status = str(item["status"])
        if kind == "memory" and record_status != "active":
            continue
        if kind == "memory" and stale(item) and not include_stale:
            continue
        score = score_record(query, query_terms, item, kind, record_status)
        if score == 0 and not include_all:
            continue
        result = dict(item)
        result.pop("schema_version", None)
        result["score"] = score
        ranked.append(result)
    ranked.sort(key=lambda item: (-item["score"], item["kind"], item["path"]))
    selected: list[dict] = []
    used = 0
    for item in ranked[:limit]:
        rendered = json.dumps(item, sort_keys=True, ensure_ascii=False)
        cost = estimated_tokens(rendered)
        if used + cost > budget_tokens:
            continue
        selected.append(item)
        used += cost
    return selected, used


def find_record(base: Path, identifier: str) -> tuple[str, Path, dict]:
    identifier = valid_id(identifier)
    matches = [
        (kind, path, load(path))
        for kind, _, path in record_sources(base)
        if path.stem == identifier
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Harness record {'was not found' if not matches else 'is ambiguous'}: {identifier}"
        )
    return matches[0]


def content_for(kind: str, item: dict) -> str:
    if kind == "memory":
        return str(item.get("content") or item.get("summary") or "")
    parts = []
    for label, field in (
        ("Task", "task"),
        ("Summary", "summary"),
        ("Next step", "next_step"),
    ):
        value = str(item.get(field) or "").strip()
        if value:
            parts.append(f"{label}: {value}")
    return "\n\n".join(parts)


def envelope_tokens(value: dict) -> int:
    return estimated_tokens(json.dumps(value, sort_keys=True, ensure_ascii=False))


def fit_metadata(result: dict, budget_tokens: int) -> dict:
    fitted = dict(result)
    fitted["content"] = ""
    fitted["estimated_tokens"] = 0
    fitted["metadata_truncated"] = False
    fitted["truncated"] = False
    if envelope_tokens(fitted) <= budget_tokens:
        return fitted
    fitted["metadata_truncated"] = True
    for field in ("summary", "read_when", "title"):
        value = str(fitted.get(field, ""))
        while value and envelope_tokens(fitted) > budget_tokens:
            value = value[: max(0, len(value) // 2)]
            fitted[field] = value.rstrip() + ("…" if value else "")
    for field in ("artifact_refs", "tags"):
        values = list(fitted.get(field, []))
        while values and envelope_tokens(fitted) > budget_tokens:
            values.pop()
            fitted[field] = values
    if envelope_tokens(fitted) > budget_tokens:
        raise RuntimeError(
            f"Hydration budget is too small for the record envelope: {budget_tokens}"
        )
    return fitted


def stabilize_estimate(result: dict) -> int:
    estimate = 0
    for _ in range(8):
        result["estimated_tokens"] = estimate
        updated = envelope_tokens(result)
        if updated == estimate:
            return updated
        estimate = updated
    result["estimated_tokens"] = estimate
    return envelope_tokens(result)


def hydrate(base: Path, identifier: str, budget_tokens: int) -> dict:
    kind, path, item = find_record(base, identifier)
    result = card(kind, str(item.get("status", "")), path, base, item, 0)
    result.pop("score", None)
    result = fit_metadata(result, budget_tokens)
    full_content = content_for(kind, item)
    low, high = 0, len(full_content)
    while low < high:
        midpoint = (low + high + 1) // 2
        candidate = full_content[:midpoint]
        result["content"] = candidate
        result["truncated"] = midpoint < len(full_content)
        if result["truncated"] and candidate:
            result["content"] = candidate[:-1].rstrip() + "…"
        stabilize_estimate(result)
        if envelope_tokens(result) <= budget_tokens:
            low = midpoint
        else:
            high = midpoint - 1
    content = full_content[:low]
    result["content"] = content
    result["truncated"] = low < len(full_content)
    if result["truncated"] and content:
        result["content"] = content[:-1].rstrip() + "…"
    estimate = stabilize_estimate(result)
    if estimate > budget_tokens:
        raise RuntimeError("Could not fit hydrated record within the requested budget")
    return result


def target_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project", "--repo", dest="project", default=".")
    parser.add_argument("--project-id", default="")
    parser.add_argument("--host", default="")
    parser.add_argument("--host-project-id", default="")
    parser.add_argument("--json", action="store_true")


def legacy_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    target_arguments(parser)
    parser.add_argument("--query", required=True)
    parser.add_argument("--budget-tokens", type=int, default=400)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--include-all", action="store_true")
    parser.add_argument("--include-stale", action="store_true")
    return parser


def modern_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    target_arguments(parser)
    sub = parser.add_subparsers(dest="command", required=True)
    p_search = sub.add_parser("search")
    p_search.add_argument("--query", required=True)
    p_search.add_argument("--limit", type=int, default=3)
    p_search.add_argument("--budget-tokens", type=int, default=400)
    p_search.add_argument("--include-all", action="store_true")
    p_search.add_argument("--include-stale", action="store_true")
    p_hydrate = sub.add_parser("hydrate")
    p_hydrate.add_argument("--id", required=True)
    p_hydrate.add_argument("--budget-tokens", type=int, default=1200)
    return parser


def positional_command(arguments: list[str]) -> str | None:
    value_options = {
        "--project",
        "--repo",
        "--project-id",
        "--host",
        "--host-project-id",
    }
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument in value_options:
            index += 2
            continue
        if any(argument.startswith(f"{option}=") for option in value_options):
            index += 1
            continue
        if argument == "--json":
            index += 1
            continue
        if argument in {
            "--query",
            "--budget-tokens",
            "--limit",
            "--include-all",
            "--include-stale",
            "--id",
        } or any(
            argument.startswith(f"{option}=")
            for option in (
                "--query",
                "--budget-tokens",
                "--limit",
                "--id",
            )
        ):
            return None
        if not argument.startswith("-"):
            return argument if argument in {"search", "hydrate"} else None
        index += 1
    return None


def main() -> int:
    modern = positional_command(sys.argv[1:]) is not None
    parser = modern_parser() if modern else legacy_parser()
    args = parser.parse_args()
    args.command = getattr(args, "command", "search")
    if getattr(args, "budget_tokens", 1) < 1:
        parser.error("--budget-tokens must be positive")
    if args.command == "search" and not 1 <= args.limit <= 20:
        parser.error("--limit must be between 1 and 20")
    try:
        project_id, base = resolve(
            args.project, args.project_id, args.host, args.host_project_id
        )
        if args.command == "hydrate":
            result = {
                "entry": hydrate(base, args.id, args.budget_tokens),
                "project_id": project_id,
            }
        else:
            entries, used = search(
                base,
                args.query,
                args.limit,
                args.include_all,
                args.include_stale,
                args.budget_tokens,
            )
            result = {
                "budget_tokens": args.budget_tokens,
                "entries": entries,
                "estimated_tokens": used,
                "project_id": project_id,
                "query": args.query,
            }
        if args.json:
            print(json.dumps(result, sort_keys=True, ensure_ascii=False))
        elif args.command == "hydrate":
            print(result["entry"]["content"])
        else:
            for entry in result["entries"]:
                print(
                    f"{entry['id']}\t{entry['kind']}\t{entry['title']}\t"
                    f"{entry['summary']}"
                )
        return 0
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
