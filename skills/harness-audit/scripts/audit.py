#!/usr/bin/env python3
"""Audit and explicitly migrate global Harness state."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Iterator
import unicodedata
import uuid


SCHEMA_VERSION = 2
DEFAULT_MAX_ACTIVE_SESSIONS = 8
DEFAULT_MEMORY_CARD_BUDGET = 1200
SEMANTIC_FIELDS = ("title", "summary", "read_when", "tags", "artifact_refs")
REQUIRED_DIRS = (
    "memory/candidates", "memory/topics", "memory/archive",
    "sessions/active", "sessions/closed", "references/product",
    "references/technical", "references/operations", "references/investigations",
    "workspace", "worktrees",
)
REQUIRED_FILES = (
    "index.md", "project.md", "decisions.md", "manifest.json",
    "memory/catalog.jsonl", "workspace/policy.json", "worktrees/policy.toml",
)


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
    return json.loads(path.read_text(encoding="utf-8"))


def valid_project_id(value: str) -> str:
    try:
        return str(uuid.UUID(value))
    except (ValueError, AttributeError) as exc:
        raise RuntimeError(f"Invalid Harness project id: {value}") from exc


def git(repo: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or "Git command failed")
    return result.stdout.strip()


def manifests() -> list[tuple[Path, dict]]:
    result: list[tuple[Path, dict]] = []
    for base in sorted((home() / "projects").glob("*")):
        if not base.is_dir():
            continue
        try:
            result.append((base, load(base / "manifest.json")))
        except (OSError, json.JSONDecodeError):
            continue
    return result


def path_bindings(manifest: dict) -> list[Path]:
    values = [
        binding.get("value", "")
        for binding in manifest.get("bindings", [])
        if isinstance(binding, dict) and binding.get("type") == "path"
    ]
    values.extend(manifest.get("repository_paths", []))
    result: list[Path] = []
    for value in values:
        try:
            candidate = Path(str(value)).expanduser()
            if candidate.is_absolute():
                result.append(candidate.resolve())
        except (OSError, ValueError):
            continue
    return sorted(set(result), key=lambda path: (-len(path.parts), str(path)))


def path_contains(parent: Path, child: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def resolve_path(value: str) -> Path:
    candidate = Path(value).expanduser().resolve()
    matches: list[tuple[int, Path]] = []
    for base, manifest in manifests():
        for binding in path_bindings(manifest):
            if path_contains(binding, candidate):
                matches.append((len(binding.parts), base))
                break
    if not matches:
        raise RuntimeError(f"Path is not linked to Harness: {candidate}")
    matches.sort(key=lambda item: (-item[0], str(item[1])))
    if len(matches) > 1 and matches[0][0] == matches[1][0]:
        raise RuntimeError(f"Path has ambiguous Harness bindings: {candidate}")
    return matches[0][1]


def current_project(repo_path: str) -> Path:
    candidate = Path(repo_path).expanduser().resolve()
    with contextlib.suppress(RuntimeError):
        return resolve_path(str(candidate))
    root_text = git(candidate, "rev-parse", "--show-toplevel")
    repo = Path(root_text).resolve()
    project_id = git(repo, "config", "--local", "--get", "harness.project-id")
    if not project_id:
        raise RuntimeError("Repository is not linked to Harness")
    return home() / "projects" / valid_project_id(project_id)


def resolve_project_id(project_id: str) -> Path:
    base = home() / "projects" / valid_project_id(project_id)
    if not base.is_dir():
        raise RuntimeError(f"Harness project does not exist: {project_id}")
    return base


def age_days(timestamp: str) -> int | None:
    try:
        value = dt.datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        return (dt.datetime.now(dt.timezone.utc) - value).days
    except (ValueError, TypeError):
        return None


def normalized(value: object) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))


def concise(value: object, limit: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    clipped = text[: max(1, limit - 1)].rstrip()
    return clipped + "…"


def fallback_title(item: dict, kind: str) -> str:
    for field in ("title", "task", "summary", "topic"):
        value = concise(item.get(field), 120)
        if value:
            return value
    identifier = str(item.get("id", "unknown"))[:8]
    return f"Unlabeled {kind} {identifier}"


def fallback_summary(item: dict) -> str:
    return concise(item.get("summary") or item.get("content") or item.get("task"), 320)


def fallback_read_when(item: dict, kind: str) -> str:
    current = concise(item.get("read_when"), 240)
    if current:
        return current
    if kind == "session" and not any(
        concise(item.get(field), 1) for field in ("task", "summary", "next_step")
    ):
        return "only when explicitly resuming this session"
    topic = concise(item.get("topic") or item.get("task") or item.get("title"), 100)
    return f"when work involves {topic}" if topic else f"when explicitly retrieving this {kind}"


def normalized_strings(value: object, field: str = "list field") -> list[str]:
    if value is None:
        values: list[object] = []
    elif isinstance(value, list):
        values = value
    elif isinstance(value, (str, int, float, bool)):
        values = [value]
    else:
        raise RuntimeError(f"{field} must be a list or scalar value")
    return sorted({concise(item, 240) for item in values if concise(item, 240)})


def catalog_strings(value: object) -> list[str]:
    try:
        return [str(item) for item in value if str(item).strip()]
    except TypeError:
        return []


def migrate_record(item: dict, kind: str, status: str | None = None) -> dict:
    result = dict(item)
    result["schema_version"] = SCHEMA_VERSION
    result["title"] = fallback_title(result, kind)
    result["summary"] = fallback_summary(result)
    result["read_when"] = fallback_read_when(result, kind)
    result["tags"] = normalized_strings(result.get("tags", []), "tags")
    result["artifact_refs"] = normalized_strings(
        result.get("artifact_refs", []), "artifact_refs"
    )
    if status:
        result["status"] = status
    return result


def normalize_binding(binding: object) -> dict | None:
    if not isinstance(binding, dict):
        return None
    kind = binding.get("type")
    value = binding.get("value")
    if kind not in ("path", "git", "host") or not isinstance(value, str) or not value.strip():
        return None
    result = {"type": kind, "value": value.strip()}
    if kind == "path":
        candidate = Path(value).expanduser()
        result["value"] = str(candidate.resolve())
        if binding.get("primary"):
            result["primary"] = True
    elif kind == "host":
        host = binding.get("host")
        if not isinstance(host, str) or not host.strip():
            return None
        result["host"] = host.strip().lower()
    return result


def binding_key(binding: dict) -> tuple[str, str, str]:
    return (binding["type"], binding.get("host", ""), binding["value"])


def migrate_manifest(manifest: dict) -> dict:
    result = dict(manifest)
    raw_bindings = list(manifest.get("bindings", []))
    raw_bindings.extend(
        {"type": "path", "value": path}
        for path in manifest.get("repository_paths", [])
        if isinstance(path, str)
    )
    raw_bindings.extend(
        {"type": "git", "value": remote}
        for remote in manifest.get("remote_urls", [])
        if isinstance(remote, str)
    )
    bindings: dict[tuple[str, str, str], dict] = {}
    for raw in raw_bindings:
        binding = normalize_binding(raw)
        if binding:
            bindings[binding_key(binding)] = binding
    path_entries = sorted(
        (entry for entry in bindings.values() if entry["type"] == "path"),
        key=lambda entry: (not entry.get("primary", False), entry["value"]),
    )
    other_entries = sorted(
        (entry for entry in bindings.values() if entry["type"] != "path"),
        key=binding_key,
    )
    if path_entries and not any(entry.get("primary") for entry in path_entries):
        path_entries[0]["primary"] = True
    ordered = path_entries + other_entries
    result["schema_version"] = SCHEMA_VERSION
    result["bindings"] = ordered
    result["repository_paths"] = sorted(
        entry["value"] for entry in ordered if entry["type"] == "path"
    )
    result["remote_urls"] = sorted(
        entry["value"] for entry in ordered if entry["type"] == "git"
    )
    return result


def memory_paths(base: Path) -> Iterator[Path]:
    yield from sorted((base / "memory/candidates").glob("*.json"))
    yield from sorted((base / "memory/topics").glob("*/*.json"))
    yield from sorted((base / "memory/archive").glob("*.json"))


def session_paths(base: Path) -> Iterator[tuple[str, Path]]:
    for status in ("active", "dormant", "closed"):
        yield from ((status, path) for path in sorted((base / "sessions" / status).glob("*.json")))


def canonical_record_id(base: Path, item: dict, kind: str, path: Path) -> tuple[str, bool]:
    raw = str(item.get("id", "")).strip()
    try:
        return str(uuid.UUID(raw)), False
    except (ValueError, AttributeError):
        identifier = str(uuid.uuid5(
            uuid.UUID(base.name),
            f"legacy-{kind}:{path.relative_to(base)}:{raw}",
        ))
        return identifier, True


def collision_id(
    base: Path,
    kind: str,
    path: Path,
    original_id: str,
    reserved: set[Path],
    target_for_id,
    reserved_ids: set[str] | None = None,
) -> tuple[str, Path]:
    attempt = 0
    while True:
        suffix = f":{attempt}" if attempt else ""
        identifier = str(uuid.uuid5(
            uuid.UUID(base.name),
            f"duplicate-{kind}:{path.relative_to(base)}:{original_id}{suffix}",
        ))
        target = target_for_id(identifier)
        if target not in reserved and (
            reserved_ids is None or identifier not in reserved_ids
        ):
            return identifier, target
        attempt += 1


def effective_session_status(item: dict, current: str, stale_days: int) -> str:
    if current != "active":
        return current
    empty = not any(concise(item.get(field), 1) for field in ("task", "summary", "next_step"))
    age = age_days(item.get("last_seen_at") or item.get("updated_at") or item.get("created_at", ""))
    if empty or (age is not None and age >= stale_days):
        return "dormant"
    return "active"


def catalog_row(kind: str, status: str, path: Path, base: Path, item: dict) -> dict:
    row = {
        "artifact_refs": catalog_strings(item.get("artifact_refs", [])),
        "id": str(item.get("id", path.stem)),
        "kind": kind,
        "path": str(path.relative_to(base)),
        "read_when": str(item.get("read_when", "")),
        "schema_version": SCHEMA_VERSION,
        "status": str(item.get("status") or status),
        "summary": str(item.get("summary") or item.get("task") or "")[:320],
        "tags": catalog_strings(item.get("tags", [])),
        "title": str(
            item.get("title")
            or item.get("topic")
            or item.get("task")
            or f"{kind} {str(item.get('id', ''))[:8]}"
        )[:160],
        "updated_at": str(item.get("updated_at", "")),
    }
    if kind == "memory":
        row.update({
            "confidence": str(item.get("confidence", "medium")),
            "review_after": str(item.get("review_after", "")),
            "topic": str(item.get("topic", "")),
        })
    return row


def expected_catalog(
    base: Path,
    findings: list[dict],
    overrides: dict[Path, dict] | None = None,
) -> str:
    overrides = overrides or {}
    rows: list[dict] = []
    for status in ("active", "dormant", "closed"):
        for path in sorted((base / "sessions" / status).glob("*.json")):
            try:
                item = overrides.get(path, load(path))
            except (OSError, json.JSONDecodeError) as exc:
                findings.append(finding("error", "invalid-json", path, str(exc)))
                continue
            rows.append(catalog_row("session", status, path, base, item))
    for path in sorted((base / "memory/topics").glob("*/*.json")):
        try:
            item = overrides.get(path, load(path))
        except (OSError, json.JSONDecodeError) as exc:
            findings.append(finding("error", "invalid-json", path, str(exc)))
            continue
        if item.get("status") != "active":
            findings.append(finding(
                "warning", "inactive-topic-record", path,
                "Non-active memory belongs in archive",
            ))
            continue
        for field in ("last_verified_at", "read_when", "review_after"):
            if not item.get(field):
                findings.append(finding(
                    "error", "missing-memory-field", path,
                    f"Active memory is missing {field}",
                ))
        review_age = age_days(item.get("review_after", ""))
        if review_age is not None and review_age >= 0:
            findings.append(finding(
                "warning", "stale-memory", path,
                f"Memory review date passed {review_age} days ago",
            ))
        rows.append(catalog_row("memory", "active", path, base, item))
    rows.sort(key=lambda row: (row["kind"], row["path"]))
    return "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows)


def finding(severity: str, code: str, path: str | Path, message: str, **details: object) -> dict:
    result = {
        "severity": severity,
        "code": code,
        "path": str(path),
        "message": message,
    }
    if details:
        result["details"] = details
    return result


def valid_bindings(manifest: dict, base: Path, findings: list[dict]) -> None:
    bindings = manifest.get("bindings")
    if not isinstance(bindings, list) or not bindings:
        severity = "error" if manifest.get("schema_version") == SCHEMA_VERSION else "warning"
        findings.append(finding(
            severity, "missing-project-bindings", base / "manifest.json",
            "Manifest has no project-native bindings",
        ))
        return
    seen: set[tuple[str, str, str]] = set()
    primary_paths = 0
    for index, raw in enumerate(bindings):
        invalid_relative_path = (
            isinstance(raw, dict)
            and raw.get("type") == "path"
            and isinstance(raw.get("value"), str)
            and not Path(raw["value"]).expanduser().is_absolute()
        )
        binding = None if invalid_relative_path else normalize_binding(raw)
        location = f"{base / 'manifest.json'}#bindings[{index}]"
        if binding is None:
            findings.append(finding(
                "error", "invalid-project-binding", location,
                "Binding must have a supported type and valid value",
            ))
            continue
        key = binding_key(binding)
        if key in seen:
            findings.append(finding(
                "warning", "duplicate-project-binding", location,
                "Binding duplicates an earlier entry",
            ))
        seen.add(key)
        if binding["type"] == "path":
            primary_paths += int(bool(binding.get("primary")))
            path = Path(binding["value"])
            if not path.exists():
                findings.append(finding(
                    "warning", "missing-project-path", path,
                    "Registered project path no longer exists",
                ))
            for forbidden in (".harness", ".project-harness"):
                if (path / forbidden).exists():
                    findings.append(finding(
                        "warning", "project-footprint", path / forbidden,
                        "Harness-owned state must remain global",
                    ))
    if primary_paths > 1:
        findings.append(finding(
            "error", "multiple-primary-paths", base / "manifest.json",
            "At most one path binding may be primary",
        ))


def semantic_findings(
    base: Path,
    findings: list[dict],
    stale_days: int,
    max_active_sessions: int,
) -> None:
    titles: dict[tuple[str, str], Path] = {}
    ids: dict[tuple[str, str], Path] = {}
    active_count = 0
    reported_total = 0
    rendered_total = 0
    cards = 0

    records: list[tuple[str, str, Path, dict]] = []
    for status, path in session_paths(base):
        try:
            records.append(("session", status, path, load(path)))
        except (OSError, json.JSONDecodeError) as exc:
            findings.append(finding("error", "invalid-json", path, str(exc)))
    for path in memory_paths(base):
        try:
            item = load(path)
            status = str(item.get("status", ""))
            records.append(("memory", status, path, item))
        except (OSError, json.JSONDecodeError) as exc:
            findings.append(finding("error", "invalid-json", path, str(exc)))

    for kind, location_status, path, item in records:
        identifier = str(item.get("id", ""))
        try:
            canonical_identifier = str(uuid.UUID(identifier))
        except (ValueError, AttributeError):
            canonical_identifier = ""
            findings.append(finding(
                "error", "non-hydratable-record-id", path,
                "Record id is not a canonical UUID and cannot be hydrated reliably",
                record_id=identifier,
            ))
        hydratable_memory = (
            kind == "memory"
            and path.parent.parent == base / "memory/topics"
        )
        if (
            canonical_identifier
            and (kind == "session" or hydratable_memory)
            and path.stem != canonical_identifier
        ):
            findings.append(finding(
                "error", "record-path-id-mismatch", path,
                "Record filename does not match its canonical id",
                record_id=canonical_identifier,
            ))
        identity_scope = (
            "session"
            if kind == "session"
            else "live-memory" if location_status in ("active", "candidate") else ""
        )
        identity_key = (identity_scope, identifier)
        if identifier and identity_scope:
            if identity_key in ids:
                findings.append(finding(
                    "error", "duplicate-record-id", path,
                    "Record id duplicates another stored record",
                    first_path=str(ids[identity_key]),
                ))
            else:
                ids[identity_key] = path
        for field in SEMANTIC_FIELDS:
            value = item.get(field)
            if field in ("tags", "artifact_refs") and value is None:
                findings.append(finding(
                    "warning", "missing-semantic-field", path,
                    f"Record is missing semantic field {field}",
                    field=field,
                ))
            elif field in ("tags", "artifact_refs") and not isinstance(value, list):
                findings.append(finding(
                    "warning", "invalid-semantic-field", path,
                    f"Semantic field {field} must be a list",
                    field=field,
                ))
            elif not value and field not in ("tags", "artifact_refs", "summary"):
                findings.append(finding(
                    "warning", "missing-semantic-field", path,
                    f"Record is missing semantic field {field}",
                    field=field,
                ))
        title = normalized(item.get("title"))
        if title:
            title_key = (kind, title)
            if title_key in titles:
                findings.append(finding(
                    "warning", "duplicate-semantic-title", path,
                    "Semantic title duplicates another record",
                    first_path=str(titles[title_key]),
                ))
            else:
                titles[title_key] = path

        if kind == "session":
            if location_status == "active":
                active_count += 1
                empty = not any(
                    concise(item.get(field), 1)
                    for field in ("task", "summary", "next_step")
                )
                if empty:
                    findings.append(finding(
                        "warning", "empty-active-session", path,
                        "Active session has no task, summary, or next step",
                    ))
                age = age_days(
                    item.get("last_seen_at")
                    or item.get("updated_at")
                    or item.get("created_at", "")
                )
                if age is None:
                    findings.append(finding(
                        "error", "invalid-session-time", path,
                        "Session timestamp is invalid",
                    ))
                elif age >= stale_days:
                    findings.append(finding(
                        "warning", "stale-active-session", path,
                        f"Active session has not been seen for {age} days",
                    ))
            elif location_status == "dormant":
                findings.append(finding(
                    "info", "dormant-session", path,
                    "Dormant session remains available for explicit retrieval",
                ))

        if kind == "memory" and location_status == "active":
            content_tokens = estimated_tokens(str(item.get("content", "")))
            if content_tokens > DEFAULT_MEMORY_CARD_BUDGET:
                findings.append(finding(
                    "warning", "oversized-memory-content", path,
                    "Memory content exceeds the default card budget and should be hydrated on demand",
                    estimated_tokens=content_tokens,
                ))
                if not concise(item.get("summary"), 1):
                    findings.append(finding(
                        "warning", "unrecallable-memory", path,
                        "Oversized memory has no compact semantic summary",
                    ))

        if kind == "session" or location_status == "active":
            content = (
                str(item.get("summary") or item.get("content") or item.get("task") or "")
            )
            title_text = str(item.get("title") or item.get("topic") or item.get("task") or "")
            rendered = (
                f"## {title_text}\n\nSource: {path.relative_to(base)}\n\n"
                f"{content}\n\nRead when: {item.get('read_when', '')}"
            )
            reported_total += estimated_tokens(content)
            rendered_total += estimated_tokens(rendered)
            cards += 1

    if active_count > max_active_sessions:
        findings.append(finding(
            "warning", "excess-active-sessions", base / "sessions/active",
            f"Project has {active_count} active sessions; limit is {max_active_sessions}",
            active_sessions=active_count,
            limit=max_active_sessions,
        ))
    if cards and rendered_total > reported_total:
        findings.append(finding(
            "info", "recall-budget-overhead", base,
            "Rendered recall cards cost more than content-only accounting",
            cards=cards,
            rendered_tokens=rendered_total,
            reported_tokens=reported_total,
            unreported_tokens=rendered_total - reported_total,
        ))


def estimated_tokens(value: str) -> int:
    return max(1, (len(value) + 3) // 4)


def workspace_findings(base: Path, findings: list[dict]) -> None:
    workspace = base / "workspace"
    try:
        policy = load(workspace / "policy.json")
        local_policy = workspace / "policy.local.json"
        if local_policy.is_file():
            policy.update(load(local_policy))
        max_age_days = max(1, int(policy.get("max_age_days", 7)))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        max_age_days = 7
        findings.append(finding(
            "error", "invalid-workspace-policy", workspace / "policy.json", str(exc),
        ))
    cutoff = dt.datetime.now().timestamp() - max_age_days * 86400
    for path in sorted(workspace.rglob("*")):
        if path in (workspace / "policy.json", workspace / "policy.local.json") or path.is_dir():
            continue
        with contextlib.suppress(OSError):
            if path.stat().st_mtime < cutoff:
                findings.append(finding(
                    "warning", "expired-workspace-file", path,
                    "Workspace file is past the cleanup age",
                ))


def audit_project(
    base: Path,
    repair_catalog: bool,
    stale_days: int,
    max_active_sessions: int,
) -> dict:
    findings: list[dict] = []
    try:
        manifest = load(base / "manifest.json")
        manifest_id = valid_project_id(manifest.get("id", ""))
        if manifest_id != base.name:
            findings.append(finding(
                "error", "identity-mismatch", base,
                "Manifest id does not match directory",
            ))
        if manifest.get("schema_version") != SCHEMA_VERSION:
            findings.append(finding(
                "warning", "legacy-schema", base / "manifest.json",
                f"Manifest uses schema {manifest.get('schema_version')}; current schema is {SCHEMA_VERSION}",
            ))
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        manifest = {}
        findings.append(finding(
            "error", "invalid-manifest", base / "manifest.json", str(exc),
        ))

    for relative in REQUIRED_DIRS:
        if not (base / relative).is_dir():
            findings.append(finding(
                "error", "missing-directory", base / relative,
                "Required directory is missing",
            ))
    if manifest.get("schema_version") == SCHEMA_VERSION and not (base / "sessions/dormant").is_dir():
        findings.append(finding(
            "error", "missing-directory", base / "sessions/dormant",
            "Required directory is missing",
        ))
    for relative in REQUIRED_FILES:
        if not (base / relative).is_file():
            findings.append(finding(
                "error", "missing-file", base / relative,
                "Required file is missing",
            ))

    valid_bindings(manifest, base, findings)
    semantic_findings(base, findings, stale_days, max_active_sessions)
    workspace_findings(base, findings)

    expected = expected_catalog(base, findings)
    catalog = base / "memory/catalog.jsonl"
    actual = catalog.read_text(encoding="utf-8") if catalog.is_file() else ""
    if actual != expected:
        severity = "info" if repair_catalog else "error"
        findings.append(finding(
            severity, "catalog-drift", catalog,
            "Catalog was rebuilt" if repair_catalog
            else "Catalog differs from active topic memory",
        ))
        if repair_catalog:
            atomic_write(catalog, expected)

    lock_path = base / ".lock"
    if lock_path.exists():
        age_seconds = max(0, dt.datetime.now().timestamp() - lock_path.stat().st_mtime)
        if age_seconds > 300:
            findings.append(finding(
                "warning", "stale-lock", lock_path,
                "Lock is older than five minutes",
            ))

    counts = {
        "active_memory": len(list((base / "memory/topics").glob("*/*.json"))),
        "active_sessions": len(list((base / "sessions/active").glob("*.json"))),
        "archived_memory": len(list((base / "memory/archive").glob("*.json"))),
        "candidates": len(list((base / "memory/candidates").glob("*.json"))),
        "closed_sessions": len(list((base / "sessions/closed").glob("*.json"))),
        "dormant_sessions": len(list((base / "sessions/dormant").glob("*.json"))),
    }
    findings.sort(key=lambda item: (
        {"error": 0, "warning": 1, "info": 2}[item["severity"]],
        item["code"],
        item["path"],
    ))
    return {"counts": counts, "findings": findings, "project_id": base.name}


def plan_project_migration(base: Path, stale_days: int) -> dict:
    operations: list[dict] = []
    try:
        manifest = load(base / "manifest.json")
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot migrate invalid manifest {base / 'manifest.json'}: {exc}") from exc
    migrated_manifest = migrate_manifest(manifest)
    manifest_path = base / "manifest.json"
    if migrated_manifest != manifest:
        operations.append({
            "action": "update", "path": str(manifest_path.relative_to(base)),
            "reason": "manifest-schema-v2", "_value": migrated_manifest,
        })

    dormant = base / "sessions/dormant"
    if not dormant.is_dir():
        operations.append({
            "action": "create-directory", "path": "sessions/dormant",
            "reason": "session-status-layout",
        })

    session_records: list[dict] = []
    for current, path in session_paths(base):
        try:
            item = load(path)
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Cannot migrate invalid session {path}: {exc}") from exc
        status = effective_session_status(item, current, stale_days)
        migrated = migrate_record(item, "session", status)
        raw_identifier = str(item.get("id", "")).strip()
        identifier, was_legacy = canonical_record_id(base, item, "session", path)
        migrated["id"] = identifier
        if was_legacy:
            migrated["legacy_id"] = raw_identifier
        session_records.append({
            "current": current,
            "identifier": identifier,
            "item": item,
            "migrated": migrated,
            "path": path,
            "raw_identifier": raw_identifier,
            "status": status,
        })

    status_priority = {"active": 0, "dormant": 1, "closed": 2}
    session_records.sort(key=lambda record: (
        status_priority[record["current"]], str(record["path"])
    ))
    reserved_ids: set[str] = set()
    reserved_targets: set[Path] = set()
    session_catalog_records: list[tuple[str, Path, dict]] = []
    for record in session_records:
        identifier = record["identifier"]
        target_for_id = lambda value, status=record["status"]: (
            base / "sessions" / status / f"{value}.json"
        )
        target = target_for_id(identifier)
        if identifier in reserved_ids or target in reserved_targets:
            identifier, target = collision_id(
                base,
                "session",
                record["path"],
                identifier,
                reserved_targets,
                target_for_id,
                reserved_ids,
            )
            record["migrated"]["legacy_id"] = record["raw_identifier"]
            record["migrated"]["id"] = identifier
        reserved_ids.add(identifier)
        reserved_targets.add(target)
        item = record["item"]
        migrated = record["migrated"]
        path = record["path"]
        session_catalog_records.append((record["status"], target, migrated))
        if migrated != item or target != path:
            operations.append({
                "action": "move" if target != path else "update",
                "path": str(path.relative_to(base)),
                "target": str(target.relative_to(base)),
                "reason": "session-schema-v2",
                "_value": migrated,
                "_source": path,
                "_target": target,
            })

    memory_records: list[dict] = []
    for path in memory_paths(base):
        try:
            item = load(path)
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Cannot migrate invalid memory {path}: {exc}") from exc
        migrated = migrate_record(item, "memory")
        raw_identifier = str(item.get("id", "")).strip()
        identifier, was_legacy = canonical_record_id(base, item, "memory", path)
        migrated["id"] = identifier
        if was_legacy:
            migrated["legacy_id"] = raw_identifier
        relative = path.relative_to(base)
        area = relative.parts[1]
        priority = 0 if area == "topics" else 1 if area == "candidates" else 2
        memory_records.append({
            "area": area,
            "identifier": identifier,
            "item": item,
            "migrated": migrated,
            "path": path,
            "priority": priority,
            "raw_identifier": raw_identifier,
        })

    memory_records.sort(key=lambda record: (record["priority"], str(record["path"])))
    reserved_live_ids: set[str] = set()
    reserved_memory_targets: set[Path] = set()
    topic_records: list[tuple[Path, dict]] = []
    for record in memory_records:
        path = record["path"]
        area = record["area"]
        identifier = record["identifier"]

        def memory_target(value: str) -> Path:
            if area == "topics":
                return path.parent / f"{value}.json"
            if area == "candidates":
                return base / "memory/candidates" / f"{value}.json"
            prefix = (
                "candidate-" if path.name.startswith("candidate-")
                else "memory-" if path.name.startswith("memory-")
                else ""
            )
            return base / "memory/archive" / f"{prefix}{value}.json"

        target = memory_target(identifier)
        live = area in ("topics", "candidates")
        if target in reserved_memory_targets or (live and identifier in reserved_live_ids):
            identifier, target = collision_id(
                base,
                "memory",
                path,
                identifier,
                reserved_memory_targets,
                memory_target,
                reserved_live_ids if live else None,
            )
            record["migrated"]["legacy_id"] = record["raw_identifier"]
            record["migrated"]["id"] = identifier
        if live:
            reserved_live_ids.add(identifier)
        reserved_memory_targets.add(target)
        item = record["item"]
        migrated = record["migrated"]
        if migrated != item:
            operations.append({
                "action": "move" if target != path else "update",
                "path": str(path.relative_to(base)),
                "target": str(target.relative_to(base)),
                "reason": "memory-schema-v2",
                "_value": migrated,
                "_source": path,
                "_target": target,
            })
        elif target != path:
            operations.append({
                "action": "move",
                "path": str(path.relative_to(base)),
                "target": str(target.relative_to(base)),
                "reason": "memory-canonical-id",
                "_value": migrated,
                "_source": path,
                "_target": target,
            })
        if area == "topics" and migrated.get("status") == "active":
            for field in ("last_verified_at", "read_when", "review_after"):
                if not migrated.get(field):
                    raise RuntimeError(
                        f"Cannot rebuild catalog: active memory {path} is missing {field}"
                    )
            topic_records.append((target, migrated))

    rows = [
        catalog_row("session", status, path, base, item)
        for status, path, item in session_catalog_records
    ]
    rows.extend(
        catalog_row("memory", "active", path, base, item)
        for path, item in topic_records
    )
    rows.sort(key=lambda row: (row["kind"], row["path"]))
    expected = "".join(
        json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows
    )
    catalog = base / "memory/catalog.jsonl"
    actual = catalog.read_text(encoding="utf-8") if catalog.is_file() else ""
    if actual != expected:
        operations.append({
            "action": "update", "path": "memory/catalog.jsonl",
            "reason": "catalog-schema-v2", "_text": expected, "_target": catalog,
        })
    return {"project_id": base.name, "base": base, "operations": operations}


def public_plan(plan: dict) -> dict:
    operations: list[dict] = []
    for item in plan["operations"]:
        operations.append({
            key: value for key, value in item.items() if not key.startswith("_")
        })
    return {
        "changes": len(operations),
        "operations": operations,
        "project_id": plan["project_id"],
    }


@contextlib.contextmanager
def migration_lock(path: Path, timeout: float = 5.0) -> Iterator[None]:
    deadline = time.monotonic() + timeout
    while True:
        try:
            path.mkdir(parents=True)
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise RuntimeError(f"Timed out waiting for Harness migration lock: {path}")
            time.sleep(0.05)
    try:
        yield
    finally:
        with contextlib.suppress(OSError):
            path.rmdir()


def backup_root() -> Path:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = home() / "backups" / f"schema-v2-{stamp}"
    candidate = base
    suffix = 1
    while candidate.exists():
        candidate = Path(f"{base}-{suffix}")
        suffix += 1
    return candidate


def backup_projects(root: Path, plans: list[dict]) -> None:
    for plan in plans:
        source = plan["base"]
        target = root / "projects" / plan["project_id"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(
            source,
            target,
            ignore=shutil.ignore_patterns(".lock", ".migration.lock"),
        )


def apply_plan(plan: dict) -> None:
    base: Path = plan["base"]
    for operation in plan["operations"]:
        if operation["action"] == "create-directory":
            (base / operation["path"]).mkdir(parents=True, exist_ok=True)
    final_targets = {
        operation["_target"]
        for operation in plan["operations"]
        if "_target" in operation
    }
    for operation in plan["operations"]:
        if operation["action"] == "create-directory":
            continue
        target = operation.get("_target", base / operation["path"])
        if "_text" in operation:
            atomic_write(target, operation["_text"])
        else:
            write_json(target, operation["_value"])
    for operation in plan["operations"]:
        source = operation.get("_source")
        if (
            operation["action"] == "move"
            and source is not None
            and source not in final_targets
        ):
            with contextlib.suppress(FileNotFoundError):
                source.unlink()


def migrate_projects(bases: list[Path], stale_days: int, dry_run: bool) -> dict:
    plans = [plan_project_migration(base, stale_days) for base in bases]
    changed = [plan for plan in plans if plan["operations"]]
    backup: Path | None = None
    if changed and not dry_run:
        lock_path = home() / ".migration.lock"
        with migration_lock(lock_path):
            plans = [plan_project_migration(base, stale_days) for base in bases]
            changed = [plan for plan in plans if plan["operations"]]
            if changed:
                backup = backup_root()
                backup_projects(backup, changed)
                for plan in changed:
                    apply_plan(plan)
    return {
        "backup_dir": str(backup) if backup else None,
        "changed_projects": len(changed),
        "dry_run": dry_run,
        "projects": [public_plan(plan) for plan in plans],
    }


def select_bases(args: argparse.Namespace) -> list[Path]:
    if args.all:
        return sorted(path for path in (home() / "projects").glob("*") if path.is_dir())
    if args.project_id:
        return [resolve_project_id(args.project_id)]
    if args.path:
        return [resolve_path(args.path)]
    return [current_project(args.repo)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--repo")
    target.add_argument("--project", "--path", dest="path")
    target.add_argument("--project-id")
    target.add_argument("--all", action="store_true")
    parser.add_argument("--repair-catalog", action="store_true")
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--stale-session-days", type=int, default=14)
    parser.add_argument("--max-active-sessions", type=int, default=DEFAULT_MAX_ACTIVE_SESSIONS)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.dry_run and not args.migrate:
        parser.error("--dry-run requires --migrate")
    if args.repair_catalog and args.migrate:
        parser.error("--repair-catalog and --migrate are mutually exclusive")
    if args.stale_session_days < 1:
        parser.error("--stale-session-days must be positive")
    if args.max_active_sessions < 1:
        parser.error("--max-active-sessions must be positive")
    try:
        bases = select_bases(args)
        migration = (
            migrate_projects(bases, args.stale_session_days, args.dry_run)
            if args.migrate else None
        )
        projects = [
            audit_project(
                base,
                args.repair_catalog,
                args.stale_session_days,
                args.max_active_sessions,
            )
            for base in bases
        ]
        errors = sum(
            1 for project in projects for item in project["findings"]
            if item["severity"] == "error"
        )
        result = {
            "errors": errors,
            "harness_home": str(home()),
            "migration": migration,
            "projects": projects,
        }
        print(
            json.dumps(result, sort_keys=True, ensure_ascii=False)
            if args.json
            else json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False)
        )
        return 1 if errors else 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
