"""Environment and work records, resource bindings, and selective Markdown I/O."""

from __future__ import annotations

import os
import time
from pathlib import Path

from .access import operator_only
from .database import connect
from .errors import HarnessError, require
from .files import identifier, inside, locked, put_document, read_json, revision, write_json


def environment_id(home, value=None, actor=None):
    value = value or (actor.run["environment"] if actor else os.environ.get("HARNESS_ENVIRONMENT"))
    require(
        bool(value), "missing_environment", "Select an environment explicitly with --environment."
    )
    identifier(value)
    if actor:
        require(
            value == actor.run["environment"],
            "scope_denied",
            "The environment is outside the assigned context.",
        )
    require(
        (home.path / "environments" / value / "environment.md").exists(),
        "not_found",
        f"Environment not found: {value}.",
    )
    return value


def work_id(home, environment, value=None, actor=None):
    value = value or (actor.run["work"] if actor else os.environ.get("HARNESS_WORK"))
    require(bool(value), "missing_work", "Select a work record with --work.")
    identifier(value)
    if actor:
        require(
            value == actor.run["work"], "scope_denied", "The work is outside the assigned context."
        )
    require(
        (home.path / "environments" / environment / "work" / value / "work.md").exists(),
        "not_found",
        f"Work not found: {value}.",
    )
    return value


def ensure_environment(home, name, title=None, actor=None):
    operator_only(actor)
    identifier(name)
    home.ensure()
    relative = f"environments/{name}/environment.md"
    with locked(home.path, "environment:" + name):
        created = not (home.path / relative).exists()
        if created:
            put_document(
                home.path,
                relative,
                f"# {title or name}\n\n## Purpose\n\nDescribe this environment's scope and shared context.\n",
                None,
            )
    return {"environment": name, "created": created, **read_record(home, relative)}


def create_work(home, env, name, title, purpose, actor=None):
    operator_only(actor)
    env = environment_id(home, env)
    identifier(name)
    require(bool(purpose.strip()), "invalid_work", "A work record needs a recognizable purpose.")
    return put_document(
        home.path,
        f"environments/{env}/work/{name}/work.md",
        f"# {title}\n\n## Purpose\n\n{purpose}\n",
        None,
    )


def list_context(home, kind, env=None, limit=20, offset=0, actor=None):
    require(
        1 <= limit <= 100 and offset >= 0,
        "invalid_page",
        "Use a limit from 1 to 100 and a nonnegative offset.",
    )
    if kind == "environment":
        paths = sorted((home.path / "environments").glob("*/environment.md"))
        if actor:
            paths = [p for p in paths if p.parent.name == actor.run["environment"]]
    else:
        env = environment_id(home, env, actor)
        paths = sorted((home.path / "environments" / env / "work").glob("*/work.md"))
        if actor:
            paths = [p for p in paths if p.parent.name == actor.run["work"]]
    items = [
        {"id": p.parent.name, "title": p.read_text().splitlines()[0][2:]}
        for p in paths[offset : offset + limit]
    ]
    return {"items": items, "next_offset": offset + limit if len(paths) > offset + limit else None}


def archive_context(home, kind, name, env=None, actor=None):
    operator_only(actor)
    identifier(name)
    if kind == "environment":
        env = environment_id(home, name)
        source = home.path / "environments" / name
        query, params = "environment=?", (env,)
    else:
        env = environment_id(home, env)
        work_id(home, env, name)
        source = home.path / "environments" / env / "work" / name
        query, params = "environment=? AND work=?", (env, name)
    with connect(home) as db:
        active = db.execute(
            f"SELECT id FROM runs WHERE {query} AND state IN ('active','waiting','interrupted')",
            params,
        ).fetchone()
        require(
            active is None,
            "in_use",
            "An execution still references this context.",
            "Finish or cancel that execution before archiving.",
        )
    destination = home.path / "archive" / kind / f"{env}-{name}-{time.time_ns()}"
    with locked(home.path, "archive:" + str(source)):
        destination.parent.mkdir(parents=True, exist_ok=True)
        source.rename(destination)
    return {"archived": str(destination.relative_to(home.path))}


def resources(
    home,
    env,
    operation="list",
    name=None,
    location=None,
    kind="directory",
    work=None,
    owned=False,
    actor=None,
):
    env = environment_id(home, env, actor)
    path = home.path / "environments" / env / "resources.json"
    if operation == "list":
        data = read_json(path, {})
        if actor:
            data = {
                key: value
                for key, value in data.items()
                if value["location"] == actor.participant["cwd"]
            }
        return {"resources": data}
    operator_only(actor)
    identifier(name)
    with locked(home.path, str(path)):
        data = read_json(path, {})
        if operation == "remove":
            require(name in data, "not_found", f"Resource not found: {name}.")
            del data[name]
        else:
            require(
                kind in ("directory", "repository", "worktree", "url", "branch", "pull-request"),
                "invalid_resource",
                "Unsupported resource kind.",
            )
            require(bool(location), "invalid_resource", "A resource needs a location.")
            if kind in ("directory", "repository", "worktree"):
                location = str(Path(location).expanduser().resolve())
                require(
                    Path(location).is_dir(), "not_found", "The resource directory does not exist."
                )
            if work:
                work_id(home, env, work)
            data[name] = {"kind": kind, "location": location, "owned": owned}
            if work:
                data[name]["work"] = work
        write_json(path, data)
    return {"resource": name, "operation": operation}


def record_path(home, relative, actor=None, write=False):
    path = inside(home.path, relative)
    require(
        path.suffix == ".md" and Path(relative).parts[0] in ("environments", "memory", "archive"),
        "invalid_path",
        "Document operations address Markdown context or memory records.",
    )
    if actor:
        actor.check_record(relative, write)
    return path


def read_record(home, relative, actor=None, offset=0, limit=12000):
    path = record_path(home, relative, actor)
    require(path.is_file(), "not_found", f"Record not found: {relative}.")
    require(
        offset >= 0 and 1 <= limit <= 40000,
        "invalid_page",
        "Read at most 40000 characters at a time.",
    )
    data = path.read_bytes()
    content = data.decode()
    return {
        "path": relative,
        "revision": revision(data),
        "content": content[offset : offset + limit],
        "next_offset": offset + limit if len(content) > offset + limit else None,
    }


def write_record(home, relative, content, expected=None, actor=None):
    home.ensure()
    record_path(home, relative, actor, write=True)
    return put_document(home.path, relative, content, expected)


def delete_record(home, relative, expected, actor=None):
    path = record_path(home, relative, actor, write=True)
    require(
        path.name not in ("environment.md", "work.md"),
        "invalid_operation",
        "Archive an environment or work through its module.",
    )
    with locked(home.path, relative):
        require(path.is_file(), "not_found", "The record does not exist.")
        require(
            revision(path.read_bytes()) == expected,
            "conflict",
            "The record changed before deletion.",
        )
        path.unlink()
    return {"deleted": relative}


def search_records(home, prefix, query="", actor=None, limit=20, offset=0):
    require(
        1 <= limit <= 100 and offset >= 0,
        "invalid_page",
        "Use a limit from 1 to 100 and a nonnegative offset.",
    )
    base = inside(home.path, prefix)
    require(
        Path(prefix).parts[0] in ("environments", "memory", "archive"),
        "invalid_path",
        "Search a context or memory scope.",
    )
    matches = []
    for path in sorted(base.rglob("*.md")):
        relative = str(path.relative_to(home.path))
        try:
            record_path(home, relative, actor)
        except HarnessError:
            continue
        text = path.read_text()
        if query.casefold() in text.casefold():
            lines = text.splitlines()
            excerpt = next(
                (line for line in lines[1:] if query and query.casefold() in line.casefold()), ""
            )
            matches.append(
                {"path": relative, "title": lines[0].removeprefix("# "), "excerpt": excerpt[:240]}
            )
    return {
        "items": matches[offset : offset + limit],
        "next_offset": offset + limit if len(matches) > offset + limit else None,
    }
