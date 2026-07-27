#!/usr/bin/env python3
"""Initialize, link, and resolve project-native Harness identities."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Iterator
import uuid

from defaults import refresh_global, refresh_project


SCHEMA_VERSION = 2


def harness_home() -> Path:
    return Path(os.environ.get("HARNESS_HOME", "~/.harness")).expanduser().resolve()


def utc_now() -> str:
    import datetime

    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def valid_project_id(value: str) -> str:
    try:
        return str(uuid.UUID(value))
    except (ValueError, AttributeError) as exc:
        raise RuntimeError(f"Invalid Harness project id: {value}") from exc


def project_path(value: str | Path) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.exists() or not path.is_dir():
        raise RuntimeError(f"Project directory does not exist: {path}")
    return path


def git(path: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), *args], text=True, capture_output=True, check=False
        )
    except OSError:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def git_root(path: Path) -> Path | None:
    value = git(path, "rev-parse", "--show-toplevel")
    return Path(value).resolve() if value else None


def git_remotes(path: Path) -> list[str]:
    root = git_root(path)
    if root is None:
        return []
    values = {
        value
        for name in git(root, "remote").splitlines()
        if (value := git(root, "remote", "get-url", name))
    }
    return sorted(values)


def legacy_git_id(path: Path) -> str | None:
    root = git_root(path)
    if root is None:
        return None
    value = git(root, "config", "--local", "--get", "harness.project-id")
    if not value:
        return None
    try:
        return valid_project_id(value)
    except RuntimeError:
        return None


def atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temp_name)


def write_json(path: Path, value: object) -> None:
    atomic_write(path, json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


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


def project_dir(project_id: str) -> Path:
    return harness_home() / "projects" / valid_project_id(project_id)


def seed(path: Path, content: str) -> None:
    if not path.exists():
        atomic_write(path, content.rstrip() + "\n")


def make_global_layout(home: Path) -> None:
    refresh_global(home, atomic_write)


def make_layout(base: Path) -> None:
    for relative in (
        "memory/candidates",
        "memory/topics",
        "memory/archive",
        "sessions/active",
        "sessions/dormant",
        "sessions/closed",
        "references/product",
        "references/technical",
        "references/operations",
        "references/investigations",
        "workspace",
        "worktrees",
    ):
        (base / relative).mkdir(parents=True, exist_ok=True)
    if not (base / "memory/catalog.jsonl").exists():
        atomic_write(base / "memory/catalog.jsonl", "")
    seed(
        base / "index.md",
        "# Harness project\n\n"
        "Read project orientation first. Search sessions and memory only when prior context "
        "can materially change the current task, then hydrate only selected records.\n",
    )
    seed(base / "project.md", "# Project\n\nRecord concise, agent-facing project orientation here.\n")
    seed(base / "decisions.md", "# Decisions\n\nRecord current provisional decisions here.\n")
    refresh_project(base, atomic_write)


def read_manifest(base: Path) -> dict:
    try:
        value = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Missing or invalid Harness manifest: {base}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"Invalid Harness manifest: {base}")
    return value


def binding_key(binding: dict) -> tuple[str, str, str]:
    return (
        str(binding.get("type", "")),
        str(binding.get("host", "")),
        str(binding.get("value", "")),
    )


def normalize_bindings(bindings: list[dict]) -> list[dict]:
    unique: dict[tuple[str, str, str], dict] = {}
    for raw in bindings:
        if not isinstance(raw, dict):
            continue
        kind = str(raw.get("type", ""))
        value = str(raw.get("value", "")).strip()
        if kind not in {"path", "git", "host"} or not value:
            continue
        item = {"type": kind, "value": value}
        if kind == "path":
            item["value"] = str(Path(value).expanduser().resolve())
            if raw.get("primary"):
                item["primary"] = True
        if kind == "host":
            host = str(raw.get("host", "")).strip().lower()
            if not host:
                continue
            item["host"] = host
        unique[binding_key(item)] = item
    paths = sorted(
        (item for item in unique.values() if item["type"] == "path"),
        key=lambda item: (not item.get("primary", False), item["value"]),
    )
    others = sorted(
        (item for item in unique.values() if item["type"] != "path"),
        key=binding_key,
    )
    if paths and not any(item.get("primary") for item in paths):
        paths[0]["primary"] = True
    return paths + others


def migrate_manifest(manifest: dict) -> tuple[dict, bool]:
    migrated = dict(manifest)
    bindings = list(migrated.get("bindings", []))
    bindings.extend(
        {"type": "path", "value": path}
        for path in migrated.get("repository_paths", [])
        if isinstance(path, str)
    )
    bindings.extend(
        {"type": "git", "value": remote}
        for remote in migrated.get("remote_urls", [])
        if isinstance(remote, str)
    )
    normalized = normalize_bindings(bindings)
    paths = sorted(item["value"] for item in normalized if item["type"] == "path")
    remotes = sorted(item["value"] for item in normalized if item["type"] == "git")
    migrated.update(
        {
            "bindings": normalized,
            "remote_urls": remotes,
            "repository_paths": paths,
            "schema_version": SCHEMA_VERSION,
        }
    )
    return migrated, migrated != manifest


def manifests() -> list[tuple[Path, dict]]:
    result: list[tuple[Path, dict]] = []
    for path in sorted((harness_home() / "projects").glob("*/manifest.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            valid_project_id(value["id"])
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, RuntimeError):
            continue
        result.append((path.parent, value))
    return result


def binding_owner_ids(
    path: Path | None = None,
    host: str = "",
    host_project_id: str = "",
) -> set[str]:
    owners: set[str] = set()
    for _, original in manifests():
        manifest, _ = migrate_manifest(original)
        identifier = valid_project_id(manifest["id"])
        for binding in manifest["bindings"]:
            if (
                path is not None
                and binding.get("type") == "path"
                and path_contains(binding["value"], path)
            ):
                owners.add(identifier)
            if (
                host
                and host_project_id
                and binding.get("type") == "host"
                and binding.get("host") == host.lower()
                and binding.get("value") == host_project_id
            ):
                owners.add(identifier)
    return owners


def ensure_bindings_available(
    project_id: str | None,
    path: Path | None,
    host: str,
    host_project_id: str,
) -> set[str]:
    owners = binding_owner_ids(path, host, host_project_id)
    if project_id:
        foreign = owners - {valid_project_id(project_id)}
        if foreign:
            raise RuntimeError(
                "Project path or host identity is already bound to another Harness project"
            )
    elif len(owners) > 1:
        raise RuntimeError(
            "Project path and host identity resolve to different Harness projects"
        )
    return owners


def path_contains(binding: str, target: Path) -> bool:
    try:
        target.relative_to(Path(binding).expanduser().resolve())
        return True
    except ValueError:
        return False


def resolve_project(
    path: Path | None = None,
    project_id: str | None = None,
    host: str = "",
    host_project_id: str = "",
) -> tuple[str, Path, dict, str]:
    if project_id:
        identifier = valid_project_id(project_id)
        base = project_dir(identifier)
        return identifier, base, read_manifest(base), "explicit-id"

    owners = binding_owner_ids(path, host, host_project_id)
    if len(owners) > 1:
        raise RuntimeError(
            "Project path and host identity resolve to different Harness projects"
        )
    if owners:
        identifier = next(iter(owners))
        base = project_dir(identifier)
        resolution = "host-binding" if host and host_project_id else "path-binding"
        return identifier, base, read_manifest(base), resolution

    records = manifests()
    if host and host_project_id:
        matches = []
        for base, original in records:
            manifest, _ = migrate_manifest(original)
            if any(
                binding.get("type") == "host"
                and binding.get("host") == host.lower()
                and binding.get("value") == host_project_id
                for binding in manifest["bindings"]
            ):
                matches.append((base, manifest))
        if len(matches) == 1:
            base, manifest = matches[0]
            return manifest["id"], base, manifest, "host-binding"
        if len(matches) > 1:
            raise RuntimeError("Ambiguous Harness host binding")

    if path is not None:
        candidates: list[tuple[int, Path, dict]] = []
        for base, original in records:
            manifest, _ = migrate_manifest(original)
            for binding in manifest["bindings"]:
                if binding.get("type") == "path" and path_contains(binding["value"], path):
                    candidates.append((len(Path(binding["value"]).parts), base, manifest))
        if candidates:
            candidates.sort(key=lambda item: (-item[0], item[2]["id"]))
            best = candidates[0]
            if len(candidates) > 1 and candidates[1][0] == best[0] and candidates[1][2]["id"] != best[2]["id"]:
                raise RuntimeError("Ambiguous Harness path binding")
            return best[2]["id"], best[1], best[2], "path-binding"

        legacy_id = legacy_git_id(path)
        if legacy_id:
            base = project_dir(legacy_id)
            return legacy_id, base, read_manifest(base), "legacy-git"

    raise RuntimeError("Project is not linked to Harness; run harness-init")


def bind(
    manifest: dict,
    path: Path | None,
    host: str,
    host_project_id: str,
) -> dict:
    updated, _ = migrate_manifest(manifest)
    bindings = list(updated["bindings"])
    if path is not None:
        bindings.append({"type": "path", "value": str(path), "primary": not any(
            item.get("type") == "path" for item in bindings
        )})
        bindings.extend({"type": "git", "value": value} for value in git_remotes(path))
    if host and host_project_id:
        bindings.append({"type": "host", "host": host.lower(), "value": host_project_id})
    updated["bindings"] = normalize_bindings(bindings)
    updated["repository_paths"] = sorted(
        item["value"] for item in updated["bindings"] if item["type"] == "path"
    )
    updated["remote_urls"] = sorted(
        item["value"] for item in updated["bindings"] if item["type"] == "git"
    )
    updated["schema_version"] = SCHEMA_VERSION
    updated["updated_at"] = utc_now()
    return updated


def init_project(
    path: Path,
    name: str | None = None,
    host: str = "",
    host_project_id: str = "",
) -> tuple[dict, bool]:
    home = harness_home()
    home.mkdir(parents=True, exist_ok=True)
    with lock(home / ".lock"):
        make_global_layout(home)
        owners = ensure_bindings_available(None, path, host, host_project_id)
        if owners:
            existing_id = next(iter(owners))
            base = project_dir(existing_id)
            existing = read_manifest(base)
            make_layout(base)
            updated = bind(existing, path, host, host_project_id)
            write_json(base / "manifest.json", updated)
            return updated, False

        project_id = str(uuid.uuid4())
        base = project_dir(project_id)
        make_layout(base)
        manifest = bind(
            {
                "bindings": [],
                "created_at": utc_now(),
                "display_name": name or path.name,
                "id": project_id,
                "remote_urls": [],
                "repository_paths": [],
                "schema_version": SCHEMA_VERSION,
                "updated_at": utc_now(),
            },
            path,
            host,
            host_project_id,
        )
        write_json(base / "manifest.json", manifest)
        return manifest, True


def link_project(
    path: Path,
    project_id: str,
    host: str = "",
    host_project_id: str = "",
) -> dict:
    base = project_dir(project_id)
    home = harness_home()
    with lock(home / ".lock"):
        make_global_layout(home)
        ensure_bindings_available(project_id, path, host, host_project_id)
        manifest = bind(read_manifest(base), path, host, host_project_id)
        make_layout(base)
        write_json(base / "manifest.json", manifest)
    return manifest


def emit(value: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, sort_keys=True, ensure_ascii=False))
    else:
        for key in sorted(value):
            print(f"{key}: {value[key]}")


def add_target_arguments(parser: argparse.ArgumentParser, *, id_allowed: bool = False) -> None:
    parser.add_argument("--project", "--repo", dest="project", default=".")
    if id_allowed:
        parser.add_argument("--project-id")
    parser.add_argument("--host", default="")
    parser.add_argument("--host-project-id", default="")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p_init = sub.add_parser("init")
    add_target_arguments(p_init)
    p_init.add_argument("--name")
    p_init.add_argument("--json", action="store_true")
    p_link = sub.add_parser("link")
    add_target_arguments(p_link, id_allowed=True)
    p_link.add_argument("--json", action="store_true")
    p_resolve = sub.add_parser("resolve")
    add_target_arguments(p_resolve, id_allowed=True)
    p_resolve.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        path = project_path(args.project)
        if args.command == "init":
            manifest, created = init_project(path, args.name, args.host, args.host_project_id)
            emit(
                {
                    "created": created,
                    "hooks": {
                        "installed": False,
                        "reason": "explicit installation only",
                    },
                    "project": manifest,
                    "project_dir": str(project_dir(manifest["id"])),
                },
                args.json,
            )
        elif args.command == "link":
            if not args.project_id:
                raise RuntimeError("--project-id is required for link")
            manifest = link_project(
                path, args.project_id, args.host, args.host_project_id
            )
            emit(
                {
                    "linked": True,
                    "project": manifest,
                    "project_dir": str(project_dir(manifest["id"])),
                },
                args.json,
            )
        else:
            identifier, base, manifest, resolution = resolve_project(
                path,
                args.project_id,
                args.host,
                args.host_project_id,
            )
            migrated, changed = migrate_manifest(manifest)
            if changed:
                with lock(harness_home() / ".lock"):
                    write_json(base / "manifest.json", migrated)
                manifest = migrated
            emit(
                {
                    "project": manifest,
                    "project_dir": str(base),
                    "project_id": identifier,
                    "resolution": resolution,
                },
                args.json,
            )
        return 0
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
