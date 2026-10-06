#!/usr/bin/env python3
"""Harness: project binding and atomic updates to external Markdown context."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

VERSION = "1.1.0"
FORMAT = "harness-project-v1"
LOCK_TIMEOUT = 10.0


class Error(RuntimeError):
    def __init__(self, code, message, **details):
        super().__init__(message)
        self.code, self.message, self.details = code, message, details


def fail(code, message, **details):
    raise Error(code, message, **details)


def contains(parent, child):
    return parent == child or parent in child.parents


def digest(content):
    return hashlib.sha256(content).hexdigest()


def absolute(value):
    return Path(os.path.abspath(Path(value).expanduser()))


def storage_root(value):
    # Explicit roots may use host aliases such as /var -> /private/var on macOS.
    # Descendant paths still reject symlinks before each operation.
    return Path(value).expanduser().resolve()


def git_container(path):
    ancestor = path if path.exists() else next(p for p in path.parents if p.exists())
    return git(ancestor, "rev-parse", "--show-toplevel")


def safe_path(path):
    for part in (path, *path.parents):
        if part.is_symlink():
            fail("unsafe_path", "Storage paths must not contain symbolic links.", path=str(part))
    return path


def sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def make_directory(path):
    safe_path(path)
    if not path.is_dir():
        make_directory(path.parent)
        path.mkdir(exist_ok=True)
        sync_directory(path.parent)


def atomic_write(path, content):
    safe_path(path)
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
             "Replacement completed; inspect state before retrying." if replaced else
             "Replacement failed; previous contents are unchanged.", path=str(path), reason=str(exc))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def locked(directory):
    """Cooperative file transaction, not an agent reservation or lease."""
    import fcntl
    make_directory(directory)
    path = safe_path(directory / ".harness.lock")
    with path.open("a+b") as stream:
        deadline = time.monotonic() + LOCK_TIMEOUT
        while True:
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    fail("lock_busy", "Another file transaction is running; retry later.")
                time.sleep(0.02)
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail("invalid_state", "Duplicate JSON key.", key=key)
        result[key] = value
    return result


def read_json(path):
    safe_path(path)
    try:
        return json.loads(path.read_bytes(), object_pairs_hook=unique_object)
    except FileNotFoundError:
        fail("not_initialized", "Project environment is not initialized.", path=str(path))
    except (ValueError, UnicodeError):
        fail("invalid_state", "State is not valid JSON.", path=str(path))


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def git(path, *arguments):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["LC_ALL"] = "C"
    try:
        result = subprocess.run(["git", "-C", str(path), *arguments], env=env,
                                capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        fail("git_unavailable", "Cannot determine project identity.", reason=str(exc))
    if result.returncode:
        if "not a git repository" in result.stderr:
            return ""
        fail("git_error", "Cannot determine project identity.", reason=result.stderr.strip())
    return result.stdout.strip()


def probe(value):
    if not isinstance(value, (str, Path)) or not str(value).strip():
        fail("invalid_input", "Provide an existing project directory.")
    selected = Path(value).expanduser().resolve()
    if not selected.is_dir():
        fail("project_missing", "Project directory does not exist.", path=str(selected))
    top = git(selected, "rev-parse", "--show-toplevel")
    if not top:
        return {"kind": "directory", "identity": str(selected), "root": str(selected)}, selected
    workspace = Path(top).resolve()
    common = (workspace / git(workspace, "rev-parse", "--git-common-dir")).resolve()
    first = git(workspace, "worktree", "list", "--porcelain", "-z").split("\0", 1)[0]
    if not first.startswith("worktree "):
        fail("git_error", "Cannot identify the primary checkout.")
    root = Path(first[len("worktree "):]).resolve()
    return {"kind": "git", "identity": str(common), "root": str(root)}, workspace


def binding_path(home, project):
    key = digest((project["kind"] + "\0" + project["identity"]).encode())
    return safe_path(home / "bindings" / (key + ".json"))


def validate_project(project):
    if (not isinstance(project, dict) or set(project) != {"kind", "identity", "root"}
            or project["kind"] not in {"git", "directory"}
            or not all(isinstance(project[k], str) and Path(project[k]).is_absolute()
                       and str(absolute(project[k])) == project[k] for k in ("identity", "root"))):
        fail("invalid_state", "Invalid project identity.")


def load_environment(folder):
    state = read_json(folder / "environment.json")
    if not isinstance(state, dict) or set(state) != {"format", "project"} or state["format"] != FORMAT:
        fail("invalid_state", "Environment is not the current Harness format.")
    validate_project(state["project"])
    root = Path(state["project"]["root"])
    if contains(root, folder) or contains(folder, root):
        fail("unsafe_path", "Environment and primary project must be outside one another.")
    return state


def read_binding(home, project):
    path = binding_path(home, project)
    value = read_json(path)
    if (not isinstance(value, dict) or set(value) != {"format", "project", "environment"}
            or value["format"] != FORMAT or not isinstance(value["environment"], str)
            or not Path(value["environment"]).is_absolute()):
        fail("invalid_state", "Invalid project binding.", path=str(path))
    validate_project(value["project"])
    if value["project"] != project:
        fail("identity_changed", "Project binding differs from the current project; preserve state before rebinding.")
    folder = safe_path(absolute(value["environment"]))
    if load_environment(folder)["project"] != project:
        fail("identity_changed", "Environment belongs to a different project.")
    return folder


def select(home, data):
    if bool(data.get("project")) == bool(data.get("environment")):
        fail("invalid_input", "Select exactly one project or environment path.")
    if data.get("environment"):
        folder = safe_path(storage_root(data["environment"]))
        return folder, load_environment(folder)["project"], None
    project, workspace = probe(data["project"])
    candidates = [project]
    if project["kind"] == "directory":
        candidates += [{"kind": "directory", "identity": str(p), "root": str(p)} for p in workspace.parents]
    for candidate in candidates:
        if binding_path(home, candidate).exists():
            return read_binding(home, candidate), candidate, workspace
    fail("not_initialized", "No environment is bound to this project.", project=str(workspace))


def location(folder, project, workspace):
    return {"environment": str(folder), "project": project,
            "workspace": str(workspace) if workspace else None,
            "knowledge": str(folder / "knowledge"), "work": str(folder / "work"),
            "worktrees": str(folder / "worktrees")}


def initialize(home, data):
    project, workspace = probe(data.get("project"))
    root = Path(project["root"])
    if contains(root, home) or contains(home, root):
        fail("unsafe_path", "Harness home and primary project must be outside one another.")
    try:
        folder, bound, current = select(home, {"project": data["project"]})
    except Error as exc:
        if exc.code != "not_initialized":
            raise
    else:
        if data.get("environment") and storage_root(data["environment"]) != folder:
            fail("already_bound", "Project already has an environment; contents were not moved.", environment=str(folder))
        return {**location(folder, bound, current), "changed": False}
    slug = re.sub(r"[^a-z0-9]+", "-", root.name.lower()).strip("-") or "project"
    suffix = digest((project["kind"] + "\0" + project["identity"]).encode())[:10]
    folder = safe_path(storage_root(data["environment"])) if data.get("environment") else home / "environments" / f"{slug}-{suffix}"
    if contains(root, folder) or contains(folder, root) or folder == home or contains(folder, home):
        fail("unsafe_path", "Use a dedicated environment outside the primary project and Harness home root.")
    if git_container(home) or git_container(folder):
        fail("unsafe_path", "Environment storage must not be inside a Git checkout.")
    if contains(home / "bindings", folder) or any((p / "environment.json").exists() for p in folder.parents):
        fail("unsafe_path", "Use a dedicated environment outside bindings and other environments.")
    with locked(home):
        if binding_path(home, project).exists():
            existing = read_binding(home, project)
            if existing != folder:
                fail("already_bound", "Project already has an environment.", environment=str(existing))
            return {**location(existing, project, workspace), "changed": False}
        if folder.exists():
            if load_environment(folder)["project"] != project:
                fail("identity_changed", "Environment belongs to a different project.")
        else:
            make_directory(folder.parent)
            temporary = Path(tempfile.mkdtemp(prefix=".harness-init-", dir=folder.parent))
            try:
                atomic_write(temporary / "environment.json", encoded({"format": FORMAT, "project": project}))
                atomic_write(temporary / "README.md", (
                    f"# {root.name}\n\nLocal project: `{root}`\n\n"
                    "Consult this map when project context is unknown; follow only relevant links.\n"
                    "Add descriptive links as useful subjects or ongoing work appear.\n\n## Map\n\n"
                    "- `knowledge/`: durable internal knowledge by subject.\n"
                    "- `work/`: plans and continuation context, only while needed.\n"
                    "- `worktrees/`: Git checkouts; exclude these from knowledge searches.\n\n"
                    "## Project-specific guidance\n\n"
                    "Keep one canonical source per decision; link to maintained sources instead of copying them.\n"
                ).encode())
                os.rename(temporary, folder)
                sync_directory(folder.parent)
            finally:
                if temporary.exists():
                    shutil.rmtree(temporary)
        binding = binding_path(home, project)
        make_directory(binding.parent)
        atomic_write(binding, encoded({"format": FORMAT, "project": project, "environment": str(folder)}))
    return {**location(folder, project, workspace), "changed": True}


def markdown_path(folder, name):
    if not isinstance(name, str) or not name:
        fail("unsafe_path", "Provide a relative Markdown path.")
    parts = name.split("/")
    if (name.startswith("/") or "\\" in name or any(p in {"", ".", ".."} or p.startswith(".") for p in parts)
            or not name.endswith(".md") or (name != "README.md" and (len(parts) < 2 or parts[0] not in {"knowledge", "work"}))):
        fail("unsafe_path", "Use README.md or a Markdown file under knowledge/ or work/.")
    return safe_path(folder / name)


def observe(path):
    safe_path(path)
    try:
        content = path.read_bytes()
    except FileNotFoundError:
        return {"sha256": "missing", "content": None}
    try:
        text = content.decode("utf-8")
    except UnicodeError:
        fail("invalid_document", "Document must be UTF-8.", path=str(path))
    return {"sha256": digest(content), "content": text}


def expected(data):
    value = data.get("expect")
    if value != "missing" and (not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)):
        fail("invalid_input", "Expect must be the observed SHA-256 or 'missing'.")
    return value


def document(operation, folder, data):
    path = markdown_path(folder, data.get("file"))
    observed = observe(path)
    if operation == "read":
        return {"file": str(path), **observed}
    token = expected(data)
    if operation == "write":
        source = data.get("input")
        if not source:
            fail("invalid_input", "Provide a UTF-8 input file, or '-' for stdin.")
        content = sys.stdin.buffer.read() if source == "-" else Path(source).read_bytes()
        content.decode("utf-8")
        if digest(content) == observed["sha256"]:
            return {"file": str(path), "sha256": digest(content), "changed": False}
        if token != observed["sha256"]:
            fail("document_conflict", "Document changed; inspect it before retrying.", sha256=observed["sha256"])
        make_directory(path.parent)
        atomic_write(path, content)
        return {"file": str(path), "sha256": digest(content), "changed": True}
    if token == "missing":
        fail("invalid_input", "Delete requires the observed document hash.")
    if observed["sha256"] == "missing":
        return {"file": str(path), "changed": False}
    if token != observed["sha256"]:
        fail("document_conflict", "Document changed; inspect it before deleting.", sha256=observed["sha256"])
    path.unlink()
    sync_directory(path.parent)
    return {"file": str(path), "changed": True}


def work_path(folder, name):
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        fail("invalid_input", "Use a readable lowercase work name with hyphens.")
    return safe_path(folder / "work" / name)


def inspect_work(path):
    safe_path(path)
    if not path.exists():
        return {"path": str(path), "sha256": "missing", "files": []}
    if not path.is_dir():
        fail("unsafe_path", "Work must be a directory.")
    records = []
    for item in sorted(path.rglob("*")):
        safe_path(item)
        relative = item.relative_to(path).as_posix()
        if item.is_dir():
            records.append([relative + "/", "directory"])
        elif item.is_file():
            records.append([relative, digest(item.read_bytes())])
        else:
            fail("unsafe_path", "Work material contains a special file.", path=str(item))
    return {"path": str(path), "sha256": digest(encoded(records)), "files": [p for p, _ in records]}


def close_work(folder, data):
    path = work_path(folder, data.get("work"))
    token = expected(data)
    retiring = safe_path(path.parent / (".closing-" + path.name))
    if retiring.exists():
        if path.exists():
            fail("close_pending", "Earlier cleanup is incomplete and the work name was reused; preserve both directories.")
        inspect_work(retiring)
        shutil.rmtree(retiring)
        sync_directory(path.parent)
        return {"path": str(path), "changed": True}
    observed = inspect_work(path)
    if observed["sha256"] == "missing":
        return {"path": str(path), "changed": False}
    if token != observed["sha256"]:
        fail("document_conflict", "Work material changed; inspect it before closing.", sha256=observed["sha256"])
    os.rename(path, retiring)
    sync_directory(path.parent)
    shutil.rmtree(retiring)
    sync_directory(path.parent)
    return {"path": str(path), "changed": True}


def execute(operation, data, home=None):
    if operation not in {"init", "resolve", "read", "write", "delete", "inspect-work", "close-work"}:
        fail("invalid_operation", "Unknown operation.")
    if not isinstance(data, dict):
        fail("invalid_input", "Arguments must be a dictionary.")
    try:
        home = safe_path(storage_root(home or os.environ.get("HARNESS_HOME", "~/.harness")))
        if operation == "init":
            return initialize(home, data)
        folder, project, workspace = select(home, data)
        if operation == "resolve":
            return location(folder, project, workspace)
        if operation == "read":
            return document(operation, folder, data)
        if operation == "inspect-work":
            return inspect_work(work_path(folder, data.get("work")))
        with locked(folder):
            if operation == "close-work":
                return close_work(folder, data)
            return document(operation, folder, data)
    except Error:
        raise
    except (OSError, ValueError, TypeError) as exc:
        fail("io_error", "Harness could not complete the operation; inspect state before retrying.", reason=str(exc))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=VERSION)
    parser.add_argument("--home", help="Binding storage (HARNESS_HOME or ~/.harness)")
    commands = parser.add_subparsers(dest="operation", required=True)
    for operation in ("init", "resolve", "read", "write", "delete", "inspect-work", "close-work"):
        command = commands.add_parser(operation)
        if operation == "init":
            command.add_argument("--project", required=True)
            command.add_argument("--environment", help="Dedicated external directory; default is under Harness home")
        else:
            selector = command.add_mutually_exclusive_group(required=True)
            selector.add_argument("--project")
            selector.add_argument("--environment")
        if operation in {"read", "write", "delete"}:
            command.add_argument("--file", required=True)
        if operation in {"write", "delete", "close-work"}:
            command.add_argument("--expect", required=True)
        if operation == "write":
            command.add_argument("--input", required=True)
        if operation in {"inspect-work", "close-work"}:
            command.add_argument("--work", required=True)
    args = vars(parser.parse_args(argv))
    operation, home = args.pop("operation"), args.pop("home")
    try:
        result = execute(operation, args, home)
    except Error as exc:
        print(json.dumps({"error": {"code": exc.code, "message": exc.message, "details": exc.details}}))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
