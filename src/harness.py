#!/usr/bin/env python3
"""Harness: external project identity, current ownership, and Markdown CAS."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid

VERSION = "0.8.0"
FORMAT = 1
LOCK_TIMEOUT = 10.0


class Error(RuntimeError):
    def __init__(self, code, message, details=None):
        super().__init__(message)
        self.code, self.message, self.details = code, message, details or {}


def fail(code, message, **details):
    raise Error(code, message, details)


def canonical_id(value):
    try:
        if str(uuid.UUID(value)) == value:
            return value
    except (ValueError, TypeError, AttributeError):
        pass
    fail("invalid_id", "Use a lowercase, hyphenated UUID.", value=value)


def contains(parent, child):
    return child == parent or parent in child.parents


def overlaps(first, second):
    return contains(first, second) or contains(second, first)


def resource_overlap(first, second):
    if overlaps(first, second):
        return True
    # Inodes identify existing aliases; remaining components identify future paths.
    ancestors = {}
    for path in (first, *first.parents):
        try:
            info = path.stat()
        except (FileNotFoundError, NotADirectoryError):
            continue
        ancestors[(info.st_dev, info.st_ino)] = first.relative_to(path).parts
    for path in (second, *second.parents):
        try:
            info = path.stat()
        except (FileNotFoundError, NotADirectoryError):
            continue
        tail = ancestors.get((info.st_dev, info.st_ino))
        if tail is not None:
            other = second.relative_to(path).parts
            if tail[:len(other)] == other or other[:len(tail)] == tail:
                return True
    return False


def now():
    return datetime.now(timezone.utc).isoformat()


def sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def make_directory(path):
    if not path.is_dir():
        make_directory(path.parent)
        path.mkdir(exist_ok=True)
        sync_directory(path.parent)


def atomic_write(path, content):
    """A failed replace leaves the old bytes intact; post-replace failures are uncertain."""
    descriptor, temporary = tempfile.mkstemp(prefix=".harness-", dir=path.parent)
    replaced = False
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        replaced = True
        sync_directory(path.parent)
    except OSError as exc:
        fail("write_uncertain" if replaced else "write_failed",
             "Replacement completed but durability is uncertain; inspect current state."
             if replaced else "Replacement failed; previous contents are unchanged.",
             path=str(path), reason=str(exc))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def locked(home):
    """Never unlink this lock or infer ownership from its age."""
    import fcntl
    make_directory(home)
    lock = home / ".runtime.lock"
    if lock.is_symlink():
        fail("unsafe_path", "The runtime lock must not be a symbolic link.", path=str(lock))
    with lock.open("a+b") as stream:
        deadline = time.monotonic() + LOCK_TIMEOUT
        while True:
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    fail("lock_busy", "Another Harness transaction holds the lock; retry later.",
                         path=str(home / ".runtime.lock"))
                time.sleep(0.02)
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def absolute_string(value):
    return (isinstance(value, str) and Path(value).is_absolute()
            and os.path.normpath(value) == value)


def validate(state, project_id):
    """Validate the small stored contract before trusting paths or coordination state."""
    if (not isinstance(state, dict) or type(state.get("format")) is not int
            or state["format"] != FORMAT or state.get("id") != project_id
            or not isinstance(state.get("name"), str)
            or not isinstance(state.get("roots"), list)
            or not isinstance(state.get("contributions"), dict)):
        fail("invalid_state", "Project snapshot is not the current format.", project_id=project_id)
    paths, workspaces = set(), set()
    for root in state["roots"]:
        if (not isinstance(root, dict) or not absolute_string(root.get("path"))
                or not isinstance(root.get("git_common_dir"), str)
                or (root["git_common_dir"] and not absolute_string(root["git_common_dir"]))
                or root["path"] in paths):
            fail("invalid_state", "Invalid or duplicate project root.", project_id=project_id)
        wid = canonical_id(root.get("workspace_id"))
        if wid in workspaces:
            fail("invalid_state", "Duplicate workspace identity.", project_id=project_id)
        paths.add(root["path"])
        workspaces.add(wid)
    for owner, record in state["contributions"].items():
        canonical_id(owner)
        if (not isinstance(record, dict) or record.get("id") != owner
                or not isinstance(record.get("purpose"), str)
                or not absolute_string(record.get("workspace"))
                or record.get("workspace_id") not in workspaces
                or type(record.get("active")) is not bool
                or type(record.get("version")) is not int or record["version"] < 1
                or not isinstance(record.get("handoff"), str)
                or not isinstance(record.get("updated_at"), str)
                or not isinstance(record.get("resources"), list)
                or not record["resources"]
                or not all(absolute_string(p) for p in record["resources"])
                or not isinstance(record.get("release_reason", ""), str)):
            fail("invalid_state", "Invalid contribution record.", project_id=project_id, owner=owner)
    return state


def project_directory(home, project_id):
    folder = home / "projects" / canonical_id(project_id)
    if folder.is_symlink() or (home / "projects").is_symlink():
        fail("unsafe_path", "Project storage must not be a symbolic link.", path=str(folder))
    return folder


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail("invalid_state", "Project snapshot contains a duplicate JSON key.", key=key)
        result[key] = value
    return result


def load_project(home, project_id):
    path = project_directory(home, project_id) / "project.json"
    if path.is_symlink():
        fail("unsafe_path", "Project snapshot must not be a symbolic link.", path=str(path))
    try:
        state = json.loads(path.read_bytes(), object_pairs_hook=unique_object,
                           parse_constant=lambda value: fail(
                               "invalid_state", "Project snapshot contains an invalid JSON constant.", value=value))
    except FileNotFoundError:
        fail("project_unknown", "Project snapshot does not exist.", path=str(path))
    except (ValueError, UnicodeError) as exc:
        fail("invalid_state", "Project snapshot cannot be decoded.", path=str(path), reason=str(exc))
    return validate(state, project_id)


def scan(home):
    directory = home / "projects"
    if not directory.exists():
        return []
    if directory.is_symlink():
        fail("unsafe_path", "Project storage must not be a symbolic link.", path=str(directory))
    result = []
    for folder in sorted(directory.iterdir()):
        if folder.name.startswith("."):
            continue
        if not folder.is_dir():
            fail("invalid_state", "Unexpected file in the projects directory.", path=str(folder))
        result.append(load_project(home, canonical_id(folder.name)))
    return result


def git(path, *arguments):
    # Shell Git overrides must not silently change the identity of --project.
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env["LC_ALL"] = "C"
    try:
        result = subprocess.run(["git", "-C", str(path), *arguments], capture_output=True,
                                text=True, timeout=5, env=env)
    except (OSError, subprocess.TimeoutExpired) as exc:
        fail("git_unavailable", "Git identity could not be checked.", reason=str(exc))
    if result.returncode:
        if "not a git repository" in result.stderr:
            return ""
        fail("git_unavailable", "Git identity could not be checked.", reason=result.stderr.strip())
    return result.stdout.strip()


def probe(value, home):
    if not isinstance(value, (str, Path)) or not str(value).strip():
        fail("invalid_input", "Provide an existing project directory.")
    path = Path(value).expanduser().resolve()
    if not path.is_dir():
        fail("project_missing", "Project directory does not exist.", path=str(path))
    top = git(path, "rev-parse", "--show-toplevel")
    root = Path(top).resolve() if top else path
    common = git(root, "rev-parse", "--git-common-dir") if top else ""
    if top and not common:
        fail("git_unavailable", "Git common-directory identity is unavailable.")
    common = str((root / common).resolve()) if common else ""
    if overlaps(root, home):
        fail("unsafe_path", "Harness storage and project roots must be outside one another.",
             project=str(root), home=str(home))
    return path, {"path": str(root), "git_common_dir": common}


def workspace(project_id, root, roots=()):
    # A moved workspace keeps its ID; reuse of its old path must get a distinct ID.
    occupied = {r["workspace_id"] for r in roots if r["path"] != root["path"]}
    seed, suffix = root["path"], 0
    identifier = str(uuid.uuid5(uuid.UUID(project_id), seed))
    while identifier in occupied:
        suffix += 1
        identifier = str(uuid.uuid5(uuid.UUID(project_id), seed + "\0" + str(suffix)))
    return {**root, "workspace_id": identifier}


def collision(states, project_id, root, replacing=None):
    for state in states:
        for existing in state["roots"]:
            if state["id"] == project_id and existing["path"] == replacing:
                continue
            if state["id"] != project_id and (
                    overlaps(Path(root["path"]), Path(existing["path"]))
                    or (root["git_common_dir"] and root["git_common_dir"] == existing["git_common_dir"])):
                fail("root_conflict", "Root overlaps another project's registered identity.",
                     project_id=state["id"], root=existing)


def select_path(states, path, current):
    candidates = [(state, root) for state in states for root in state["roots"]
                  if contains(Path(root["path"]), path)]
    if candidates:
        state, root = max(candidates, key=lambda pair: len(Path(pair[1]["path"]).parts))
        if root["git_common_dir"] != current["git_common_dir"]:
            fail("topology_changed", "Registered root topology changed; use explicit bind --replace.",
                 registered=root, current=current, project_id=state["id"])
        collision(states, state["id"], current)
        if not current["git_common_dir"] or root["path"] == current["path"]:
            return state, root
        return state, workspace(state["id"], current, state["roots"])
    matches = [state for state in states if current["git_common_dir"] and any(
        root["git_common_dir"] == current["git_common_dir"] for root in state["roots"])]
    if len(matches) > 1:
        fail("root_conflict", "Git identity belongs to multiple projects.")
    if matches:
        state = matches[0]
        collision(states, state["id"], current)
        return state, workspace(state["id"], current, state["roots"])
    fail("project_unknown", "Project is not registered; use init or explicit bind.", path=str(path))


def select(home, data):
    if bool(data.get("project")) == bool(data.get("project_id")):
        fail("invalid_input", "Select exactly one of project or project_id.")
    if data.get("project_id"):
        return load_project(home, data["project_id"]), None
    path, current = probe(data["project"], home)
    return select_path(scan(home), path, current)


def result(home, state, current):
    folder = project_directory(home, state["id"])
    return {"project_id": state["id"], "project_dir": str(folder),
            "knowledge_dir": str(folder / "knowledge"), "workspace": current}


def save(home, state, new=False):
    validate(state, state["id"])
    content = (json.dumps(state, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    folder = project_directory(home, state["id"])
    if not new:
        atomic_write(folder / "project.json", content)
        return
    # Publish a complete directory, so concurrent readers never observe a partial project.
    make_directory(folder.parent)
    temporary = Path(tempfile.mkdtemp(prefix=".project-", dir=folder.parent))
    try:
        (temporary / "knowledge").mkdir()
        atomic_write(temporary / "project.json", content)
        os.rename(temporary, folder)
        try:
            sync_directory(folder.parent)
        except OSError as exc:
            fail("write_uncertain", "Identity was published but durability is uncertain; resolve it.", reason=str(exc))
    finally:
        if temporary.exists():
            for child in temporary.iterdir():
                child.rmdir() if child.is_dir() else child.unlink()
            temporary.rmdir()


def initialize(home, data, binding=False):
    path, current = probe(data.get("project"), home)
    states = scan(home)
    if binding:
        project_id = canonical_id(data.get("project_id"))
        state = next((s for s in states if s["id"] == project_id), None)
        if state is None:
            fail("project_unknown", "Target project is not registered.", project_id=project_id)
        replacing = str(Path(data["replace"]).expanduser().resolve()) if data.get("replace") else None
        old = next((r for r in state["roots"] if r["path"] == replacing), None)
        exact = next((r for r in state["roots"] if r["path"] == current["path"]), None)
        if replacing and not old:
            if exact and exact["git_common_dir"] == current["git_common_dir"]:
                return result(home, state, exact)
            fail("root_unknown", "Replacement source is not a registered root.", path=replacing)
        if old and old == exact and old["git_common_dir"] == current["git_common_dir"]:
            return result(home, state, old)
        if old and any(c["active"] and c["workspace_id"] == old["workspace_id"]
                       for c in state["contributions"].values()):
            fail("active_contribution", "Release active contributions before replacing their workspace.")
        if exact and exact != old:
            if exact["git_common_dir"] != current["git_common_dir"]:
                fail("topology_changed", "Use --replace to change this registered root.")
            if old:
                fail("root_conflict", "Replacement destination is already registered.")
            return result(home, state, exact)
        collision(states, project_id, current, replacing)
        root = workspace(project_id, current, state["roots"])
        if old:
            root["workspace_id"] = old["workspace_id"]
            state["roots"].remove(old)
        state["roots"].append(root)
        save(home, state)
        return result(home, state, root)
    if data.get("project_id"):
        fail("invalid_input", "Use bind to associate an existing project ID.")
    try:
        state, root = select_path(states, path, current)
    except Error as exc:
        if exc.code != "project_unknown":
            raise
        project_id = str(uuid.uuid4())
        collision(states, project_id, current)
        root = workspace(project_id, current)
        state = {"format": FORMAT, "id": project_id, "name": data.get("name") or path.name,
                 "roots": [root], "contributions": {}}
        save(home, state, new=True)
        return result(home, state, root)
    if root not in state["roots"]:
        state["roots"].append(root)
        save(home, state)
    return result(home, state, root)


def expected_version(data):
    expected = data.get("expect")
    if isinstance(expected, str) and expected.isdigit():
        expected = int(expected)
    if type(expected) is not int or expected < 1:
        fail("invalid_input", "Provide the observed positive contribution version in expect.")
    return expected


def check_version(record, expected):
    if record["version"] != expected:
        fail("version_conflict", "Contribution changed; inspect it before retrying.", current=record)


def input_bytes(data):
    if not data.get("input"):
        fail("invalid_input", "Provide an input file containing UTF-8 Markdown.")
    content = (sys.stdin.buffer.read() if data["input"] == "-"
               else Path(data["input"]).expanduser().read_bytes())
    try:
        content.decode("utf-8")
    except UnicodeError:
        fail("invalid_input", "Input must contain UTF-8 Markdown.")
    return content


def ownership(operation, home, state, current, data):
    records = state["contributions"]
    owner = data.get("owner")
    record = records.get(canonical_id(owner)) if owner else None
    if operation == "claim":
        if current is None:
            fail("invalid_input", "Claim requires a project path to identify the writer's workspace.")
        if owner and record is None:
            fail("owner_unknown", "Contribution owner does not exist.")
        if record and not record["active"]:
            fail("owner_closed", "Closed ownership cannot be reopened; create a new owner.")
        expected = expected_version(data) if owner else None
        if record and record["workspace_id"] != current["workspace_id"]:
            fail("workspace_conflict", "An owner cannot change workspaces.")
        resources = data.get("resource")
        if not isinstance(resources, list) or not resources or not all(
                isinstance(p, str) and p.strip() for p in resources):
            fail("invalid_input", "Claim at least one literal resource path.")
        resources = sorted(set(str((Path(current["path"]) / Path(p).expanduser()).resolve()) for p in resources))
        if any(any(char in p for char in "*?[") for p in resources):
            fail("invalid_input", "Resources are literal paths; glob syntax is not supported.")
        if record and set(resources).issubset(record["resources"]):
            return {**result(home, state, current), "contribution": record, "changed": False}
        if record:
            check_version(record, expected)
        elif not isinstance(data.get("purpose"), str) or not data["purpose"].strip():
            fail("invalid_input", "A new owner requires a nonempty purpose.")
        conflicts = []
        for project in scan(home):
            for other in project["contributions"].values():
                if not other["active"] or (project["id"] == state["id"] and other["id"] == owner):
                    continue
                for requested in resources:
                    for reserved in other["resources"]:
                        if resource_overlap(Path(requested), Path(reserved).resolve()):
                            conflicts.append({"project_id": project["id"], "owner": other["id"], "purpose": other["purpose"],
                                              "workspace": other["workspace"], "resource": reserved,
                                              "requested": requested})
        if conflicts:
            fail("resource_conflict", "Resources overlap active ownership; coordinate before writing.", conflicts=conflicts)
        if record:
            record["resources"] = sorted(set(record["resources"]) | set(resources))
        else:
            owner = str(uuid.uuid4())
            record = {"id": owner, "purpose": data["purpose"], "workspace": current["path"],
                      "workspace_id": current["workspace_id"], "resources": resources,
                      "active": True, "handoff": "", "version": 0, "updated_at": ""}
            records[owner] = record
            if current not in state["roots"]:
                state["roots"].append(current)
    else:
        if not owner:
            fail("invalid_input", "Provide the contribution owner UUID.")
        expected = expected_version(data)
        if record is None:
            if operation == "drop":
                return {**result(home, state, current), "owner": owner, "changed": False}
            fail("owner_unknown", "Contribution owner does not exist.")
        if operation == "drop":
            if record["active"]:
                fail("active_contribution", "Active ownership cannot be dropped; release it first.")
            check_version(record, expected)
            del records[owner]
            save(home, state)
            return {**result(home, state, current), "owner": owner, "changed": True}
        if operation == "handoff":
            content = input_bytes(data).decode("utf-8")
            if not content.strip():
                fail("invalid_input", "Provide a nonempty Markdown handoff.")
            active = not bool(data.get("release"))
            if record["handoff"] == content and record["active"] == active:
                return {**result(home, state, current), "contribution": record, "changed": False}
            if not record["active"]:
                fail("owner_closed", "Closed ownership cannot be changed or reopened.")
            check_version(record, expected)
            record.update(handoff=content, active=active)
        elif operation == "release":
            reason = data.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                fail("invalid_input", "Provide a nonempty release reason.")
            if not record["active"]:
                return {**result(home, state, current), "contribution": record, "changed": False}
            check_version(record, expected)
            record.update(active=False, release_reason=reason)
    record["version"] += 1
    record["updated_at"] = now()
    save(home, state)
    return {**result(home, state, current), "contribution": record, "changed": True}


def knowledge_path(home, state, name):
    if (not isinstance(name, str) or not name or Path(name).is_absolute()
            or ".." in Path(name).parts or Path(name).suffix != ".md"):
        fail("unsafe_path", "Use a relative .md filename inside knowledge, without '..'.")
    directory = project_directory(home, state["id"]) / "knowledge"
    target = directory / name
    # Reject links even when they presently point inside knowledge: CAS addresses one name.
    for path in [directory, *target.relative_to(directory).parents]:
        candidate = path if path.is_absolute() else directory / path
        if candidate.is_symlink():
            fail("unsafe_path", "Knowledge paths must not contain symbolic links.", path=str(candidate))
    if target.is_symlink() or not contains(directory.resolve(), target.resolve()):
        fail("unsafe_path", "Knowledge path escapes its directory or is a symbolic link.", path=str(target))
    return target


def observe(path):
    try:
        content = path.read_bytes()
    except FileNotFoundError:
        return {"missing": True, "sha256": "missing", "content": None}
    try:
        text = content.decode("utf-8")
    except UnicodeError:
        fail("invalid_document", "Knowledge file is not UTF-8 Markdown.", path=str(path))
    return {"missing": False, "sha256": hashlib.sha256(content).hexdigest(), "content": text}


def document(operation, home, state, current, data):
    path = knowledge_path(home, state, data.get("file"))
    observed = observe(path)
    base = {**result(home, state, current), "file": data["file"]}
    if operation == "read":
        return {**base, **observed}
    expected = data.get("expect")
    if not isinstance(expected, str) or not (expected == "missing" or (
            len(expected) == 64 and all(c in "0123456789abcdef" for c in expected))):
        fail("invalid_input", "Expect must be the observed SHA-256 or 'missing'.")
    if operation == "write":
        content = input_bytes(data)
        digest = hashlib.sha256(content).hexdigest()
        if digest == observed["sha256"]:
            return {**base, **observed, "changed": False}
        if expected != observed["sha256"]:
            fail("document_conflict", "Knowledge changed; read it before retrying.", observed=observed, file=data["file"])
        make_directory(path.parent)
        atomic_write(path, content)
        return {**base, "missing": False, "sha256": digest, "content": content.decode("utf-8"), "changed": True}
    if expected == "missing":
        fail("invalid_input", "Delete requires the observed SHA-256.")
    if observed["missing"]:
        return {**base, **observed, "changed": False}
    if expected != observed["sha256"]:
        fail("document_conflict", "Knowledge changed; read it before deleting.", observed=observed, file=data["file"])
    path.unlink()
    try:
        sync_directory(path.parent)
    except OSError as exc:
        fail("write_uncertain", "File was removed but durability is uncertain; inspect it.", reason=str(exc))
    return {**base, "missing": True, "sha256": "missing", "content": None, "changed": True}


def dispatch(operation, data, home):
    if operation in {"init", "bind"}:
        return initialize(home, data, operation == "bind")
    state, current = select(home, data)
    if operation == "resolve":
        return result(home, state, current)
    if operation == "status":
        reservations = [{"owner": record["id"], "purpose": record["purpose"],
                         "workspace": record["workspace"], "workspace_id": record["workspace_id"],
                         "version": record["version"], "resource": resource}
                        for record in state["contributions"].values() if record["active"]
                        for resource in record["resources"]]
        return {**result(home, state, current), "contributions": state["contributions"], "reservations": reservations}
    if operation in {"read", "write", "delete"}:
        return document(operation, home, state, current, data)
    return ownership(operation, home, state, current, data)


def execute(operation, data, home=None):
    """Execute one operation; return JSON-compatible data or raise Error."""
    if operation not in {"init", "bind", "resolve", "status", "claim", "handoff", "release", "drop", "read", "write", "delete"}:
        fail("invalid_operation", "Unknown operation.", operation=operation)
    if not isinstance(data, dict):
        fail("invalid_input", "Operation arguments must be a dictionary.")
    try:
        home = Path(home or os.environ.get("HARNESS_HOME", "~/.harness")).expanduser().resolve()
        if operation in {"resolve", "status", "read"}:
            return dispatch(operation, data, home)
        # Reject unsafe project/home relationships before creating even the lock file.
        if data.get("project"):
            probe(data["project"], home)
        with locked(home):
            return dispatch(operation, data, home)
    except Error:
        raise
    except (OSError, ValueError, TypeError) as exc:
        fail("io_error", "Harness could not complete the operation.", reason=str(exc))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=VERSION)
    parser.add_argument("--home", help="External storage directory (default: HARNESS_HOME or ~/.harness)")
    commands = parser.add_subparsers(dest="operation", required=True)
    for operation in ("resolve", "init", "bind", "status", "claim", "handoff", "release", "drop", "read", "write", "delete"):
        command = commands.add_parser(operation)
        if operation in {"init", "bind", "claim"}:
            command.add_argument("--project", required=True)
        else:
            selector = command.add_mutually_exclusive_group(required=True)
            selector.add_argument("--project")
            selector.add_argument("--project-id")
        if operation == "init":
            command.add_argument("--name")
        if operation == "bind":
            command.add_argument("--project-id", required=True)
            command.add_argument("--replace")
        if operation == "claim":
            command.add_argument("--purpose")
            command.add_argument("--resource", action="append", required=True)
            command.add_argument("--owner")
            command.add_argument("--expect", type=int)
        if operation in {"handoff", "release", "drop"}:
            command.add_argument("--owner", required=True)
            command.add_argument("--expect", required=True, type=int)
        if operation == "handoff":
            command.add_argument("--release", action="store_true")
        if operation == "release":
            command.add_argument("--reason", required=True)
        if operation in {"handoff", "write"}:
            command.add_argument("--input", required=True)
        if operation in {"read", "write", "delete"}:
            command.add_argument("--file", required=True)
        if operation in {"write", "delete"}:
            command.add_argument("--expect", required=True)
    arguments = vars(parser.parse_args(argv))
    operation, home = arguments.pop("operation"), arguments.pop("home")
    try:
        output = execute(operation, arguments, home)
    except Error as exc:
        print(json.dumps({"error": {"code": exc.code, "message": exc.message, "details": exc.details}}))
        return 1
    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
