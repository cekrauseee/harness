"""Explicit, conservative import of Harness 0.5 files and legacy installation cleanup.

This module never invokes legacy code. Source fingerprints shipped with the package
come from an immutable repository revision. Scanning and previewing are read-only.
"""
from __future__ import annotations

import contextlib
import copy
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import stat
import tempfile
import uuid

from . import core


KNOWN = json.loads((Path(__file__).parent / "legacy/fingerprints.json").read_text())
LOCK_NAME = ".runtime.lock"
NAMESPACE = uuid.UUID("8714fe8d-13ad-5bbc-b975-cbaf09528959")


def _error(code, message, **details):
    raise core.HarnessError(code, message, details)


def _hash(content):
    return hashlib.sha256(content).hexdigest()


def _digest(value):
    return _hash(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())


def _home(home):
    return Path(home).expanduser().resolve() if home is not None else core.home_path()


def _json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    try:
        value = json.loads(path.read_bytes(), object_pairs_hook=unique,
                           parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"Invalid JSON constant: {value}")))
    except (OSError, ValueError, UnicodeError) as exc:
        _error("invalid_legacy_json", f"Cannot read JSON at {path}: {exc}")
    if not isinstance(value, dict):
        _error("invalid_legacy_json", f"Expected a JSON object: {path}")
    return value


def _safe_relative(value):
    path = Path(value)
    if path.is_absolute() or not path.parts or any(p in {".", ".."} for p in path.parts):
        _error("unsafe_backup", f"Unsafe backup path: {value}")
    return path


def _inventory(root, *, ignore_lock=False):
    """Hash every regular file; reject links and special files without following them."""
    files, directories = {}, []
    if not root.exists():
        return {"files": files, "directories": directories}
    if root.is_symlink() or not root.is_dir():
        _error("unsafe_source", f"Expected a real directory: {root}")
    for current, dirs, names in os.walk(root, followlinks=False):
        for name in sorted(dirs + names):
            path = Path(current) / name
            relative = path.relative_to(root).as_posix()
            if ignore_lock and relative == LOCK_NAME:
                if path.is_symlink() or not path.is_file():
                    _error("unsafe_source", f"Unsafe runtime lock: {path}")
                continue
            metadata = path.lstat()
            if stat.S_ISDIR(metadata.st_mode):
                directories.append(relative)
            elif stat.S_ISREG(metadata.st_mode):
                content = path.read_bytes()
                files[relative] = {"sha256": _hash(content), "size": len(content), "mode": stat.S_IMODE(metadata.st_mode)}
            else:
                _error("unsafe_source", f"Symlinks and special files require manual migration: {path}")
    return {"files": dict(sorted(files.items())), "directories": sorted(directories)}


def _warning(findings, code, message, path="", severity="warning"):
    findings.append({"code": code, "message": message, "path": str(path), "severity": severity})


def _legacy_schema(item, path):
    version = item.get("schema_version", 1)
    if type(version) is not int or version not in (1, 2):
        _error("unsupported_legacy_schema", f"Only legacy schema 1 or 2 is supported: {path}", schema_version=version)


def _strings(value):
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item]
    return []


def _text(item, *names, default=""):
    for name in names:
        value = item.get(name)
        if isinstance(value, str) and value:
            return value
    return default


def _mapped_id(identifier, source, used):
    if isinstance(identifier, str) and identifier and identifier not in used:
        result = identifier
    else:
        result = str(uuid.uuid5(NAMESPACE, source))
        while result in used:
            result = str(uuid.uuid5(NAMESPACE, source + ":" + result))
    used.add(result)
    return result


def _source(home, relative, original=None):
    result = {"path": str(home / relative), "relative_path": relative, "sha256": _hash((home / relative).read_bytes())}
    if original is not None:
        result["original"] = original
    return result


def _bindings(manifest, findings, path):
    raw = manifest.get("bindings", [])
    if not isinstance(raw, list):
        _error("invalid_legacy_bindings", f"Bindings must be a list: {path}")
    legacy_paths = manifest.get("repository_paths", [])
    if not isinstance(legacy_paths, list):
        _error("invalid_legacy_bindings", f"repository_paths must be a list: {path}")
    raw = raw + [{"type": "path", "value": item} for item in legacy_paths]
    result = []
    for item in raw:
        if not isinstance(item, dict):
            _error("invalid_legacy_bindings", f"Invalid binding: {path}")
        kind, value = item.get("type"), item.get("value")
        if not isinstance(value, str) or not value.strip():
            _error("invalid_legacy_bindings", f"Binding has no value: {path}")
        if kind == "path":
            bound = Path(value).expanduser()
            if not bound.is_absolute():
                _error("invalid_legacy_bindings", f"Relative path binding requires manual repair: {path}")
            binding = {"kind": "path", "value": str(bound.resolve())}
        elif kind == "host":
            host = item.get("host")
            if not isinstance(host, str) or not host.strip():
                _error("invalid_legacy_bindings", f"Host binding has no host: {path}")
            binding = {"kind": "host", "host": host.lower().strip(), "value": value}
        elif kind == "git":
            _warning(findings, "legacy_remote_reference", "Git remotes are preserved as references, not identity bindings.", path)
            continue
        else:
            _error("invalid_legacy_bindings", f"Unsupported binding type {kind!r}: {path}")
        if binding not in result:
            result.append(binding)
    return result


def _overlap(first, second):
    if first["kind"] != second["kind"]:
        return False
    if first["kind"] == "host":
        return first["host"] == second["host"] and first["value"] == second["value"]
    a, b = Path(first["value"]), Path(second["value"])
    return a == b or a in b.parents or b in a.parents


def _default_plan(home, inventory, findings):
    remove = []
    for relative, info in inventory["files"].items():
        key = relative
        parts = Path(relative).parts
        if len(parts) == 4 and parts[0] == "projects" and parts[2:] == ("worktrees", "policy.toml"):
            key = "projects/*/worktrees/policy.toml"
        known = KNOWN["defaults"].get(key)
        if known:
            if info["sha256"] == known["sha256"]:
                remove.append(relative)
            else:
                _warning(findings, "edited_legacy_default", "Edited legacy execution default is retained as inactive historical data; it is not new runtime policy.", relative)
    return remove


def _project_state(home, base, manifest, fingerprint, findings, aliases):
    identifier = manifest["id"]
    state = core.new_state(identifier, _text(manifest, "display_name", "title", default=identifier))
    state["project"]["created_at"] = _text(manifest, "created_at", default=state["project"]["created_at"])
    state["project"]["bindings"] = _bindings(manifest, findings, base / "manifest.json")
    state["legacy"] = {"migration_fingerprint": fingerprint, "manifest": _source(home, str((base / "manifest.json").relative_to(home)), manifest),
                       "query_aliases": aliases, "reference_sources": [], "id_map": [], "policy_active": False,
                       "uncertainty": "Legacy status and confidence are historical assertions; no approval, delivery, presence, or current verification is inferred."}
    timestamp = state["project"]["created_at"]
    workspaces = {}
    for binding in state["project"]["bindings"]:
        if binding["kind"] == "path":
            wid = str(uuid.uuid5(NAMESPACE, identifier + ":workspace:" + binding["value"]))
            workspaces[binding["value"]] = wid
            state["workspaces"][wid] = {"id": wid, "path": binding["value"], "kind": "directory", "git_common_dir": "", "legacy": True, "presence_unknown": True}
    session_ids, memory_ids = set(), set()
    for path in sorted((base / "sessions").rglob("*.json")):
        original = _json(path)
        _legacy_schema(original, path)
        relative = path.relative_to(home).as_posix()
        sid = _mapped_id(original.get("id"), relative, session_ids)
        if sid != original.get("id"):
            _warning(findings, "mapped_legacy_session_id", "Duplicate or missing session ID is mapped deterministically; every source occurrence is retained.", relative)
        tid = str(uuid.uuid5(NAMESPACE, identifier + ":task:" + relative))
        cid = str(uuid.uuid5(NAMESPACE, identifier + ":checkpoint:" + relative))
        wid = workspaces.get(original.get("worktree"), "")
        if not wid and len(workspaces) == 1:
            wid = next(iter(workspaces.values()))
        created = _text(original, "created_at", default=timestamp)
        updated = _text(original, "updated_at", default=created)
        title = _text(original, "title", "task", default="Legacy session " + str(original.get("id") or path.stem))
        source = _source(home, relative, original)
        state["tasks"][tid] = {"id": tid, "title": title, "objective": _text(original, "task", "summary", default=title),
            "status": "blocked", "created_at": created, "updated_at": updated, "session_ids": [sid], "events": [],
            "legacy_status": original.get("status", path.parent.name), "presence_unknown": True, "legacy_source": source}
        state["sessions"][sid] = {"id": sid, "task_id": tid, "workspace_id": wid, "status": "blocked",
            "created_at": created, "updated_at": updated, "checkpoint_ids": [cid], "presence_unknown": True,
            "legacy_status": original.get("status", path.parent.name), "legacy_source": source}
        state["checkpoints"][cid] = {"id": cid, "task_id": tid, "session_id": sid, "workspace_id": wid,
            "summary": _text(original, "summary", "task"), "evidence": _strings(original.get("artifact_refs")),
            "next_action": _text(original, "next_step"), "status": "blocked", "created_at": updated, "revision": 1,
            "legacy_source": source, "uncertainty": "Legacy lifecycle does not establish delivery or current presence."}
        state["legacy"]["id_map"].append({"kind": "session", "source": relative, "legacy_id": original.get("id"), "id": sid, "task_id": tid})
    for path in sorted((base / "memory").rglob("*.json")):
        original = _json(path)
        _legacy_schema(original, path)
        relative = path.relative_to(home).as_posix()
        mid = _mapped_id(original.get("id"), relative, memory_ids)
        if mid != original.get("id"):
            _warning(findings, "mapped_legacy_memory_id", "Duplicate or missing memory ID is mapped deterministically; every source occurrence is retained.", relative)
        title = _text(original, "title", "topic", default="Legacy memory " + path.stem)
        memory_aliases = _strings(original.get("tags")) + _strings(original.get("topic"))
        for alias, alternatives in aliases.items():
            if alias in memory_aliases or any(word in memory_aliases for word in _strings(alternatives)):
                memory_aliases += [alias] + _strings(alternatives)
        state["memories"][mid] = {"id": mid, "title": title, "summary": _text(original, "summary"),
            "content": _text(original, "content"), "kind": "historical", "status": "stale", "sources": [str(path)],
            "scope": _text(original, "read_when", "topic", default="legacy"), "aliases": sorted(set(memory_aliases)),
            "created_at": _text(original, "created_at", default=timestamp), "updated_at": _text(original, "updated_at", default=timestamp),
            "revision": 1, "review_after": original.get("review_after"), "superseded_by": None, "legacy_source": _source(home, relative, original),
            "uncertainty": "Imported without re-verifying legacy classification, confidence, supersession, or pending promotion."}
        state["legacy"]["id_map"].append({"kind": "memory", "source": relative, "legacy_id": original.get("id"), "id": mid})
    catalog = base / "memory/catalog.jsonl"
    if catalog.exists():
        # The old catalog is derived, never authoritative over the source records.
        try:
            for line in catalog.read_text(encoding="utf-8").splitlines():
                if line.strip() and not isinstance(json.loads(line), dict):
                    raise ValueError("Expected a catalog object")
        except (ValueError, UnicodeError):
            _warning(findings, "invalid_legacy_catalog", "Malformed derived catalog is retained in the backup; records are imported from their source files.", catalog)
        state["legacy"]["reference_sources"].append(_source(home, catalog.relative_to(home).as_posix()))
    for path in sorted(base.rglob("*.md")):
        relative = path.relative_to(home).as_posix()
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            _error("invalid_legacy_text", f"Markdown must be UTF-8 for automatic import: {path}")
        mid = _mapped_id(None, relative, memory_ids)
        title = next((line.lstrip("# ").strip() for line in content.splitlines() if line.strip()), path.stem)
        state["memories"][mid] = {"id": mid, "title": title, "summary": "Legacy reference preserved without promoting it to instructions.",
            "content": content, "kind": "historical", "status": "stale", "sources": [str(path)], "scope": "legacy reference", "aliases": [],
            "created_at": timestamp, "updated_at": timestamp, "revision": 1, "review_after": None, "superseded_by": None,
            "legacy_source": _source(home, relative), "policy_active": False}
        state["legacy"]["reference_sources"].append(_source(home, relative))
    for directory in (home / "overrides", home / "standards"):
        if directory.exists():
            for path in sorted(directory.rglob("*")):
                if path.is_file():
                    state["legacy"]["reference_sources"].append(_source(home, path.relative_to(home).as_posix()))
    state["revision"] = 1
    state["events"].append({"id": str(uuid.uuid5(NAMESPACE, identifier + ":migration:" + fingerprint)), "revision": 1,
        "operation": "migrate.apply", "created_at": timestamp, "details": {"fingerprint": fingerprint, "source_schema": manifest.get("schema_version", 1)}})
    return state


def _plan(home):
    inventory = _inventory(home, ignore_lock=True)
    fingerprint = _digest(inventory)
    findings, states, projects, aliases = [], {}, [], {}
    alias_path = home / "standards/query-aliases.json"
    if alias_path.exists():
        aliases = _json(alias_path)
    managed = home / "managed.json"
    if managed.exists():
        version = _json(managed).get("defaults_version", 0)
        if type(version) is not int or version > core.DEFAULTS_VERSION:
            _error("unsupported_defaults_version", "A future defaults version requires a newer runtime.", defaults_version=version)
    owners = []
    for path in sorted((home / "projects").glob("*/manifest.json")):
        manifest = _json(path)
        _legacy_schema(manifest, path)
        identifier = manifest.get("id")
        try:
            valid = isinstance(identifier, str) and str(uuid.UUID(identifier)) == identifier and identifier == path.parent.name
        except ValueError:
            valid = False
        if not valid:
            _error("invalid_legacy_project_id", f"Manifest ID must be a canonical UUID matching its directory: {path}")
        destination = core.state_path(home, identifier)
        if destination.exists():
            state = core.read_state(destination)
            if not state.get("legacy", {}).get("migration_fingerprint"):
                _error("existing_state_conflict", f"Legacy manifest and unrelated v3 state coexist: {destination}")
            backup = state["legacy"].get("backup_dir")
            if not isinstance(backup, str):
                _error("migration_history_missing", "Imported state has no backup provenance; inspect it before another migration.")
            metadata = _json(Path(backup) / "backup.json")
            if metadata.get("status") != "complete":
                _error("migration_incomplete", "An earlier import did not complete; inspect its backup and use guarded restore before retrying.", backup_dir=backup)
            prefix = f"projects/{identifier}/"
            def legacy_scope(files):
                return {name: info for name, info in files.items() if
                        (name.startswith(prefix) and name != prefix + "state.json") or
                        name.startswith(("standards/", "overrides/")) or name in {"managed.json", "charter.md"}}
            if legacy_scope(inventory["files"]) != legacy_scope(metadata["after"]["files"]):
                _error("source_changed", "Legacy files changed after import; new preview does not authorize silently dropping those changes.", project_id=identifier)
            projects.append({"project_id": identifier, "status": "already_migrated"})
        else:
            state = _project_state(home, path.parent, manifest, fingerprint, findings, aliases)
            states[identifier] = state
            projects.append({"project_id": identifier, "status": "pending", "sessions": len(state["sessions"]), "memories": len(state["memories"])})
        for binding in state["project"]["bindings"]:
            for owner, other in owners:
                if owner != identifier and _overlap(binding, other):
                    _error("ambiguous_legacy_binding", "Two projects have overlapping path or host bindings; repair identity explicitly before migration.", project_ids=[owner, identifier], binding=binding)
            owners.append((identifier, binding))
    # Existing v3-only projects also participate in collision checks.
    for path in sorted((home / "projects").glob("*/state.json")):
        if (path.parent / "manifest.json").exists():
            continue
        state = core.read_state(path)
        identifier = state["project"]["id"]
        for binding in state["project"]["bindings"]:
            if binding.get("kind") not in {"path", "host"}:
                continue
            for owner, other in owners:
                if owner != identifier and _overlap(binding, other):
                    _error("ambiguous_legacy_binding", "Legacy and v3 projects have overlapping bindings.", project_ids=[owner, identifier])
            owners.append((identifier, binding))
    remove = _default_plan(home, inventory, findings)
    for project in projects:
        if project["status"] == "pending":
            _warning(findings, "legacy_presence_unknown", "Imported work remains blocked pending explicit reassessment; closed legacy sessions do not establish approved delivery.", project["project_id"])
    return {"success": True, "scope": "entire_home", "home": str(home), "fingerprint": fingerprint, "inventory": inventory,
            "projects": projects, "findings": findings, "remove_defaults": remove, "states": states,
            "old_agents_must_be_stopped": True}


def _backup_root(home):
    return home.parent / ("." + home.name + "-migration-backups")


def _create_backup(home, plan, operation):
    root = _backup_root(home)
    if root.is_symlink():
        _error("unsafe_backup", "Backup root cannot be a symlink.")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix=operation + "-", dir=root))
    os.chmod(directory, 0o700)
    snapshot = directory / "source"
    snapshot.mkdir()
    for relative in plan["inventory"]["directories"]:
        (snapshot / _safe_relative(relative)).mkdir(parents=True, exist_ok=True)
    for relative in plan["inventory"]["files"]:
        destination = snapshot / _safe_relative(relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(home / relative, destination, follow_symlinks=False)
        with destination.open("rb") as handle:
            os.fsync(handle.fileno())
    if _inventory(snapshot) != plan["inventory"] or _inventory(home, ignore_lock=True) != plan["inventory"]:
        _error("source_changed", "Legacy files changed while creating the backup; no migration writes were made.", backup_dir=str(directory))
    metadata = {"schema_version": 1, "operation": operation, "home": str(home), "fingerprint": plan["fingerprint"],
                "before": plan["inventory"], "status": "prepared"}
    core.atomic_json(directory / "backup.json", metadata)
    return directory, metadata


def _write_bytes(path, content, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fchmod(handle.fileno(), mode)
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary)


def _acknowledge(data):
    if data.get("old_agents_stopped") is not True:
        _error("old_agents_running", "Set old_agents_stopped=true only after stopping old Harness agents, hooks, and scripts. New locks cannot coordinate with them.")


def _without_states(inventory):
    return {"files": {path: value for path, value in inventory["files"].items() if not (len(Path(path).parts) == 3 and Path(path).parts[0] == "projects" and Path(path).name == "state.json")},
            "directories": inventory["directories"]}


def _previous_apply(home, fingerprint):
    for path in sorted(_backup_root(home).glob("migrate-*/backup.json")):
        metadata = _json(path)
        if metadata.get("fingerprint") != fingerprint or metadata.get("home") != str(home) or metadata.get("status") != "complete":
            continue
        if _without_states(_inventory(home, ignore_lock=True)) != _without_states(metadata["after"]):
            _error("source_changed", "Legacy files changed after migration; do not rerun old scripts.")
        for identifier in metadata["project_ids"]:
            current = core.read_state(core.state_path(home, identifier))
            if current.get("legacy", {}).get("migration_fingerprint") != fingerprint:
                _error("existing_state_conflict", "Migration state no longer matches its recorded import.")
        return {"success": True, "idempotent": True, "backup_dir": str(path.parent), "project_ids": metadata["project_ids"], "fingerprint": fingerprint}
    return None


def _apply(home, data):
    _acknowledge(data)
    fingerprint = data.get("fingerprint")
    if not isinstance(fingerprint, str) or not fingerprint:
        _error("preview_required", "Provide the fingerprint from migrate.preview.")
    with core.locked(home):
        previous = _previous_apply(home, fingerprint)
        if previous:
            return previous
        plan = _plan(home)
        if plan["fingerprint"] != fingerprint:
            _error("source_changed", "Legacy files changed since preview; preview again before applying.")
        if not plan["states"] and not plan["remove_defaults"]:
            return {"success": True, "idempotent": True, "backup_dir": None, "project_ids": [], "fingerprint": fingerprint}
        directory, metadata = _create_backup(home, plan, "migrate")
        expected = copy.deepcopy(plan["inventory"])
        output = {}
        for identifier, state in plan["states"].items():
            state["legacy"]["backup_dir"] = str(directory)
            def add_backup_sources(value):
                if isinstance(value, dict):
                    if "relative_path" in value and "sha256" in value and "path" in value:
                        value["backup_path"] = str(directory / "source" / value["relative_path"])
                    for key, child in list(value.items()):
                        if key != "original":
                            add_backup_sources(child)
                elif isinstance(value, list):
                    for child in value:
                        add_backup_sources(child)
            add_backup_sources(state)
            path = core.state_path(home, identifier)
            content = (json.dumps(state, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()
            relative = path.relative_to(home).as_posix()
            expected["files"][relative] = {"sha256": _hash(content), "size": len(content), "mode": 0o600}
            output[path] = content
        for relative in plan["remove_defaults"]:
            expected["files"].pop(relative)
        metadata.update({"after": expected, "project_ids": list(plan["states"]), "removed_defaults": plan["remove_defaults"], "status": "applying"})
        core.atomic_json(directory / "backup.json", metadata)
        if _inventory(home, ignore_lock=True) != plan["inventory"]:
            _error("source_changed", "Source changed immediately before application; no migration writes were made.", backup_dir=str(directory))
        for path, content in output.items():
            _write_bytes(path, content)
        # Remove only exact known execution defaults after all canonical states are durable.
        for relative in plan["remove_defaults"]:
            path = home / relative
            if _hash(path.read_bytes()) != plan["inventory"]["files"][relative]["sha256"]:
                _error("source_changed", "An execution default changed during migration; preserve it and inspect the backup.", backup_dir=str(directory))
            path.unlink()
        if _inventory(home, ignore_lock=True) != expected:
            _error("source_changed", "Home changed during migration; backup retained for inspection and guarded restore.", backup_dir=str(directory))
        metadata["status"] = "complete"
        core.atomic_json(directory / "backup.json", metadata)
        return {"success": True, "idempotent": False, "backup_dir": str(directory), "project_ids": list(plan["states"]),
                "fingerprint": fingerprint, "removed_defaults": plan["remove_defaults"], "findings": plan["findings"]}


def _restore(home, data):
    _acknowledge(data)
    if not isinstance(data.get("backup_dir"), str) or not data["backup_dir"]:
        _error("backup_required", "Provide backup_dir returned by migrate.apply.")
    directory = Path(data["backup_dir"]).expanduser().resolve()
    if directory == home or home in directory.parents:
        _error("unsafe_backup", "Restore backup must be outside the Harness home.")
    metadata = _json(directory / "backup.json")
    if metadata.get("schema_version") != 1 or metadata.get("operation") != "migrate" or metadata.get("home") != str(home):
        _error("unsafe_backup", "Backup metadata does not match this home and migration format.")
    before, after = metadata.get("before"), metadata.get("after")
    if not isinstance(before, dict) or not isinstance(after, dict):
        _error("unsafe_backup", "Backup has no complete restoration plan.")
    for inventory in (before, after):
        for relative in list(inventory["files"]) + inventory["directories"]:
            _safe_relative(relative)
    if _inventory(directory / "source") != before:
        _error("backup_changed", "Backup bytes do not match the original checksums; restore refused.")
    with core.locked(home):
        current = _inventory(home, ignore_lock=True)
        if metadata.get("status") == "restored" and current == before:
            return {"success": True, "idempotent": True, "backup_dir": str(directory), "restored": True}
        # Accept only pre/post bytes for restart after interrupted migration or restore.
        if set(current["directories"]) != set(before["directories"]) or not set(current["files"]).issubset(set(before["files"]) | set(after["files"])):
            _error("restore_conflict", "Files or directories were added after migration; restore would discard newer work.")
        for relative in set(before["files"]) | set(after["files"]):
            actual = current["files"].get(relative)
            if actual not in (before["files"].get(relative), after["files"].get(relative)):
                _error("restore_conflict", "Files changed after migration; restore refuses to overwrite newer work.", path=relative)
        metadata["status"] = "restoring"
        core.atomic_json(directory / "backup.json", metadata)
        for relative, info in before["files"].items():
            if current["files"].get(relative) != info:
                _write_bytes(home / relative, (directory / "source" / relative).read_bytes(), info["mode"])
        for relative in set(after["files"]) - set(before["files"]):
            with contextlib.suppress(FileNotFoundError):
                (home / relative).unlink()
        if _inventory(home, ignore_lock=True) != before:
            _error("restore_conflict", "Home changed during restore; backup retained.")
        metadata["status"] = "restored"
        core.atomic_json(directory / "backup.json", metadata)
        return {"success": True, "idempotent": False, "backup_dir": str(directory), "restored": True}


def _paths(data, name):
    values = data.get(name, [])
    if not isinstance(values, list) or not all(isinstance(value, str) and value for value in values):
        _error("invalid_input", f"{name} must be a list of explicit paths.")
    return sorted({Path(value).expanduser().absolute() for value in values}, key=str)


def _known_handler(handler):
    if not isinstance(handler, dict) or set(handler) != {"type", "command", "timeout"} or handler.get("type") != "command" or handler.get("timeout") != 15:
        return False
    if not isinstance(handler["command"], str):
        return False
    try:
        command = shlex.split(handler["command"])
    except (ValueError, TypeError):
        return False
    if len(command) != 4 or command[0] != "python3" or command[2:] != ["event", "session-start"]:
        return False
    adapter = Path(command[1])
    if not adapter.is_absolute() or tuple(adapter.parts[-3:]) != ("harness-init", "scripts", "hook_adapter.py"):
        return False
    if adapter.is_symlink() or not adapter.is_file():
        return False
    return _hash(adapter.read_bytes()) == KNOWN["hook_adapter_sha256"]


def _hook_cleanup(config):
    updated = copy.deepcopy(config)
    removed = 0
    hooks = updated.get("hooks", {})
    if not isinstance(hooks, dict):
        _error("invalid_hooks", "Host hooks must be a JSON object.")
    for event, groups in list(hooks.items()):
        if not isinstance(groups, list):
            _error("invalid_hooks", f"hooks.{event} must be a list.")
        retained = []
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                retained.append(group)
                continue
            handlers = [handler for handler in group["hooks"] if not _known_handler(handler)]
            removed += len(group["hooks"]) - len(handlers)
            if handlers or handlers == group["hooks"]:
                replacement = dict(group)
                replacement["hooks"] = handlers
                retained.append(replacement)
            elif set(group) - {"hooks", "matcher"}:
                # Preserve unknown group metadata even when the known handler was its last one.
                replacement = dict(group)
                replacement["hooks"] = []
                retained.append(replacement)
        if retained:
            hooks[event] = retained
        elif groups:
            del hooks[event]
    return updated, removed


def _scan(data):
    findings, skills, hook_files = [], [], []
    for root in _paths(data, "skill_roots"):
        for name, known_files in KNOWN["skills"].items():
            path = root / name
            if not path.exists() and not path.is_symlink():
                continue
            try:
                inventory = _inventory(path)
                actual = {relative: info["sha256"] for relative, info in inventory["files"].items()}
                expected_dirs = {parent.as_posix() for relative in known_files for parent in Path(relative).parents if parent != Path(".")}
                exact = actual == known_files and set(inventory["directories"]) == expected_dirs
            except core.HarnessError:
                inventory, exact = None, False
            skills.append({"path": str(path), "name": name, "exact_known_legacy": exact, "inventory": inventory})
            if not exact:
                _warning(findings, "modified_or_unknown_legacy_skill", "Known legacy name has unknown or edited content; automatic cleanup will preserve it.", path)
    for path in _paths(data, "hook_files"):
        if not path.exists():
            continue
        if path.is_symlink() or not path.is_file():
            _error("unsafe_source", f"Host hook configuration must be a regular file: {path}")
        config = _json(path)
        updated, removed = _hook_cleanup(config)
        hook_files.append({"path": str(path), "sha256": _hash(path.read_bytes()), "remove_handlers": removed, "updated": updated})
        if "harness-init/scripts/hook_adapter.py" in json.dumps(updated):
            _warning(findings, "unknown_legacy_hook", "Unrecognized or unavailable legacy handler is preserved; inspect it manually.", path)
    fingerprint = _digest({"skills": skills, "hook_files": hook_files})
    return {"success": True, "fingerprint": fingerprint, "skills": skills, "hook_files": hook_files, "findings": findings,
            "scope": "explicit_paths_only", "cleanup_requires_opt_in": True}


def _clean(home, data):
    _acknowledge(data)
    with core.locked(home):
        plan = _scan(data)
        if data.get("fingerprint") != plan["fingerprint"]:
            _error("source_changed", "Legacy installation changed or no scan fingerprint was supplied; run legacy.scan again.")
        matched = [skill for skill in plan["skills"] if skill["exact_known_legacy"]]
        changed_hooks = [entry for entry in plan["hook_files"] if entry["remove_handlers"]]
        if not matched and not changed_hooks:
            return {"success": True, "idempotent": True, "quarantine_dir": None, "findings": plan["findings"]}
        root = _backup_root(home)
        if root.is_symlink():
            _error("unsafe_backup", "Backup root cannot be a symlink.")
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        directory = Path(tempfile.mkdtemp(prefix="legacy-clean-", dir=root))
        records = []
        for index, entry in enumerate(matched):
            source = Path(entry["path"])
            if source.stat().st_dev != directory.stat().st_dev:
                _error("cross_device_cleanup", "Automatic skill quarantine requires the skill and backup on the same filesystem; preserve this installation for manual removal.")
            destination = directory / f"skill-{index}-{entry['name']}"
            shutil.copytree(source, destination, symlinks=True)
            if _inventory(destination) != entry["inventory"]:
                _error("source_changed", "Legacy skill changed during backup; cleanup was not applied.")
            records.append({"source": str(source), "backup": str(destination), "quarantine": str(destination) + "-original", "kind": "skill"})
        for index, entry in enumerate(changed_hooks):
            source = Path(entry["path"])
            destination = directory / f"hooks-{index}.json"
            shutil.copy2(source, destination)
            if _hash(destination.read_bytes()) != entry["sha256"]:
                _error("source_changed", "Hook configuration changed during backup; cleanup was not applied.")
            records.append({"source": str(source), "backup": str(destination), "kind": "hooks"})
        core.atomic_json(directory / "cleanup.json", {"operation": "legacy.clean", "fingerprint": plan["fingerprint"], "records": records, "status": "prepared"})
        if _scan(data)["fingerprint"] != plan["fingerprint"]:
            _error("source_changed", "Installation changed before cleanup; preserved backup for inspection.")
        # Clean hooks before removing the scripts used to establish their exact identity.
        for entry in changed_hooks:
            source = Path(entry["path"])
            _write_bytes(source, (json.dumps(entry["updated"], indent=2, ensure_ascii=False) + "\n").encode(), stat.S_IMODE(source.stat().st_mode))
        for index, entry in enumerate(matched):
            source = Path(entry["path"])
            if _inventory(source) != entry["inventory"]:
                _error("source_changed", "Legacy skill changed before removal; preserved it and its backup.")
            os.replace(source, directory / f"skill-{index}-{entry['name']}-original")
        core.atomic_json(directory / "cleanup.json", {"operation": "legacy.clean", "fingerprint": plan["fingerprint"], "records": records, "status": "complete"})
        return {"success": True, "idempotent": False, "quarantine_dir": str(directory), "removed_skills": [entry["path"] for entry in matched],
                "removed_handlers": sum(entry["remove_handlers"] for entry in changed_hooks), "findings": plan["findings"]}


def execute(operation, data, home=None):
    if not isinstance(data, dict):
        _error("invalid_input", "Operation input must be a JSON object.")
    home = _home(home)
    if operation == "migrate.preview":
        plan = _plan(home)
        del plan["states"]
        return plan
    if operation == "migrate.apply":
        return _apply(home, data)
    if operation == "migrate.restore":
        return _restore(home, data)
    if operation == "legacy.scan":
        return _scan(data)
    if operation == "legacy.clean":
        return _clean(home, data)
    _error("unknown_operation", f"Unknown migration operation: {operation}")
