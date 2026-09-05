"""Transactional, file-native Harness runtime. Python standard library only.

The project snapshot is the transaction boundary. Readers never initialize state;
writers serialize on an OS advisory lock and replace one complete snapshot.
"""

from __future__ import annotations

import base64
import contextlib
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
import unicodedata
import uuid


SCHEMA_VERSION = 3
DEFAULTS_VERSION = 8
PRESENCE_SECONDS = 1800
KINDS = {"fact", "hypothesis", "decision", "historical"}
MEMORY_STATUSES = {"current", "stale", "superseded", "retracted"}
SESSION_STATUSES = {"active", "blocked", "delivered", "released"}


class HarnessError(RuntimeError):
    def __init__(self, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def _fail(code: str, message: str, **details):
    raise HarnessError(code, message, details)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def home_path() -> Path:
    return Path(os.environ.get("HARNESS_HOME", "~/.harness")).expanduser().resolve()


def _uuid(value: str) -> str:
    try:
        result = str(uuid.UUID(value))
    except (ValueError, TypeError, AttributeError):
        _fail("invalid_project_id", "A canonical project UUID is required.")
    if result != value:
        _fail("invalid_project_id", "Use the lowercase, hyphenated project UUID.")
    return result


def state_path(home: Path, project_id: str) -> Path:
    return Path(home) / "projects" / _uuid(project_id) / "state.json"


@contextlib.contextmanager
def locked(home: Path, timeout: float = 10.0):
    """Hold a process-safe lock. Age never grants permission to break this lock."""
    try:
        import fcntl
    except ImportError:
        _fail("unsupported_platform", "Harness writes require POSIX advisory flock support.")
    home = Path(home)
    home.mkdir(parents=True, exist_ok=True)
    with (home / ".runtime.lock").open("a+b") as handle:
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    _fail("lock_busy", "Another Harness transaction is still running. Retry the same request ID.")
                time.sleep(0.01)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def atomic_json(path: Path, data: dict) -> None:
    """Durably replace one snapshot. A failed replace leaves the old file intact."""
    encoded = (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2,
                          allow_nan=False) + "\n").encode("utf-8")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".state-", dir=path.parent)
    replaced = False
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        replaced = True
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except OSError as exc:
        raise HarnessError(
            "write_uncertain" if replaced else "write_failed",
            "Snapshot durability was not confirmed. Retry the same request ID."
            if replaced else "Snapshot replacement failed; the previous snapshot is unchanged.",
            {"path": str(path), "reason": str(exc)},
        ) from exc
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary)


def new_state(project_id: str, title: str = "") -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "defaults_version": DEFAULTS_VERSION,
        "project": {"id": _uuid(project_id), "title": title, "created_at": utc_now(), "bindings": []},
        "revision": 0, "workspaces": {}, "tasks": {}, "sessions": {},
        "checkpoints": {}, "claims": {}, "memories": {}, "events": [], "receipts": {},
    }


def _no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read_state(path: Path) -> dict:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_no_duplicate_keys,
                           parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (OSError, ValueError, UnicodeError) as exc:
        raise HarnessError("corrupt_state", "Cannot read the canonical project snapshot; repair or restore it before continuing.",
                           {"path": str(path), "reason": str(exc)}) from exc
    if not isinstance(value, dict):
        _fail("corrupt_state", "Project snapshot must be a JSON object.", path=str(path))
    if value.get("schema_version") != SCHEMA_VERSION:
        _fail("unsupported_schema", "This runtime supports only schema 3 snapshots.",
              path=str(path), found=value.get("schema_version"), supported=SCHEMA_VERSION)
    if not isinstance(value.get("defaults_version"), int) or value["defaults_version"] > DEFAULTS_VERSION:
        _fail("unsupported_defaults", "Snapshot defaults version is invalid or newer than this runtime supports.", path=str(path))
    if not isinstance(value.get("revision"), int) or isinstance(value["revision"], bool) or value["revision"] < 0:
        _fail("corrupt_state", "Snapshot revision is invalid.", path=str(path))
    for key in ("project", "workspaces", "tasks", "sessions", "checkpoints", "claims", "memories", "receipts"):
        if not isinstance(value.get(key), dict):
            _fail("corrupt_state", f"Snapshot {key} must be an object.", path=str(path))
    try:
        project_id = _uuid(value["project"].get("id"))
    except HarnessError as exc:
        raise HarnessError("corrupt_state", "Snapshot project identity is invalid.", {"path": str(path)}) from exc
    if Path(path).parent.name != project_id:
        _fail("corrupt_state", "Snapshot identity disagrees with its project directory.", path=str(path))
    if not isinstance(value["project"].get("bindings"), list) or not isinstance(value.get("events"), list):
        _fail("corrupt_state", "Snapshot bindings and events must be arrays.", path=str(path))
    for binding in value["project"]["bindings"]:
        if (not isinstance(binding, dict) or binding.get("kind") not in {"path", "git_common_dir", "host"}
                or not isinstance(binding.get("value"), str) or not binding["value"]):
            _fail("corrupt_state", "Snapshot contains an invalid identity binding.", path=str(path))
    for collection in ("workspaces", "tasks", "sessions", "checkpoints", "claims", "memories"):
        for key, record in value[collection].items():
            if not isinstance(record, dict) or record.get("id") != key:
                _fail("corrupt_state", f"Invalid {collection} record identity.", path=str(path), id=key)
    text_fields = {
        "workspaces": ("path", "kind", "git_common_dir"),
        "tasks": ("title", "objective", "status", "created_at", "updated_at"),
        "sessions": ("task_id", "workspace_id", "status", "created_at", "updated_at"),
        "checkpoints": ("task_id", "session_id", "workspace_id", "summary", "next_action", "status", "created_at"),
        "claims": ("task_id", "session_id", "workspace_id", "resource", "path", "acquired_at"),
        "memories": ("title", "summary", "content", "kind", "status", "scope", "created_at", "updated_at"),
    }
    list_fields = {"tasks": ("session_ids", "events"), "sessions": ("checkpoint_ids",),
                   "checkpoints": ("evidence",), "memories": ("sources", "aliases")}
    for collection, fields in text_fields.items():
        for record in value[collection].values():
            if any(not isinstance(record.get(field), str) for field in fields):
                _fail("corrupt_state", f"A {collection} record is missing a required text field.", path=str(path), id=record["id"])
            if any(not isinstance(record.get(field), list) for field in list_fields.get(collection, ())):
                _fail("corrupt_state", f"A {collection} record is missing a required array.", path=str(path), id=record["id"])
            for field in ("session_ids", "checkpoint_ids", "aliases"):
                if field in record and not all(isinstance(item, str) for item in record[field]):
                    _fail("corrupt_state", f"Invalid string array {field}.", path=str(path), id=record["id"])
    for task in value["tasks"].values():
        if task["status"] not in {"active", "blocked", "delivered"}:
            _fail("corrupt_state", "Invalid task lifecycle status.", path=str(path), id=task["id"])
        for event in task["events"]:
            if (not isinstance(event, dict) or not all(isinstance(event.get(field), str) for field in ("id", "kind", "session_id", "created_at"))
                    or not isinstance(event.get("evidence"), list) or event["kind"] not in {"accepted", "committed", "published", "resolved"}
                    or not isinstance(event.get("revision"), int)):
                _fail("corrupt_state", "Invalid task lifecycle event.", path=str(path), id=task["id"])
            for field in ("resolves_checkpoint_ids", "resolves_session_ids"):
                if not isinstance(event.get(field, []), list) or not all(isinstance(item, str) for item in event.get(field, [])):
                    _fail("corrupt_state", "Invalid explicit task resolution target array.", path=str(path), id=event["id"])
    for session in value["sessions"].values():
        if session["status"] not in SESSION_STATUSES:
            _fail("corrupt_state", "Invalid participant lifecycle status.", path=str(path), id=session["id"])
    for memory in value["memories"].values():
        if memory["kind"] not in KINDS or memory["status"] not in MEMORY_STATUSES:
            _fail("corrupt_state", "Invalid memory epistemic kind or status.", path=str(path), id=memory["id"])
        if memory.get("superseded_by") is not None and not isinstance(memory["superseded_by"], str):
            _fail("corrupt_state", "Invalid memory supersession target.", path=str(path), id=memory["id"])
    for collection in ("memories", "checkpoints"):
        for record in value[collection].values():
            if type(record.get("revision")) is not int or not 0 <= record["revision"] <= value["revision"]:
                _fail("corrupt_state", f"Invalid {collection} record revision.", path=str(path), id=record["id"])
    for workspace in value["workspaces"].values():
        if not isinstance(workspace.get("path"), str) or not Path(workspace["path"]).is_absolute():
            _fail("corrupt_state", "Workspace requires an absolute path.", path=str(path))
        if workspace["kind"] not in {"git", "directory"}:
            _fail("corrupt_state", "Unknown workspace kind.", path=str(path), id=workspace["id"])
    for claim in value["claims"].values():
        if (not isinstance(claim.get("path"), str) or not Path(claim["path"]).is_absolute()
                or not all(isinstance(claim.get(key), str) for key in ("task_id", "session_id", "workspace_id"))):
            _fail("corrupt_state", "Claim ownership or resource is invalid.", path=str(path))
        if "released_at" not in claim or claim["released_at"] is not None and not isinstance(claim["released_at"], str):
            _fail("corrupt_state", "Claim release state is invalid.", path=str(path), id=claim["id"])
    previous_revision = 0
    for event in value["events"]:
        if (not isinstance(event, dict) or not isinstance(event.get("revision"), int)
                or event["revision"] != previous_revision + 1 or event["revision"] > value["revision"]):
            _fail("corrupt_state", "Journal revisions must be consecutive and within the snapshot revision.", path=str(path))
        previous_revision = event["revision"]
    if previous_revision != value["revision"]:
        _fail("corrupt_state", "The canonical journal is missing one or more snapshot revisions.", path=str(path))
    for request_id, receipt in value["receipts"].items():
        if (not isinstance(receipt, dict) or not isinstance(receipt.get("digest"), str)
                or not isinstance(receipt.get("result"), dict) or type(receipt["result"].get("revision")) is not int):
            _fail("corrupt_state", "Invalid idempotency receipt.", path=str(path), request_id=request_id)
    return value


def _contains(parent: Path, child: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _outside(home: Path, workspace: dict) -> None:
    if _contains(Path(workspace["path"]), home):
        _fail("state_inside_project", "HARNESS_HOME must be outside the registered project directory.",
              home=str(home), project=workspace["path"])


def _project_path(project) -> Path:
    if not isinstance(project, (str, Path)) or not str(project).strip():
        _fail("invalid_input", "Provide the project directory in 'project'.")
    path = Path(project).expanduser().resolve()
    if not path.is_dir():
        _fail("project_missing", "Project directory does not exist.", project=str(path))
    return path


def _git(path: Path, *args: str) -> str:
    try:
        result = subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True,
                                check=False, timeout=5)
    except FileNotFoundError:
        return ""
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HarnessError("git_unavailable", "Git identity could not be checked.", {"reason": str(exc)}) from exc
    return result.stdout.strip() if result.returncode == 0 else ""


def _probe(path: Path) -> dict:
    root = _git(path, "rev-parse", "--show-toplevel")
    if root:
        root_path = Path(root).resolve()
        common = _git(root_path, "rev-parse", "--git-common-dir")
        if not common:
            _fail("git_unavailable", "Git common-directory identity could not be checked.")
        common_path = Path(common)
        if not common_path.is_absolute():
            common_path = root_path / common_path
        return {"path": str(root_path), "kind": "git", "git_common_dir": str(common_path.resolve())}
    return {"path": str(path), "kind": "directory", "git_common_dir": ""}


def _scan(home: Path) -> list[dict]:
    projects = home / "projects"
    if not projects.exists():
        return []
    result = []
    for folder in sorted(projects.iterdir()):
        if not folder.is_dir():
            continue
        snapshot = folder / "state.json"
        if snapshot.exists():
            result.append(read_state(snapshot))
        elif not folder.name.startswith("."):
            _fail("incomplete_state", "A project directory has no canonical snapshot; inspect or restore it before initialization.", path=str(folder))
    return result


def _workspace(state: dict, probe: dict) -> dict:
    for workspace in state["workspaces"].values():
        if Path(workspace["path"]) == Path(probe["path"]):
            # Probe current physical identity rather than stale display metadata.
            return {**workspace, **probe}
    return {"id": str(uuid.uuid5(uuid.UUID(state["project"]["id"]), probe["path"])), **probe}


def _matches(state: dict, path: Path, probe: dict, host: str, host_project_id: str) -> tuple[bool, dict]:
    bindings = state["project"]["bindings"]
    common = probe["git_common_dir"]
    if common and any(b["kind"] == "git_common_dir" and b["value"] == common for b in bindings):
        return True, _workspace(state, probe)
    if host and host_project_id and any(b["kind"] == "host" and b.get("host") == host
                                       and b["value"] == host_project_id for b in bindings):
        # A host binding selects identity, but still cannot enroll an arbitrary path silently.
        known = any(b["kind"] == "path" and Path(b["value"]) == Path(probe["path"]) for b in bindings)
        if known:
            return True, _workspace(state, probe)
    candidates = []
    for workspace in state["workspaces"].values():
        root = Path(workspace["path"])
        if workspace.get("kind") == "directory" and not common and _contains(root, path):
            candidates.append(workspace)
        elif common and workspace.get("kind") == "directory" and root.is_dir():
            # A registered directory that later becomes Git can remain the same
            # project when its current physical topology proves the relationship.
            registered = _probe(root)
            if registered["path"] == str(root) and registered["git_common_dir"] == common:
                return True, _workspace(state, probe)
        elif common and root == Path(probe["path"]) and workspace.get("git_common_dir") == common:
            candidates.append(workspace)
    if candidates:
        return True, max(candidates, key=lambda item: len(Path(item["path"]).parts))
    return False, probe


def resolve_state(home: Path, project, project_id: str = "", host: str = "", host_project_id: str = "") -> tuple[dict, dict]:
    """Resolve a registered project and workspace without writing any files."""
    home = Path(home).expanduser().resolve()
    path = _project_path(project)
    probe = _probe(path)
    states = _scan(home)
    matches = []
    for state in states:
        matched, workspace = _matches(state, path, probe, host, host_project_id)
        if matched:
            matches.append((state, workspace))
    if len(matches) > 1:
        _fail("ambiguous_identity", "Multiple snapshots claim this workspace; explicitly reconcile the bindings.",
              project_ids=[state["project"]["id"] for state, _ in matches])
    if project_id:
        _uuid(project_id)
        if matches and matches[0][0]["project"]["id"] != project_id:
            _fail("identity_conflict", "The supplied project UUID differs from this workspace's registered identity.",
                  project_id=matches[0][0]["project"]["id"])
    if not matches:
        for state in states:
            for workspace in state["workspaces"].values():
                if workspace["path"] == probe["path"]:
                    _fail("identity_reconciliation_required", "This registered path has changed Git topology. Reconcile it with explicit project.bind evidence before continuing.",
                          project_id=state["project"]["id"], workspace_id=workspace["id"])
        _fail("not_initialized", "No project identity matches this directory. Initialize it or explicitly bind a known project UUID.", project=str(path))
    state, workspace = matches[0]
    _outside(home, workspace)
    return state, workspace


def _text(data: dict, name: str, required: bool = True, default: str = "") -> str:
    value = data.get(name, default)
    if not isinstance(value, str) or (required and not value.strip()):
        _fail("invalid_input", f"'{name}' must be {'a non-empty' if required else 'a'} string.")
    return value.strip()


def _array(data: dict, name: str, default=None) -> list:
    value = data.get(name, [] if default is None else default)
    if not isinstance(value, list):
        _fail("invalid_input", f"'{name}' must be an array.")
    return copy.deepcopy(value)


def _integer(data: dict, name: str, default: int, maximum: int | None = None) -> int:
    value = data.get(name, default)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0 or (maximum is not None and value > maximum):
        _fail("invalid_input", f"'{name}' must be a non-negative integer" + (f" at most {maximum}." if maximum else "."))
    return value


def _expected(state: dict, data: dict) -> None:
    if "expected_revision" in data and _integer(data, "expected_revision", 0) != state["revision"]:
        _fail("revision_conflict", "The project changed since the supplied revision. Read current state and reconcile before retrying.",
              expected=data["expected_revision"], current=state["revision"])


def _result(state: dict, **values) -> dict:
    return {"success": True, "project_id": state["project"]["id"], "revision": state["revision"], **values}


def _digest(operation: str, data: dict) -> str:
    return hashlib.sha256(json.dumps({"operation": operation, "data": data}, sort_keys=True,
                                    ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()).hexdigest()


def _replay(state: dict, operation: str, data: dict) -> dict | None:
    request_id = _text(data, "request_id")
    previous = state["receipts"].get(request_id)
    if previous is None:
        return None
    if not isinstance(previous, dict) or not isinstance(previous.get("result"), dict):
        _fail("corrupt_state", "The idempotency receipt is invalid.", request_id=request_id)
    if previous.get("digest") != _digest(operation, data):
        _fail("request_id_reused", "This request ID was already used for different input. Use a new request ID for a new action.", request_id=request_id)
    result = copy.deepcopy(previous["result"])
    replayed = {**result, "original_revision": result["revision"], "revision": state["revision"], "replayed": True}
    if operation in {"remember", "memory.update"}:
        replayed["next"] = "Use hydrate with memory.id to read the current canonical record."
    return replayed


def _commit(home: Path, state: dict, operation: str, data: dict, values: dict, details: dict) -> dict:
    state["revision"] += 1
    state["defaults_version"] = DEFAULTS_VERSION
    state["events"].append({"id": str(uuid.uuid4()), "revision": state["revision"], "operation": operation,
                            "created_at": utc_now(), "details": details})
    result = _result(state, **values)
    if data.get("request_id"):
        receipt_result = copy.deepcopy(result)
        if operation in {"remember", "memory.update"}:
            receipt_result = _result(
                state,
                memory={"id": result["memory"]["id"], "revision": result["memory"]["revision"]},
            )
        state["receipts"][data["request_id"]] = {"digest": _digest(operation, data), "result": receipt_result}
    atomic_json(state_path(home, state["project"]["id"]), state)
    return result


def _enroll(state: dict, workspace: dict, data: dict) -> None:
    state["workspaces"][workspace["id"]] = workspace
    bindings = state["project"]["bindings"]
    wanted = [{"kind": "path", "value": workspace["path"]}]
    if workspace["git_common_dir"]:
        wanted.append({"kind": "git_common_dir", "value": workspace["git_common_dir"]})
    host = _text(data, "host", False)
    host_id = _text(data, "host_project_id", False)
    if bool(host) != bool(host_id):
        _fail("invalid_input", "Optional host and host_project_id must be supplied together.")
    if host:
        wanted.append({"kind": "host", "host": host, "value": host_id})
    for binding in wanted:
        if binding not in bindings:
            bindings.append(binding)


def _guard_overlap(states: list[dict], probe: dict, project_id: str = "") -> None:
    proposed = Path(probe["path"])
    for state in states:
        if state["project"]["id"] == project_id:
            continue
        for workspace in state["workspaces"].values():
            existing = Path(workspace["path"])
            if _contains(proposed, existing) or _contains(existing, proposed):
                _fail("identity_overlap", "The proposed project scope overlaps another registered project. Reconcile the existing identity instead of creating overlapping projects.",
                      project_id=state["project"]["id"], workspace_id=workspace["id"], existing_path=str(existing), proposed_path=str(proposed))


def _initialize(home: Path, data: dict) -> dict:
    path = _project_path(data.get("project"))
    probe = _probe(path)
    _outside(home, probe)
    try:
        state, workspace = resolve_state(home, path, data.get("project_id", ""), data.get("host", ""), data.get("host_project_id", ""))
    except HarnessError as exc:
        if exc.code != "not_initialized":
            raise
        if data.get("project_id"):
            _fail("explicit_binding_required", "A supplied project UUID must be associated with this directory using project.bind and evidence.")
        _guard_overlap(_scan(home), probe)
        state = new_state(str(uuid.uuid4()), _text(data, "title", False, path.name))
        workspace = _workspace(state, probe)
        _enroll(state, workspace, data)
        return _commit(home, state, "init", data, {"created": True, "workspace": workspace, "project": state["project"]}, {"workspace_id": workspace["id"]})
    if data.get("request_id"):
        replay = _replay(state, "init", data)
        if replay:
            return replay
    _expected(state, data)
    _guard_overlap(_scan(home), workspace, state["project"]["id"])
    old = copy.deepcopy((state["workspaces"], state["project"]["bindings"]))
    _enroll(state, workspace, data)
    if old != (state["workspaces"], state["project"]["bindings"]) or data.get("request_id"):
        return _commit(home, state, "init", data, {"created": False, "workspace": workspace, "project": state["project"]}, {"workspace_id": workspace["id"]})
    return _result(state, created=False, workspace=workspace, project=state["project"])


def _binding(home: Path, operation: str, data: dict) -> dict:
    project_id = _uuid(_text(data, "project_id"))
    states = _scan(home)
    state = next((item for item in states if item["project"]["id"] == project_id), None)
    if state is None:
        _fail("not_initialized", "The supplied project UUID has no canonical snapshot.")
    replay = _replay(state, operation, data)
    if replay:
        return replay
    _expected(state, data)
    evidence = _array(data, "evidence")
    if not evidence:
        _fail("evidence_required", "Explicit binding or relocation needs evidence explaining why this is the same project.")
    path = _project_path(data.get("project"))
    probe = _probe(path)
    _outside(home, probe)
    _guard_overlap(states, probe, project_id)
    for other in states:
        matched, _ = _matches(other, path, probe, "", "")
        if matched and other["project"]["id"] != project_id:
            _fail("identity_conflict", "This directory already belongs to another project UUID.", project_id=other["project"]["id"])
    workspace = _workspace(state, probe)
    if operation == "project.move":
        old_path = str(Path(_text(data, "from_path")).expanduser().resolve())
        old = next((item for item in state["workspaces"].values() if item["path"] == old_path), None)
        if old is None:
            _fail("unknown_workspace", "from_path is not a registered workspace.")
        if Path(old_path).exists() and old_path != probe["path"]:
            _fail("old_path_exists", "The old workspace still exists. Use project.bind for an additional workspace.")
        if workspace["id"] in state["workspaces"] and workspace["id"] != old["id"]:
            _fail("workspace_conflict", "The destination is already a different registered workspace. Reconcile its participants before merging identities.")
        workspace["id"] = old["id"]
        retained_common = {item.get("git_common_dir") for key, item in state["workspaces"].items() if key != old["id"]}
        state["project"]["bindings"] = [b for b in state["project"]["bindings"] if not (
            (b["kind"] == "path" and b["value"] == old_path) or
            (b["kind"] == "git_common_dir" and b["value"] == old.get("git_common_dir") and b["value"] not in retained_common))]
        for claim in state["claims"].values():
            if claim["workspace_id"] == old["id"] and _contains(Path(old_path), Path(claim["path"])):
                claim["path"] = str(Path(workspace["path"]) / Path(claim["path"]).relative_to(old_path))
    _enroll(state, workspace, data)
    return _commit(home, state, operation, data, {"workspace": workspace}, {"workspace_id": workspace["id"], "evidence": evidence})


def _session(state: dict, data: dict, workspace: dict, active: bool = False) -> dict:
    session_id = _text(data, "session_id")
    session = state["sessions"].get(session_id)
    if session is None:
        _fail("unknown_session", "Session not found. Start or join a task to obtain a participant session ID.", session_id=session_id)
    if session.get("workspace_id") != workspace["id"]:
        _fail("workspace_mismatch", "This session belongs to another workspace. Join the task from the current workspace.", session_id=session_id)
    if active and session["status"] in {"delivered", "released"}:
        _fail("session_closed", "This participant has delivered or released its work. Join the task to begin a new contribution.", session_id=session_id)
    return session


def _resources(data: dict, workspace: dict) -> list[dict]:
    resources = _array(data, "resources")
    result = []
    seen = set()
    for resource in resources:
        if not isinstance(resource, str) or not resource.strip():
            _fail("invalid_resource", "Each resource must be a non-empty file or directory path.")
        if any(symbol in resource for symbol in "*?[]{}"):
            _fail("unsupported_glob", "Claims accept exact files or directory subtrees. Expand globs before claiming.", resource=resource)
        path = Path(resource).expanduser()
        if not path.is_absolute():
            path = Path(workspace["path"]) / path
        resolved = str(path.resolve())
        if resolved not in seen:
            result.append({"resource": resource, "path": resolved})
            seen.add(resolved)
    return result


def _live_claims(state: dict) -> list[dict]:
    return [claim for claim in state["claims"].values() if claim.get("released_at") is None]


def _presence(session: dict) -> str:
    if session.get("status") in {"released", "delivered"}:
        return "closed"
    if session.get("presence_unknown"):
        return "unknown"
    try:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(session["updated_at"])).total_seconds()
    except (ValueError, TypeError, KeyError):
        return "unknown"
    return "recent" if 0 <= age <= PRESENCE_SECONDS else "unknown"


def _claim_view(state: dict, claim: dict) -> dict:
    session = state["sessions"].get(claim["session_id"], {})
    task = state["tasks"].get(claim["task_id"], {})
    return {**claim, "owner_title": task.get("title", "Unknown task"), "owner_objective": task.get("objective", ""),
            "presence": _presence(session), "owner_status": session.get("status", "unknown")}


def _claim(state: dict, session: dict, workspace: dict, resources: list[dict]) -> list[dict]:
    conflicts = []
    active_claims = _live_claims(state)
    for resource in resources:
        path = Path(resource["path"])
        for existing in active_claims:
            if existing["session_id"] == session["id"]:
                continue
            other = Path(existing["path"]).resolve()
            if _contains(path, other) or _contains(other, path):
                conflicts.append({"requested": resource, "owner": _claim_view(state, existing)})
    if conflicts:
        _fail("resource_conflict", "Resources are owned by another participant. Coordinate with the listed owner; only explicit release removes a claim.", conflicts=conflicts)
    acquired = []
    for resource in resources:
        existing = next((claim for claim in active_claims if claim["session_id"] == session["id"] and claim["path"] == resource["path"]), None)
        if existing:
            acquired.append(existing)
            continue
        claim = {"id": str(uuid.uuid4()), "task_id": session["task_id"], "session_id": session["id"],
                 "workspace_id": workspace["id"], **resource, "acquired_at": utc_now(), "released_at": None, "release_reason": None}
        state["claims"][claim["id"]] = claim
        acquired.append(claim)
    return acquired


def _release(state: dict, session_id: str, reason: str) -> list[str]:
    released = []
    for claim in _live_claims(state):
        if claim["session_id"] == session_id:
            claim["released_at"] = utc_now()
            claim["release_reason"] = reason
            released.append(claim["id"])
    return released


def _resolutions(task: dict) -> tuple[dict, dict]:
    checkpoints, sessions = {}, {}
    for event in task.get("events", []):
        checkpoints.update({key: event["id"] for key in event.get("resolves_checkpoint_ids", [])})
        sessions.update({key: event["id"] for key in event.get("resolves_session_ids", [])})
    return checkpoints, sessions


def _task_status(state: dict, task: dict) -> None:
    if any(key not in state["sessions"] for key in task["session_ids"]):
        _fail("corrupt_state", "Task references a missing participant.", task_id=task["id"])
    sessions = [state["sessions"][key] for key in task["session_ids"]]
    statuses = [session["status"] for session in sessions]
    _, reconciled = _resolutions(task)
    if "active" in statuses:
        task["status"] = "active"
    elif "delivered" in statuses and all(session["status"] == "delivered" or
            (session["status"] == "released" and session["id"] in reconciled) for session in sessions):
        task["status"] = "delivered"
    else:
        task["status"] = "blocked"
    task["updated_at"] = utc_now()


def _task_mutation(state: dict, workspace: dict, operation: str, data: dict) -> tuple[dict, dict]:
    now = utc_now()
    if operation in {"task.start", "task.join"}:
        resources = _resources(data, workspace)
        if operation == "task.start":
            objective = _text(data, "objective")
            task = {"id": str(uuid.uuid4()), "title": _text(data, "title", False) or objective[:120], "objective": objective,
                    "status": "active", "created_at": now, "updated_at": now, "session_ids": [], "events": []}
        else:
            task = state["tasks"].get(_text(data, "task_id"))
            if task is None:
                _fail("unknown_task", "Task not found.")
        session = {"id": str(uuid.uuid4()), "task_id": task["id"], "workspace_id": workspace["id"],
                   "status": "active", "created_at": now, "updated_at": now, "checkpoint_ids": []}
        claims = _claim(state, session, workspace, resources)
        task["session_ids"].append(session["id"])
        task["status"] = "active"
        task["updated_at"] = now
        state["tasks"][task["id"]] = task
        state["sessions"][session["id"]] = session
        return {"task": task, "session": session, "claims": claims}, {"task_id": task["id"], "session_id": session["id"], "claim_ids": [c["id"] for c in claims]}
    if operation == "task.event":
        session = _session(state, data, workspace)
        kind = _text(data, "kind")
        if kind not in {"accepted", "committed", "published", "resolved"}:
            _fail("invalid_input", "Task events require kind accepted, committed, published, or resolved.")
        evidence = _array(data, "evidence")
        if not evidence:
            _fail("evidence_required", "Task lifecycle and follow-up resolution events need explicit evidence.")
        task = state["tasks"][session["task_id"]]
        targets = {}
        for field, collection in (("resolves_checkpoint_ids", "checkpoints"), ("resolves_session_ids", "sessions")):
            identifiers = _array(data, field)
            if not all(isinstance(key, str) and key for key in identifiers) or len(set(identifiers)) != len(identifiers):
                _fail("invalid_resolution", f"{field} must contain distinct record ID strings.")
            for key in identifiers:
                target = state[collection].get(key)
                if target is None or target["task_id"] != task["id"]:
                    _fail("invalid_resolution", "Resolution targets must exist and belong to this task.", id=key)
                if collection == "sessions" and target["status"] != "released":
                    _fail("invalid_resolution", "Only released participants can be reconciled by an event. Active or blocked work must checkpoint or release explicitly.", session_id=key)
                if collection == "sessions" and any(claim["session_id"] == key for claim in _live_claims(state)):
                    _fail("invalid_resolution", "The participant still owns claims. Release them explicitly before reconciling responsibility.", session_id=key)
            targets[field] = identifiers
        if kind == "resolved" and not any(targets.values()):
            _fail("invalid_resolution", "A resolved event must explicitly name checkpoint or released-session IDs.")
        event = {"id": str(uuid.uuid4()), "kind": kind, "session_id": session["id"], "evidence": evidence,
                 "summary": _text(data, "summary", False), "created_at": now, "revision": state["revision"] + 1, **targets}
        task["events"].append(event)
        _task_status(state, task)
        return {"task": task, "event": event}, {"task_id": task["id"], "event_id": event["id"], "kind": kind}
    session = _session(state, data, workspace, active=operation in {"task.claim", "task.checkpoint"})
    task = state["tasks"].get(session["task_id"])
    if task is None:
        _fail("corrupt_state", "Session references a missing task.", session_id=session["id"])
    details = {"task_id": task["id"], "session_id": session["id"]}
    if operation == "task.claim":
        claims = _claim(state, session, workspace, _resources(data, workspace))
        session["updated_at"] = now
        session.pop("presence_unknown", None)
        return {"claims": claims, "session": session}, {**details, "claim_ids": [c["id"] for c in claims]}
    if operation == "task.release":
        reason = _text(data, "reason")
        released = _release(state, session["id"], reason)
        if session["status"] != "delivered":
            session["status"] = "released"
        session["updated_at"] = now
        _task_status(state, task)
        return {"session": session, "task": task, "released_claim_ids": released}, {**details, "reason": reason, "released_claim_ids": released}
    if operation == "task.checkpoint":
        status = _text(data, "status", False, "active")
        if status not in {"active", "blocked", "delivered"}:
            _fail("invalid_input", "Checkpoint status must be active, blocked, or delivered.")
        checkpoint = {"id": str(uuid.uuid4()), **details, "workspace_id": workspace["id"],
                      "summary": _text(data, "summary"), "evidence": _array(data, "evidence"),
                      "next_action": _text(data, "next_action", False), "status": status,
                      "created_at": now, "revision": state["revision"] + 1}
        state["checkpoints"][checkpoint["id"]] = checkpoint
        session["checkpoint_ids"].append(checkpoint["id"])
        session["status"] = status
        session["updated_at"] = now
        session.pop("presence_unknown", None)
        released = _release(state, session["id"], "participant delivered") if status == "delivered" else []
        _task_status(state, task)
        return {"checkpoint": checkpoint, "session": session, "task": task, "released_claim_ids": released}, {**details, "checkpoint_id": checkpoint["id"], "status": status, "released_claim_ids": released}
    _fail("unknown_operation", "Unsupported task operation.", operation=operation)


def _memory_mutation(state: dict, operation: str, data: dict) -> tuple[dict, dict]:
    now = utc_now()
    if operation == "remember":
        kind = _text(data, "kind")
        if kind not in KINDS:
            _fail("invalid_input", "Memory kind must be fact, hypothesis, decision, or historical.")
        aliases = _array(data, "aliases")
        if not all(isinstance(alias, str) and alias.strip() for alias in aliases):
            _fail("invalid_input", "Aliases must be non-empty strings, including explicit multilingual terms when useful.")
        memory = {"id": str(uuid.uuid4()), "title": _text(data, "title"), "summary": _text(data, "summary"),
                  "content": _text(data, "content"), "kind": kind, "status": "current",
                  "sources": _array(data, "sources"), "scope": _text(data, "scope", False, "project"),
                  "aliases": aliases, "created_at": now, "updated_at": now, "revision": state["revision"] + 1,
                  "review_after": data.get("review_after"), "superseded_by": None}
    else:
        memory_id = _text(data, "id")
        memory = state["memories"].get(memory_id)
        if memory is None:
            _fail("not_found", "Memory record not found.", id=memory_id)
        if "expected_revision" not in data:
            _fail("invalid_input", "memory.update requires the memory record's expected_revision.")
        if _integer(data, "expected_revision", 0) != memory["revision"]:
            _fail("revision_conflict", "Memory changed since the supplied record revision.", expected=data["expected_revision"], current=memory["revision"])
        fields = {"title", "summary", "content", "kind", "status", "sources", "scope", "aliases", "review_after", "superseded_by"}
        if not fields.intersection(data):
            _fail("invalid_input", "Provide an explicit memory field or status to update.")
        for field in ("title", "summary", "content", "scope", "kind", "status"):
            if field in data:
                memory[field] = _text(data, field)
        if memory["kind"] not in KINDS or memory["status"] not in MEMORY_STATUSES:
            _fail("invalid_input", "Unknown epistemic kind or memory status.")
        for field in ("sources", "aliases"):
            if field in data:
                memory[field] = _array(data, field)
        if not all(isinstance(alias, str) and alias.strip() for alias in memory["aliases"]):
            _fail("invalid_input", "Aliases must be non-empty strings.")
        for field in ("review_after", "superseded_by"):
            if field in data:
                memory[field] = data[field]
        if memory.get("superseded_by") is not None and not isinstance(memory["superseded_by"], str):
            _fail("invalid_supersession", "superseded_by must be a record ID string or null.")
        if memory["status"] == "superseded":
            replacement = memory.get("superseded_by")
            if replacement == memory_id or replacement not in state["memories"]:
                _fail("invalid_supersession", "A superseded memory must name a different existing replacement record.")
            visited = {memory_id}
            while replacement:
                if replacement in visited:
                    _fail("invalid_supersession", "Memory supersession must not form a cycle.")
                visited.add(replacement)
                replacement = state["memories"][replacement].get("superseded_by")
                if replacement and replacement not in state["memories"]:
                    _fail("corrupt_state", "An existing memory has a missing supersession target.")
        elif memory.get("superseded_by"):
            _fail("invalid_supersession", "superseded_by is only valid when status is superseded. Clear it explicitly when changing status.")
        memory.pop("history", None)
        memory["updated_at"] = now
        memory["revision"] = state["revision"] + 1
    if memory.get("review_after") is not None:
        try:
            date = datetime.fromisoformat(memory["review_after"])
            if date.tzinfo is None:
                _fail("invalid_input", "review_after requires an ISO timestamp with a timezone.")
        except (TypeError, ValueError):
            _fail("invalid_input", "review_after requires an ISO timestamp with a timezone or null.")
    state["memories"][memory["id"]] = memory
    return {"memory": memory}, {"memory_id": memory["id"], "kind": memory["kind"], "status": memory["status"]}


def _task_view(state: dict, task: dict, current_workspace: str) -> dict:
    if any(key not in state["sessions"] for key in task["session_ids"]):
        _fail("corrupt_state", "Task references a missing participant.", task_id=task["id"])
    sessions = [{**state["sessions"][key], "presence": _presence(state["sessions"][key])} for key in task["session_ids"]]
    return {**task, "sessions": sessions,
            "current_workspace": any(session["workspace_id"] == current_workspace for session in sessions),
            "claims": [_claim_view(state, c) for c in _live_claims(state) if c["task_id"] == task["id"]]}


def _json_size(value) -> int:
    return len(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def _cursor(project_id: str, after: int, through: int) -> str:
    encoded = json.dumps({"project_id": project_id, "after": after, "through": through}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(encoded).decode().rstrip("=")


def _changes(state: dict, data: dict) -> dict:
    since = _integer(data, "since", 0)
    through = state["revision"]
    if data.get("cursor"):
        try:
            raw = data["cursor"]
            decoded = json.loads(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)))
            if decoded["project_id"] != state["project"]["id"]:
                raise ValueError("wrong project")
            since, through = decoded["after"], decoded["through"]
            if any(not isinstance(v, int) or isinstance(v, bool) for v in (since, through)) or not 0 <= since <= through <= state["revision"]:
                raise ValueError("revision outside snapshot")
        except (ValueError, TypeError, KeyError):
            _fail("invalid_cursor", "Change cursor is malformed, belongs to another project, or refers to a future revision.")
    if since > state["revision"]:
        _fail("invalid_cursor", "The requested revision is ahead of the current snapshot.", since=since, current=state["revision"])
    budget = _integer(data, "budget_chars", 16000)
    limit = _integer(data, "limit", 100, 10000)
    available = [event for event in state["events"] if since < event["revision"] <= through]
    entries = []
    budget_blocked = False
    for event in available:
        if len(entries) >= limit:
            break
        if _json_size(entries + [event]) > budget:
            budget_blocked = True
            break
        entries.append(event)
    after = entries[-1]["revision"] if entries else since
    more = len(entries) < len(available)
    if not more:
        after = through
    return _result(state, events=entries, through_revision=through, next_revision=after,
                   next_cursor=_cursor(state["project"]["id"], after, through) if more else None,
                   has_more=more, omitted_budget=len(available) - len(entries) if budget_blocked else 0,
                   omitted_limit=len(available) - len(entries) if more and not budget_blocked else 0,
                   blocked_by_budget=budget_blocked, required_chars=_json_size([available[len(entries)]]) if budget_blocked else None,
                   chars_used=_json_size(entries) if entries else 0,
                   status="omitted_budget" if budget_blocked and not entries else ("found" if entries else ("omitted_limit" if more else "absent")))


def _tokens(text: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    normalized = "".join(character for character in normalized if not unicodedata.combining(character))
    return set(re.findall(r"[^\W_]+", normalized, re.UNICODE))


_ALIAS_GROUPS = (
    "authentication autenticacao auth", "memory memoria memories memorias", "review revisao revisoes reviews",
    "documentation documentacao docs", "project projeto projetos projects", "error erro erros errors bug bugs",
    "mobile movel moveis", "artifact artefato artefatos artifacts", "claim ownership posse propriedade",
    "checkpoint handoff continuidade", "test teste testes tests", "decision decisao decisoes decisions",
)


def _terms(query: str) -> tuple[set[str], list[str]]:
    terms = _tokens(query)
    original = set(terms)
    for group in _ALIAS_GROUPS:
        group_terms = set(group.split())
        if original.intersection(group_terms):
            terms.update(group_terms)
    return terms, sorted(terms - original)


def _stale(memory: dict) -> bool:
    if memory.get("status") == "stale":
        return True
    if not memory.get("review_after"):
        return False
    try:
        return datetime.fromisoformat(memory["review_after"]) <= datetime.now(timezone.utc)
    except (ValueError, TypeError):
        return True


def _card(memory: dict) -> dict:
    return {key: memory.get(key) for key in ("id", "title", "summary", "kind", "status", "scope", "sources", "aliases", "created_at", "updated_at", "revision", "superseded_by")} | {"stale": _stale(memory), "type": "memory"}


def _recall(state: dict, data: dict) -> dict:
    query = _text(data, "query", False)
    terms, expanded = _terms(query)
    limit = _integer(data, "limit", 10, 1000)
    budget = _integer(data, "budget_chars", 8000)
    scope = _text(data, "scope", False)
    candidates = []
    for memory in state["memories"].values():
        if scope and memory.get("scope") != scope:
            continue
        title_terms = _tokens(memory.get("title", "") + " " + " ".join(memory.get("aliases", [])))
        body_terms = _tokens(memory.get("summary", "") + " " + memory.get("content", ""))
        score = 3 * len(terms & title_terms) + len(terms & body_terms)
        if not terms or score:
            candidates.append((score, memory.get("updated_at", ""), _card(memory)))
    candidates.sort(key=lambda item: (-item[0], item[2]["id"]))
    entries, omitted = [], []
    limited = candidates[:limit]
    for _, _, card in limited:
        if _json_size(entries + [card]) <= budget:
            entries.append(card)
        else:
            omitted.append(card["id"])
    status = "found" if entries else ("omitted_budget" if omitted else ("omitted_limit" if candidates else "absent"))
    return _result(state, entries=entries, status=status, total_matches=len(candidates), omitted_budget=len(omitted),
                   omitted_limit=max(0, len(candidates) - limit), omitted_ids=omitted, chars_used=_json_size(entries) if entries else 0,
                   diagnostics={"method": "lexical", "expanded_terms": expanded,
                                "limitation": "Lexical matching with a small Portuguese/English alias list; explicit record aliases improve recall. No semantic equivalence is inferred."})


def _hydrate(state: dict, data: dict) -> dict:
    record_id = _text(data, "id")
    budget = _integer(data, "budget_chars", 16000)
    entry = state["memories"].get(record_id) or state["checkpoints"].get(record_id)
    if entry is None:
        return _result(state, status="absent", entry=None, chars_used=0)
    size = _json_size(entry)
    if size > budget:
        return _result(state, status="omitted_budget", entry=None, required_chars=size, chars_used=0)
    return _result(state, status="found", entry=copy.deepcopy(entry), chars_used=size)


def _integrity(state: dict, workspace: dict) -> list[dict]:
    issues = []
    for session in state["sessions"].values():
        if session.get("task_id") not in state["tasks"] or session.get("workspace_id") not in state["workspaces"]:
            issues.append({"kind": "broken_session_reference", "id": session["id"]})
        if _presence(session) == "unknown":
            issues.append({"kind": "unknown_presence", "id": session["id"], "action": "Reconcile with the owner; age never releases claims."})
        for checkpoint_id in session.get("checkpoint_ids", []):
            if checkpoint_id not in state["checkpoints"]:
                issues.append({"kind": "missing_checkpoint", "id": checkpoint_id})
    for task in state["tasks"].values():
        if any(key not in state["sessions"] for key in task.get("session_ids", [])):
            issues.append({"kind": "missing_participant", "id": task["id"]})
    for claim in _live_claims(state):
        if claim["session_id"] not in state["sessions"]:
            issues.append({"kind": "missing_claim_owner", "id": claim["id"], "action": "Retain the claim until explicit reconciliation."})
    memories = list(state["memories"].values())
    for memory in memories:
        if _stale(memory):
            issues.append({"kind": "stale_memory", "id": memory["id"]})
        if memory.get("superseded_by") and memory["superseded_by"] not in state["memories"]:
            issues.append({"kind": "missing_supersession", "id": memory["id"]})
        for source in memory.get("sources", []):
            source_path = source.get("path") if isinstance(source, dict) else source
            if not isinstance(source_path, str) or re.match(r"^[a-zA-Z][\w+.-]*://", source_path):
                continue
            source_path = re.sub(r":\d+(?::\d+)?$", "", source_path)
            # Prose citations are not presumed to be local file paths.
            if " " in source_path and not source_path.startswith("/"):
                continue
            if not (source_path.startswith(("/", "./", "../")) or "/" in source_path or Path(source_path).suffix):
                continue
            candidate = Path(source_path).expanduser()
            if not candidate.is_absolute():
                candidate = Path(workspace["path"]) / candidate
            if not candidate.exists():
                issues.append({"kind": "missing_source", "id": memory["id"], "source": source,
                               "resolved_path": str(candidate.resolve()), "action": "Verify or update the source reference explicitly."})
    for index, memory in enumerate(memories):
        for other in memories[index + 1:]:
            if memory.get("scope") != other.get("scope"):
                continue
            if _tokens(memory.get("title", "")) == _tokens(other.get("title", "")):
                issues.append({"kind": "duplicate_candidate" if memory.get("content") == other.get("content") else "possible_contradiction",
                               "ids": [memory["id"], other["id"]], "action": "Review the sources; lexical similarity does not establish semantic equivalence."})
    return issues


def _consolidate(state: dict, workspace: dict, data: dict) -> dict:
    sessions = [session for session in state["sessions"].values() if session["workspace_id"] == workspace["id"]
                or session["workspace_id"] not in state["workspaces"]]
    contributions, unknown, pending = [], [], []
    for session in sessions:
        task = state["tasks"].get(session["task_id"], {})
        resolved_checkpoints, resolved_sessions = _resolutions(task)
        checkpoint = state["checkpoints"].get(session["checkpoint_ids"][-1]) if session.get("checkpoint_ids") else None
        action_resolved_by = resolved_checkpoints.get(checkpoint["id"]) if checkpoint else None
        participant_resolved_by = resolved_sessions.get(session["id"])
        contribution = {"session_id": session["id"], "task_id": session["task_id"], "workspace_id": session["workspace_id"],
                        "status": session["status"], "presence": _presence(session),
                        "checkpoint_id": checkpoint["id"] if checkpoint else None,
                        "summary": checkpoint["summary"] if checkpoint else "No checkpoint recorded.",
                        "evidence": checkpoint["evidence"] if checkpoint else [],
                        "next_action": checkpoint["next_action"] if checkpoint else "Reconcile this participant's work.",
                        "next_action_resolved_by": action_resolved_by,
                        "participant_resolved_by": participant_resolved_by,
                        "updated_at": session["updated_at"]}
        (contributions if session["workspace_id"] == workspace["id"] else unknown).append(contribution)
        if ((not checkpoint and not participant_resolved_by) or
                (checkpoint and checkpoint.get("next_action") and not action_resolved_by) or
                session["status"] in {"active", "blocked"} or
                (session["status"] == "released" and not participant_resolved_by)):
            pending.append({"session_id": session["id"], "task_id": session["task_id"], "next_action": contribution["next_action"],
                            "status": session["status"]})
    relevant_tasks = {session["task_id"] for session in sessions}
    values = {"workspace": workspace, "claims": [_claim_view(state, claim) for claim in _live_claims(state)],
              "contributions": contributions, "unknown_workspace_contributions": unknown, "pending": pending,
              "task_events": [{"task_id": task_id, **event} for task_id in sorted(relevant_tasks)
                              for event in state["tasks"].get(task_id, {}).get("events", [])],
              "scope": "All project claims; latest contribution per current-workspace participant; all unknown-workspace contributions.",
              "diagnostics": {"truncated": False, "delivery_is_acceptance": False,
                              "history": "Use task.show, hydrate, changes, or include_history:true for older checkpoints."}}
    if data.get("include_history"):
        included_ids = {session["id"] for session in sessions}
        values["history"] = sorted((checkpoint for checkpoint in state["checkpoints"].values() if checkpoint["session_id"] in included_ids),
                                   key=lambda checkpoint: (checkpoint["revision"], checkpoint["id"]))
    return _result(state, **values)


_READS = {"resolve", "task.list", "task.show", "changes", "recall", "hydrate", "maintain", "consolidate"}
_WRITES = {"init", "project.bind", "project.move", "task.start", "task.join", "task.claim", "task.release",
           "task.checkpoint", "task.event", "remember", "memory.update"}


def execute(operation: str, data: dict, home: Path | None = None) -> dict:
    """Execute a JSON operation, returning success or raising a structured error."""
    if not isinstance(data, dict):
        _fail("invalid_input", "Operation data must be a JSON object.")
    if operation not in _READS | _WRITES:
        _fail("unknown_operation", "Unknown Harness operation.", operation=operation)
    home = Path(home).expanduser().resolve() if home is not None else home_path()
    # Validate JSON before taking a lock, and isolate caller-owned containers.
    try:
        data = json.loads(json.dumps(data, ensure_ascii=False, allow_nan=False))
    except (ValueError, TypeError) as exc:
        raise HarnessError("invalid_input", "Operation data must be finite JSON values.") from exc
    if operation in _WRITES:
        # Check the proposed root before creating even a lock file.
        path = _project_path(data.get("project"))
        _outside(home, _probe(path))
        if operation != "init" or "request_id" in data:
            _text(data, "request_id")
        with locked(home):
            if operation == "init":
                return _initialize(home, data)
            if operation in {"project.bind", "project.move"}:
                return _binding(home, operation, data)
            state, workspace = resolve_state(home, data.get("project"), data.get("project_id", ""), data.get("host", ""), data.get("host_project_id", ""))
            replay = _replay(state, operation, data)
            if replay:
                return replay
            if operation != "memory.update":
                _expected(state, data)
            _guard_overlap(_scan(home), workspace, state["project"]["id"])
            _enroll(state, workspace, data)
            if operation in {"remember", "memory.update"}:
                values, details = _memory_mutation(state, operation, data)
            else:
                values, details = _task_mutation(state, workspace, operation, data)
                for key in ("task_id", "session_id", "checkpoint_id"):
                    if key in details:
                        values.setdefault(key, details[key])
            return _commit(home, state, operation, data, values, details)
    state, workspace = resolve_state(home, data.get("project"), data.get("project_id", ""), data.get("host", ""), data.get("host_project_id", ""))
    if operation == "resolve":
        return _result(state, project=state["project"], workspace=workspace, schema_version=SCHEMA_VERSION, defaults_version=state["defaults_version"])
    if operation == "task.list":
        scope = _text(data, "scope", False, "workspace")
        if scope not in {"workspace", "current", "all"}:
            _fail("invalid_input", "Task list scope must be workspace, current, or all.")
        tasks = [_task_view(state, task, workspace["id"]) for task in state["tasks"].values()]
        if scope != "all":
            tasks = [task for task in tasks if task["current_workspace"]]
        return _result(state, tasks=tasks, workspace=workspace)
    if operation == "task.show":
        task = state["tasks"].get(_text(data, "task_id"))
        if task is None:
            _fail("unknown_task", "Task not found.")
        return _result(state, task=_task_view(state, task, workspace["id"]), checkpoints=[checkpoint for checkpoint in state["checkpoints"].values() if checkpoint["task_id"] == task["id"]])
    if operation == "changes":
        return _changes(state, data)
    if operation == "recall":
        return _recall(state, data)
    if operation == "hydrate":
        return _hydrate(state, data)
    if operation == "maintain":
        issues = _integrity(state, workspace)
        return _result(state, issues=issues, changed=False, claims=[_claim_view(state, claim) for claim in _live_claims(state)],
                       diagnostics={"semantic_deduplication": False, "automatic_release": False})
    return _consolidate(state, workspace, data)
