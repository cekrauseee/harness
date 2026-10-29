"""Run contracts, participant decisions, and shared finite execution budgets."""

from __future__ import annotations

import json
import secrets
import subprocess
import sys
import time
import uuid
from pathlib import Path

from . import workflows
from .access import digest, operator_only
from .config import validate_limits
from .context import environment_id, record_path, work_id
from .database import connect, transaction
from .errors import require
from .files import read_json, write_json

TERMINAL = ("accepted", "cancelled", "failed", "expired")
PACKAGE_ROOT = Path(__file__).resolve().parents[2]
ENTRY = PACKAGE_ROOT / "scripts" / "entry.py"
RUNTIME_ENTRY = PACKAGE_ROOT / "scripts" / "runtime.py"


def row_run(db, run_id):
    row = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    require(row is not None, "not_found", f"Execution not found: {run_id}.")
    return row


def directory(home, run_id):
    return home.path / ".runtime" / run_id


def launch_supervisor(home, run_id):
    runtime = directory(home, run_id)
    runtime.mkdir(parents=True, exist_ok=True)
    with (runtime / "supervisor.log").open("ab") as log:
        child = subprocess.Popen(
            [sys.executable, str(RUNTIME_ENTRY), "--root", str(home.path), "supervise", run_id],
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            start_new_session=True,
        )
    return child.pid


def create(
    home,
    environment,
    work,
    resource,
    prompt,
    profile_name=None,
    workflow_name=None,
    authorization=None,
    autonomous=False,
    actor=None,
):
    operator_only(actor)
    home.ensure()
    environment = environment_id(home, environment)
    if work:
        work = work_id(home, environment, work)
    require(
        0 < len(prompt.strip()) <= 32000,
        "invalid_prompt",
        "Provide an execution brief of 1–32000 characters.",
    )
    resources = read_json(home.path / "environments" / environment / "resources.json", {})
    config = home.config()
    if workflow_name:
        require(
            not autonomous and bool(authorization),
            "authorization_required",
            "A workflow requires explicit user authorization.",
        )
        require(bool(work), "missing_work", "A workflow belongs to a work record.")
        definition = workflows.get(home, environment, work, workflow_name)["definition"]
        workflows.validate(home, definition, environment)
        kind = definition["mode"]
        limits = definition["limits"]
    else:
        profile_name = profile_name or config["defaults"]["scout" if autonomous else "worker"]
        profile = home.profile(profile_name)
        require(
            bool(authorization) or (autonomous and profile.get("autonomous")),
            "authorization_required",
            "Use an explicitly authorized execution or an allowed autonomous profile.",
        )
        require(
            not autonomous or profile.get("autonomous"),
            "scope_denied",
            "This profile is not allowed for autonomous delegation.",
        )
        require(
            resource in resources
            and resources[resource]["kind"] in ("directory", "repository", "worktree"),
            "invalid_resource",
            "Select a registered local resource.",
        )
        kind = "task"
        limits = dict(config["limits"])
        if autonomous:
            limits.update(
                seconds=min(profile["seconds"], 300),
                attempt_seconds=min(profile["seconds"], 300),
                max_attempts=1,
                concurrency=1,
            )
        definition = {"profile": profile_name, "resource": resource}
    validate_limits(limits)
    run_id = "r-" + uuid.uuid4().hex[:16]
    tokens = {}
    now = time.time()
    with connect(home) as db, transaction(db):
        db.execute(
            "INSERT INTO runs(id,environment,work,kind,state,created,deadline,limits_json,definition_json,authorization) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                run_id,
                environment,
                work,
                kind,
                "active",
                now,
                now + limits["seconds"],
                json.dumps(limits),
                json.dumps(definition),
                authorization or "Configured economical delegation",
            ),
        )

        def participant(module, node, role, profile_key, context, resource_key, state):
            key = f"{run_id}.{module}.{node}"
            secret = secrets.token_urlsafe(32)
            tokens[key] = secret
            cwd = resources[resource_key]["location"]
            db.execute(
                "INSERT INTO participants(id,run_id,module,role,profile_json,context_json,cwd,state,token_hash,prompt) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    key,
                    run_id,
                    module,
                    role,
                    json.dumps(home.profile(profile_key)),
                    json.dumps(context),
                    cwd,
                    state,
                    digest(secret),
                    prompt.strip(),
                ),
            )

        if workflow_name:
            for module in definition["modules"]:
                for node_name, node in module["nodes"].items():
                    state = (
                        "ready"
                        if node["role"] == "coordinator" and not module.get("depends_on")
                        else "idle"
                    )
                    participant(
                        module["id"],
                        node_name,
                        node["role"],
                        node["profile"],
                        node.get("context", []),
                        module["resource"],
                        state,
                    )
            integration = definition["integration"]
            participant(
                "integration",
                "coordinator",
                "integration",
                integration["profile"],
                integration.get("context", []),
                integration["resource"],
                "idle",
            )
        else:
            participant("task", "worker", "worker", profile_name, [], resource, "ready")
    runtime = directory(home, run_id)
    runtime.mkdir(parents=True, mode=0o700)
    write_json(runtime / "credentials.json", tokens)
    launch_supervisor(home, run_id)
    return {"run": run_id, "state": "active", "deadline": now + limits["seconds"], "limits": limits}


def status(home, run_id, actor=None):
    if actor:
        actor.check_run(run_id)
    with connect(home) as db:
        run = dict(row_run(db, run_id))
        participants = [
            dict(p)
            for p in db.execute(
                "SELECT id,module,role,state,rounds,parent_id FROM participants WHERE run_id=? ORDER BY id",
                (run_id,),
            )
        ]
        attempts = [
            dict(a)
            for a in db.execute(
                "SELECT id,participant_id,state,created,started,ended,exit_code,reason,usage_json FROM attempts WHERE run_id=? ORDER BY created",
                (run_id,),
            )
        ]
    if actor and actor.participant["role"] != "integration":
        participants = [p for p in participants if p["module"] == actor.participant["module"]]
        ids = {p["id"] for p in participants}
        attempts = [a for a in attempts if a["participant_id"] in ids]
    for attempt in attempts:
        raw_usage = attempt.pop("usage_json")
        attempt["usage"] = json.loads(raw_usage) if raw_usage else None
    return {
        "run": run_id,
        "kind": run["kind"],
        "state": run["state"],
        "revision": run["revision"],
        "environment": run["environment"],
        "work": run["work"],
        "deadline": run["deadline"],
        "limits": json.loads(run["limits_json"]),
        "reason": run["reason"],
        "participants": participants,
        "attempts": attempts,
    }


def list_runs(home, environment=None, limit=20, actor=None):
    require(1 <= limit <= 100, "invalid_page", "List at most 100 executions.")
    if actor:
        return {"runs": [status(home, actor.run["id"], actor)]}
    if not (home.path / "state.sqlite").exists():
        return {"runs": []}
    with connect(home) as db:
        query = "SELECT id,environment,work,kind,state,created,deadline,reason FROM runs"
        rows = db.execute(
            query
            + (" WHERE environment=?" if environment else "")
            + " ORDER BY created DESC LIMIT ?",
            (environment, limit) if environment else (limit,),
        ).fetchall()
    return {"runs": [dict(row) for row in rows]}


def result(home, run_id, participant_id, actor=None, offset=0, limit=12000):
    require(
        offset >= 0 and 1 <= limit <= 40000,
        "invalid_page",
        "Read at most 40000 characters at a time.",
    )
    if actor:
        actor.check_run(run_id)
    with connect(home) as db:
        participant = db.execute(
            "SELECT * FROM participants WHERE id=? AND run_id=?", (participant_id, run_id)
        ).fetchone()
        require(participant is not None, "not_found", "Participant not found.")
        if actor:
            require(
                actor.participant["role"] == "integration"
                or participant["module"] == actor.participant["module"],
                "scope_denied",
                "This result is outside the assigned module.",
            )
        attempt = db.execute(
            "SELECT * FROM attempts WHERE participant_id=? ORDER BY created DESC LIMIT 1",
            (participant_id,),
        ).fetchone()
        require(attempt is not None, "not_found", "This participant has no attempt yet.")
    path = home.path / attempt["output_path"]
    from .providers import output

    text, _ = output(path.read_text(errors="replace") if path.exists() else "")
    return {
        "participant": participant_id,
        "attempt": attempt["id"],
        "state": attempt["state"],
        "exit_code": attempt["exit_code"],
        "content": text[offset : offset + limit],
        "next_offset": offset + limit if len(text) > offset + limit else None,
    }


def decide(
    home,
    run_id,
    event,
    reason,
    expected_revision,
    participant_id=None,
    target=None,
    context=None,
    actor=None,
):
    require(
        reason and len(reason) <= 16000,
        "invalid_decision",
        "A decision needs a concise reason or delegated brief.",
    )
    require(
        event in ("delegate", "request_changes", "accept", "fail"),
        "invalid_decision",
        "Unsupported graph decision.",
    )
    if actor:
        actor.check_run(run_id)
        require(
            participant_id in (None, actor.id),
            "scope_denied",
            "A participant cannot impersonate another role.",
        )
        participant_id = actor.id
    refs = context or []
    for ref in refs:
        path = record_path(home, ref, actor)
        require(path.is_file(), "not_found", f"Context record not found: {ref}.")
    with connect(home) as db, transaction(db):
        run = row_run(db, run_id)
        require(
            run["state"] in ("active", "waiting"),
            "invalid_state",
            "This execution cannot accept decisions in its current state.",
        )
        require(
            run["deadline"] > time.time(), "budget_exhausted", "The execution deadline has passed."
        )
        require(
            run["revision"] == expected_revision,
            "conflict",
            "The execution changed. Read its revision and reconsider the decision.",
        )
        participant = db.execute(
            "SELECT * FROM participants WHERE id=? AND run_id=?", (participant_id, run_id)
        ).fetchone()
        if run["kind"] == "task" and actor is None and event in ("accept", "fail"):
            if event == "accept":
                pending = db.execute(
                    "SELECT id FROM participants WHERE run_id=? AND state NOT IN ('complete','accepted')",
                    (run_id,),
                ).fetchone()
                require(
                    pending is None,
                    "invalid_state",
                    "Wait for a successful result before accepting.",
                )
            db.execute(
                "UPDATE runs SET state=?,reason=? WHERE id=?",
                ("accepted" if event == "accept" else "failed", reason, run_id),
            )
        else:
            require(
                participant is not None and participant["role"] in ("coordinator", "integration"),
                "scope_denied",
                "Only the assigned coordinator can decide graph transitions.",
            )
            require(
                participant["state"] in ("running", "waiting", "ready"),
                "invalid_state",
                "The coordinator is not ready to decide.",
            )
            if event == "fail":
                db.execute("UPDATE runs SET state='failed',reason=? WHERE id=?", (reason, run_id))
            elif event == "accept":
                if participant["role"] == "integration":
                    remaining = db.execute(
                        "SELECT id FROM participants WHERE run_id=? AND role='coordinator' AND state!='accepted'",
                        (run_id,),
                    ).fetchone()
                    require(
                        remaining is None,
                        "invalid_state",
                        "Every module needs acceptance before integration can be accepted.",
                    )
                    helpers = db.execute(
                        "SELECT id FROM participants WHERE run_id=? AND role='helper' AND state!='complete'",
                        (run_id,),
                    ).fetchone()
                    require(
                        helpers is None,
                        "invalid_state",
                        "Every assigned helper needs a successful result before final acceptance.",
                    )
                    db.execute(
                        "UPDATE runs SET state='accepted',reason=? WHERE id=?", (reason, run_id)
                    )
                else:
                    unfinished = db.execute(
                        "SELECT id FROM participants WHERE run_id=? AND module=? AND role IN ('worker','helper') AND state!='complete'",
                        (run_id, participant["module"]),
                    ).fetchone()
                    require(
                        unfinished is None,
                        "invalid_state",
                        "Every assigned worker needs a successful result before module acceptance.",
                    )
                if participant["state"] == "running":
                    db.execute(
                        "UPDATE participants SET next_state='accepted' WHERE id=?",
                        (participant_id,),
                    )
                else:
                    db.execute(
                        "UPDATE participants SET state='accepted' WHERE id=?", (participant_id,)
                    )
            elif event == "request_changes" and participant["role"] == "integration":
                coordinator = db.execute(
                    "SELECT * FROM participants WHERE id=? AND run_id=? AND role='coordinator'",
                    (target, run_id),
                ).fetchone()
                require(
                    coordinator is not None,
                    "scope_denied",
                    "Address integration corrections to a configured module coordinator.",
                )
                require(
                    coordinator["state"] == "accepted",
                    "invalid_state",
                    "Request integration corrections from an accepted module.",
                )
                allowed = json.loads(coordinator["context_json"])
                allowed.extend(ref for ref in refs if ref not in allowed)
                require(
                    len(allowed) <= 24,
                    "invalid_context",
                    "A participant can receive at most 24 explicit context records.",
                )
                db.execute(
                    "UPDATE participants SET state='ready',context_json=? WHERE id=?",
                    (json.dumps(allowed), target),
                )
                column = "next_state" if participant["state"] == "running" else "state"
                db.execute(
                    f"UPDATE participants SET {column}='blocked' WHERE id=?", (participant_id,)
                )
                db.execute("UPDATE runs SET state='active' WHERE id=?", (run_id,))
            else:
                require(
                    participant["role"] == "coordinator",
                    "scope_denied",
                    "Delegate within a module graph.",
                )
                worker = db.execute(
                    "SELECT * FROM participants WHERE id=? AND run_id=? AND module=? AND role='worker'",
                    (target, run_id, participant["module"]),
                ).fetchone()
                require(
                    worker is not None, "scope_denied", "Choose a configured worker in this module."
                )
                require(
                    worker["state"] in ("idle", "complete", "failed", "interrupted"),
                    "invalid_state",
                    "The worker is already scheduled or running.",
                )
                limits = json.loads(run["limits_json"])
                require(
                    worker["rounds"] < limits["max_rounds"],
                    "budget_exhausted",
                    "This worker has reached its configured round limit.",
                )
                if event == "request_changes":
                    require(
                        worker["rounds"] > 0,
                        "invalid_state",
                        "Request changes after the worker's first result.",
                    )
                allowed = json.loads(worker["context_json"])
                allowed.extend(ref for ref in refs if ref not in allowed)
                require(
                    len(allowed) <= 24,
                    "invalid_context",
                    "A participant can receive at most 24 explicit context records.",
                )
                db.execute(
                    "UPDATE participants SET state='ready',prompt=?,rounds=rounds+1,context_json=? WHERE id=?",
                    (reason, json.dumps(allowed), target),
                )
                column = "next_state" if participant["state"] == "running" else "state"
                db.execute(
                    f"UPDATE participants SET {column}='waiting' WHERE id=?", (participant_id,)
                )
                db.execute("UPDATE runs SET state='active' WHERE id=?", (run_id,))
        db.execute("UPDATE runs SET revision=revision+1 WHERE id=?", (run_id,))
        db.execute(
            "INSERT INTO decisions(run_id,participant_id,event,target,reason,created,revision) VALUES(?,?,?,?,?,?,?)",
            (run_id, participant_id, event, target, reason, time.time(), expected_revision + 1),
        )
    return {"run": run_id, "event": event, "revision": expected_revision + 1}


def stop(home, run_id, reason, actor=None):
    operator_only(actor)
    with connect(home) as db, transaction(db):
        run = row_run(db, run_id)
        state = run["state"] if run["state"] in TERMINAL else "cancelled"
        if run["state"] not in TERMINAL:
            db.execute(
                "UPDATE runs SET state='cancelled',reason=?,revision=revision+1 WHERE id=?",
                (reason or "Stopped by the user.", run_id),
            )
    from .processes import stop_attempts

    stop_attempts(home, run_id, "cancelled")
    return {"run": run_id, "state": state}


def resume(home, run_id, reason, actor=None):
    operator_only(actor)
    require(bool(reason), "authorization_required", "Explain the explicitly requested resumption.")
    from .processes import process_identity

    with connect(home) as db, transaction(db):
        run = row_run(db, run_id)
        require(
            run["state"] in ("waiting", "interrupted", "failed", "cancelled"),
            "invalid_state",
            "This execution cannot be resumed.",
        )
        supervisor_alive = bool(
            run["supervisor_pid"]
            and process_identity(run["supervisor_pid"]) == run["supervisor_identity"]
        )
        require(
            not supervisor_alive or run["state"] == "waiting",
            "in_use",
            "The previous supervisor is still exiting. Retry after it stops.",
        )
        require(
            run["deadline"] > time.time(),
            "budget_exhausted",
            "The original execution deadline has passed.",
        )
        count = db.execute("SELECT count(*) FROM attempts WHERE run_id=?", (run_id,)).fetchone()[0]
        require(
            count < json.loads(run["limits_json"])["max_attempts"],
            "budget_exhausted",
            "The shared attempt budget is exhausted.",
        )
        uncertain = db.execute(
            "SELECT id FROM attempts WHERE run_id=? AND state IN ('reserved','running','ambiguous')",
            (run_id,),
        ).fetchone()
        require(
            uncertain is None,
            "recovery_required",
            "Inspect and recover unresolved attempts before resuming.",
        )
        if run["kind"] == "task":
            db.execute(
                "UPDATE participants SET state='ready',next_state=NULL WHERE run_id=? AND parent_id IS NULL",
                (run_id,),
            )
        else:
            db.execute(
                "UPDATE participants SET state='idle',next_state=NULL WHERE run_id=? AND role='coordinator' AND state IN ('waiting','failed','interrupted')",
                (run_id,),
            )
            db.execute(
                "UPDATE participants SET state='blocked',next_state=NULL WHERE run_id=? AND role='integration' AND state IN ('waiting','failed','interrupted')",
                (run_id,),
            )
        db.execute(
            "UPDATE runs SET state='active',reason=?,revision=revision+1 WHERE id=?",
            (reason, run_id),
        )
    if not supervisor_alive:
        launch_supervisor(home, run_id)
    return {"run": run_id, "state": "active", "budget": "original"}


def recover(home, run_id, confirm_stopped=False, actor=None):
    operator_only(actor)
    from .processes import process_identity, stop_attempts

    with connect(home) as db:
        run = row_run(db, run_id)
        require(
            not run["supervisor_pid"]
            or process_identity(run["supervisor_pid"]) != run["supervisor_identity"],
            "in_use",
            "The supervisor is still running.",
        )
    stop_attempts(home, run_id, "interrupted")
    with connect(home) as db, transaction(db):
        ambiguous = db.execute(
            "SELECT id FROM attempts WHERE run_id=? AND state IN ('reserved','ambiguous')",
            (run_id,),
        ).fetchall()
        require(
            not ambiguous or confirm_stopped,
            "ambiguous_launch",
            "An attempt may have launched before its process identity was recorded.",
            "Inspect the operating system, then use --confirm-stopped only after verifying it has stopped. Nothing will be relaunched automatically.",
        )
        db.execute(
            "UPDATE attempts SET state='interrupted',ended=?,reason='Recovered without replay' WHERE run_id=? AND state IN ('reserved','ambiguous','running')",
            (time.time(), run_id),
        )
        db.execute(
            "UPDATE participants SET state='interrupted',next_state=NULL WHERE run_id=? AND state IN ('running','ready')",
            (run_id,),
        )
        db.execute(
            "UPDATE runs SET state='interrupted',supervisor_pid=NULL,supervisor_identity=NULL,revision=revision+1 WHERE id=? AND state NOT IN ('accepted','cancelled','expired')",
            (run_id,),
        )
    return {"run": run_id, "recovered": True, "relaunched": False}


def spawn_helper(home, run_id, profile_name, prompt, actor):
    require(actor is not None, "invalid_identity", "A helper needs a managed parent participant.")
    actor.check_run(run_id)
    require(actor.participant["role"] != "helper", "scope_denied", "Helpers cannot delegate again.")
    profile = home.profile(profile_name)
    require(
        profile.get("autonomous"),
        "scope_denied",
        "Use a configured economical profile for a helper.",
    )
    profile["seconds"] = min(profile["seconds"], 300)
    require(0 < len(prompt.strip()) <= 16000, "invalid_prompt", "A helper needs a bounded brief.")
    key = f"{run_id}.helper.{uuid.uuid4().hex[:8]}"
    token = secrets.token_urlsafe(32)
    from .files import locked

    with locked(home.path, f"credentials:{run_id}"):
        credentials_path = directory(home, run_id) / "credentials.json"
        credentials = read_json(credentials_path)
        credentials[key] = token
        write_json(credentials_path, credentials)
        with connect(home) as db, transaction(db):
            run = row_run(db, run_id)
            require(
                run["state"] == "active" and run["deadline"] > time.time(),
                "invalid_state",
                "This execution cannot start a helper.",
            )
            parent = db.execute("SELECT state FROM participants WHERE id=?", (actor.id,)).fetchone()
            require(
                parent["state"] == "running",
                "invalid_state",
                "Only a running parent can delegate a helper.",
            )
            limits = json.loads(run["limits_json"])
            require(
                limits["concurrency"] >= 2,
                "budget_exhausted",
                "This execution has no parallel capacity for a helper.",
            )
            pending = db.execute(
                "SELECT id FROM participants WHERE parent_id=? AND state IN ('ready','running')",
                (actor.id,),
            ).fetchone()
            require(pending is None, "in_use", "This participant already has an active helper.")
            db.execute(
                "INSERT INTO participants(id,run_id,module,role,profile_json,context_json,cwd,state,token_hash,prompt,parent_id) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    key,
                    run_id,
                    actor.participant["module"],
                    "helper",
                    json.dumps(profile),
                    actor.participant["context_json"],
                    actor.participant["cwd"],
                    "ready",
                    digest(token),
                    prompt.strip(),
                    actor.id,
                ),
            )
            db.execute("UPDATE participants SET next_state='waiting' WHERE id=?", (actor.id,))
    return {"run": run_id, "participant": key, "budget": "shared"}


def retry_helper(home, run_id, participant_id, reason, actor=None):
    require(
        bool(reason.strip()) and len(reason) <= 16000,
        "invalid_reason",
        "Explain why retrying the helper can resolve its failure.",
    )
    if actor:
        actor.check_run(run_id)
    with connect(home) as db, transaction(db):
        run = row_run(db, run_id)
        require(
            run["state"] in ("active", "waiting"),
            "invalid_state",
            "Resume the execution explicitly before retrying a stopped helper.",
        )
        require(
            run["deadline"] > time.time(),
            "budget_exhausted",
            "The original execution deadline has passed.",
        )
        participant = db.execute(
            "SELECT * FROM participants WHERE id=? AND run_id=? AND role='helper'",
            (participant_id, run_id),
        ).fetchone()
        require(
            participant is not None, "not_found", "Select an existing helper in this execution."
        )
        require(
            actor is None or participant["parent_id"] == actor.id,
            "scope_denied",
            "Only the helper's parent or the operator can retry it.",
        )
        require(
            participant["state"] in ("failed", "interrupted"),
            "invalid_state",
            "Retry only a failed or interrupted helper.",
        )
        uncertain = db.execute(
            "SELECT id FROM attempts WHERE participant_id=? AND state IN ('reserved','running','ambiguous')",
            (participant_id,),
        ).fetchone()
        require(
            uncertain is None,
            "recovery_required",
            "Recover unresolved attempts before retrying this helper.",
        )
        count = db.execute("SELECT count(*) FROM attempts WHERE run_id=?", (run_id,)).fetchone()[0]
        require(
            count < json.loads(run["limits_json"])["max_attempts"],
            "budget_exhausted",
            "The shared attempt budget is exhausted.",
        )
        parent = db.execute(
            "SELECT * FROM participants WHERE id=?", (participant["parent_id"],)
        ).fetchone()
        require(
            parent is not None and parent["state"] != "accepted",
            "invalid_state",
            "The parent has already accepted its scope.",
        )
        require(
            actor is None or parent["state"] == "running",
            "invalid_state",
            "Only a running parent can request a retry.",
        )
        db.execute(
            "UPDATE participants SET state='ready',next_state=NULL WHERE id=?", (participant_id,)
        )
        column = "next_state" if parent["state"] == "running" else "state"
        db.execute(f"UPDATE participants SET {column}='waiting' WHERE id=?", (parent["id"],))
        db.execute("UPDATE runs SET state='active',revision=revision+1 WHERE id=?", (run_id,))
        db.execute(
            "INSERT INTO decisions(run_id,participant_id,event,target,reason,created,revision) VALUES(?,?,?,?,?,?,?)",
            (
                run_id,
                actor.id if actor else None,
                "retry",
                participant_id,
                reason,
                time.time(),
                run["revision"] + 1,
            ),
        )
    return {"run": run_id, "participant": participant_id, "state": "ready", "budget": "original"}
