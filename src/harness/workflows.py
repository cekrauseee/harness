"""Readable workflow definitions and a deliberately small graph vocabulary."""

from __future__ import annotations

import copy

from .access import operator_only
from .config import validate_limits
from .context import environment_id, record_path, work_id
from .errors import require
from .files import identifier, locked, read_json, revision, write_json


def template(home, mode, module, resource, context):
    require(mode in ("develop", "review"), "invalid_workflow", "Choose develop or review.")
    identifier(module)
    config = home.config()
    return {
        "version": 1,
        "mode": mode,
        "limits": copy.deepcopy(config["limits"]),
        "integration": {
            "profile": config["defaults"]["coordinator"],
            "resource": resource,
            "context": context,
        },
        "modules": [
            {
                "id": module,
                "depends_on": [],
                "resource": resource,
                "entry": "coordinator",
                "nodes": {
                    "coordinator": {
                        "role": "coordinator",
                        "profile": config["defaults"]["coordinator"],
                        "context": context,
                    },
                    "worker": {
                        "role": "worker",
                        "profile": config["defaults"]["worker"],
                        "context": context,
                    },
                },
                "edges": [
                    {"from": "coordinator", "event": "delegate", "to": "worker"},
                    {"from": "coordinator", "event": "request_changes", "to": "worker"},
                    {"from": "worker", "event": "result", "to": "coordinator"},
                    {"from": "coordinator", "event": "accept", "to": "accepted"},
                ],
            }
        ],
    }


def validate(home, definition, environment):
    require(
        isinstance(definition, dict) and definition.get("version") == 1,
        "invalid_workflow",
        "A workflow needs version 1.",
    )
    require(
        definition.get("mode") in ("develop", "review"),
        "invalid_workflow",
        "Unsupported workflow mode.",
    )
    validate_limits(definition.get("limits", {}))
    modules = definition.get("modules", [])
    require(
        isinstance(modules, list) and 1 <= len(modules) <= 32,
        "invalid_workflow",
        "Define between 1 and 32 coherent modules.",
    )
    require(
        all(isinstance(module, dict) for module in modules),
        "invalid_workflow",
        "Each module must be an object.",
    )
    resources = read_json(home.path / "environments" / environment / "resources.json", {})
    module_ids = [identifier(m.get("id", "")) for m in modules]
    require(
        len(set(module_ids)) == len(module_ids) and "integration" not in module_ids,
        "invalid_workflow",
        "Module identifiers must be unique; integration is reserved.",
    )

    def validate_context(node):
        require(
            isinstance(node, dict), "invalid_workflow", "Nodes and integration must be objects."
        )
        home.profile(node.get("profile", ""))
        refs = node.get("context", [])
        require(
            isinstance(refs, list) and len(refs) <= 24,
            "invalid_workflow",
            "A node can reference at most 24 context records.",
        )
        for ref in refs:
            require(
                isinstance(ref, str) and not ref.endswith("/"),
                "invalid_workflow",
                "Assign explicit context files, not whole directories.",
            )
            path = record_path(home, ref)
            require(path.is_file(), "not_found", f"Context record not found: {ref}.")
            require(
                ref.startswith(f"environments/{environment}/") or ref.startswith("memory/"),
                "scope_denied",
                "Workflow context must belong to its environment or global memory.",
            )

    def validate_resource(resource):
        require(
            isinstance(resource, str)
            and resource in resources
            and resources[resource]["kind"] in ("directory", "repository", "worktree"),
            "invalid_workflow",
            f"A registered local resource is required: {resource}.",
        )

    for module in modules:
        validate_resource(module.get("resource"))
        deps = module.get("depends_on", [])
        require(
            isinstance(deps, list)
            and all(isinstance(d, str) and d in module_ids and d != module["id"] for d in deps),
            "invalid_workflow",
            "Module dependencies must reference other modules.",
        )
        nodes = module.get("nodes", {})
        require(
            isinstance(nodes, dict) and 2 <= len(nodes) <= 17,
            "invalid_workflow",
            "Each module needs one coordinator and 1–16 workers.",
        )
        for name, node in nodes.items():
            identifier(name)
            validate_context(node)
        coordinators = [name for name, node in nodes.items() if node.get("role") == "coordinator"]
        require(
            len(coordinators) == 1 and module.get("entry") == coordinators[0],
            "invalid_workflow",
            "The module entry must be its single coordinator.",
        )
        coordinator = coordinators[0]
        workers = [name for name, node in nodes.items() if node.get("role") == "worker"]
        require(
            len(workers) == len(nodes) - 1,
            "invalid_workflow",
            "Module roles are coordinator or worker.",
        )
        expected = {(coordinator, "accept", "accepted")}
        for worker in workers:
            expected.update(
                {
                    (coordinator, "delegate", worker),
                    (coordinator, "request_changes", worker),
                    (worker, "result", coordinator),
                }
            )
        edges = module.get("edges", [])
        require(
            isinstance(edges, list)
            and all(
                isinstance(e, dict)
                and all(isinstance(e.get(k), str) for k in ("from", "event", "to"))
                for e in edges
            ),
            "invalid_workflow",
            "Edges must be objects with string from, event, and to fields.",
        )
        actual = {(e.get("from"), e.get("event"), e.get("to")) for e in edges}
        require(
            actual == expected and len(edges) == len(expected),
            "invalid_workflow",
            "Edges must declare delegation, correction, result, and coordinator acceptance for every worker.",
        )

    visited, visiting = set(), set()
    by_id = {module["id"]: module for module in modules}

    def visit(key):
        require(key not in visiting, "invalid_workflow", "Module dependencies contain a cycle.")
        if key in visited:
            return
        visiting.add(key)
        for dep in by_id[key].get("depends_on", []):
            visit(dep)
        visiting.remove(key)
        visited.add(key)

    for key in module_ids:
        visit(key)
    integration = definition.get("integration", {})
    validate_context(integration)
    validate_resource(integration.get("resource"))
    return definition


def path_for(home, environment, work, name):
    identifier(name)
    return home.path / "environments" / environment / "work" / work / "workflows" / f"{name}.json"


def put(home, environment, work, name, definition, expected=None, actor=None):
    operator_only(actor)
    environment = environment_id(home, environment)
    work = work_id(home, environment, work)
    validate(home, definition, environment)
    path = path_for(home, environment, work, name)
    with locked(home.path, str(path)):
        current = revision(path.read_bytes()) if path.exists() else None
        require(current == expected, "conflict", "The workflow changed or already exists.")
        write_json(path, definition)
    return {"path": str(path.relative_to(home.path)), "revision": revision(path.read_bytes())}


def get(home, environment, work, name, actor=None):
    environment = environment_id(home, environment, actor)
    work = work_id(home, environment, work, actor)
    path = path_for(home, environment, work, name)
    require(path.is_file(), "not_found", f"Workflow not found: {name}.")
    if actor:
        require(
            actor.participant["role"] == "integration",
            "scope_denied",
            "Module participants receive their own graph context.",
        )
    return {"definition": read_json(path), "revision": revision(path.read_bytes())}
