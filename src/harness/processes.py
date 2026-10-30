"""Bounded local process ownership, scheduling, and a finite crash guard."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time
import uuid

from .database import connect, transaction
from .errors import HarnessError
from .files import locked, read_json
from .runs import RUNTIME_ENTRY, TERMINAL, directory, row_run

LOG_LIMIT = 4 * 1024 * 1024


def process_identity(pid):
    if not pid:
        return None
    try:
        value = subprocess.run(
            ["ps", "-p", str(pid), "-o", "lstart="], text=True, capture_output=True, timeout=3
        )
        return value.stdout.strip() or None
    except (OSError, subprocess.TimeoutExpired):
        return None


def signal_group(pid, sig):
    try:
        os.killpg(pid, sig)
    except ProcessLookupError:
        pass
    except PermissionError as exc:
        # Some platforms report EPERM after the last live member exits.
        groups = subprocess.run(
            ["ps", "-axo", "pgid=,stat="], capture_output=True, text=True, timeout=3
        )
        live = [line.split() for line in groups.stdout.splitlines() if len(line.split()) == 2]
        if groups.returncode or any(
            group == str(pid) and not state.startswith("Z") for group, state in live
        ):
            raise HarnessError(
                "process_stop_failed",
                f"Cannot stop owned process group {pid}.",
                "Inspect the process before recovering this execution.",
            ) from exc


def group_members(group):
    result = subprocess.run(
        ["ps", "-axo", "pid=,pgid=,stat="], text=True, capture_output=True, timeout=3
    )
    if result.returncode:
        raise HarnessError("process_inspection_failed", "Cannot inspect the owned process group.")
    members = []
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[1] == str(group) and not fields[2].startswith("Z"):
            members.append(int(fields[0]))
    return members


def owned_group_exists(attempt):
    """A departed leader can leave children in its recorded POSIX session."""
    members = group_members(attempt["pid"])
    if not members:
        return False
    leader = process_identity(attempt["pid"])
    if not attempt["identity"] or (leader is not None and leader != attempt["identity"]):
        raise HarnessError("ambiguous_process", "The recorded process identity no longer matches.")
    for member in members:
        try:
            if os.getsid(member) != attempt["pid"]:
                raise HarnessError(
                    "ambiguous_process", "A process group member is outside the recorded session."
                )
        except ProcessLookupError:
            continue
        except PermissionError as exc:
            raise HarnessError(
                "ambiguous_process", "Cannot verify the recorded process session."
            ) from exc
    return True


def stop_attempts(home, run_id, reason):
    with locked(home.path, "launch:" + run_id):
        _stop_attempts(home, run_id, reason)


def _stop_attempts(home, run_id, reason):
    with connect(home) as db:
        attempts = db.execute(
            "SELECT * FROM attempts WHERE run_id=? AND state IN ('running','reserved','ambiguous')",
            (run_id,),
        ).fetchall()
    live, errors = [], {}
    for attempt in attempts:
        if attempt["pid"]:
            try:
                if owned_group_exists(attempt):
                    signal_group(attempt["pid"], signal.SIGTERM)
                    live.append(attempt)
            except (HarnessError, OSError, subprocess.TimeoutExpired) as exc:
                errors[attempt["id"]] = exc
    if live:
        time.sleep(0.2)
        for attempt in live:
            try:
                if owned_group_exists(attempt):
                    signal_group(attempt["pid"], signal.SIGKILL)
                until = time.monotonic() + 2
                while owned_group_exists(attempt):
                    if time.monotonic() >= until:
                        raise HarnessError(
                            "process_stop_failed", "The owned process group has not stopped."
                        )
                    time.sleep(0.02)
            except (HarnessError, OSError, subprocess.TimeoutExpired) as exc:
                errors[attempt["id"]] = exc
    with connect(home) as db, transaction(db):
        for attempt in attempts:
            state = "ambiguous" if not attempt["pid"] or attempt["id"] in errors else "interrupted"
            db.execute(
                "UPDATE attempts SET state=?,ended=?,reason=? WHERE id=? AND state IN ('running','reserved','ambiguous')",
                (state, time.time(), str(errors.get(attempt["id"], reason)), attempt["id"]),
            )
    if errors:
        raise next(iter(errors.values()))


def launch(home, attempt, participant, argv, environment):
    """Serialize launch with stopping; a revoked reservation never becomes live."""
    with locked(home.path, "launch:" + attempt["run_id"]), connect(home) as db, transaction(db):
        run = row_run(db, attempt["run_id"])
        current = db.execute("SELECT state FROM attempts WHERE id=?", (attempt["id"],)).fetchone()
        if (
            run["state"] not in ("active", "waiting")
            or current["state"] != "reserved"
            or time.time() >= attempt["deadline"]
        ):
            db.execute(
                "UPDATE attempts SET state='interrupted',ended=?,reason='Launch revoked' WHERE id=? AND state='reserved'",
                (time.time(), attempt["id"]),
            )
            db.execute(
                "UPDATE participants SET state='interrupted',next_state=NULL WHERE id=? AND state='running'",
                (participant["id"],),
            )
            return None
        child = subprocess.Popen(
            argv,
            cwd=participant["cwd"],
            env=environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            db.execute(
                "UPDATE attempts SET state='running',pid=?,identity=?,started=? WHERE id=? AND state='reserved'",
                (child.pid, process_identity(child.pid), time.time(), attempt["id"]),
            )
        except BaseException:
            signal_group(child.pid, signal.SIGKILL)
            child.wait(timeout=5)
            raise
        return child


def deliver(home, attempt, stream, data):
    """Nonblocking chunks keep prompt delivery inside the execution deadline."""
    fd = stream.fileno()
    os.set_blocking(fd, False)
    offset = 0
    try:
        while offset < len(data):
            with locked(home.path, "launch:" + attempt["run_id"]), connect(home) as db:
                run = row_run(db, attempt["run_id"])
                current = db.execute(
                    "SELECT state FROM attempts WHERE id=?", (attempt["id"],)
                ).fetchone()
                if (
                    run["state"] not in ("active", "waiting")
                    or current["state"] != "running"
                    or time.time() >= attempt["deadline"]
                ):
                    return
                try:
                    offset += os.write(fd, data[offset : offset + 4096])
                except BlockingIOError:
                    pass
            if offset < len(data):
                time.sleep(0.01)
    except (BrokenPipeError, OSError):
        pass
    finally:
        stream.close()


def guard(home, run_id, supervisor_pid, identity):
    """This companion exits with the run and never launches or resumes models."""
    while True:
        with connect(home) as db:
            run = row_run(db, run_id)
        alive = process_identity(supervisor_pid) == identity
        if not alive or time.time() >= run["deadline"]:
            reason = "Supervisor lost" if not alive else "Execution deadline reached"
            state = "interrupted" if not alive else "expired"
            try:
                stop_attempts(home, run_id, reason)
            except (HarnessError, OSError, subprocess.TimeoutExpired) as exc:
                reason += "; cleanup requires inspection: " + str(exc)[:500]
                state = "interrupted"
            with connect(home) as db, transaction(db):
                db.execute(
                    "UPDATE participants SET state='interrupted',next_state=NULL WHERE run_id=? AND state IN ('running','ready')",
                    (run_id,),
                )
                db.execute(
                    "UPDATE runs SET state=?,reason=?,revision=revision+1 WHERE id=? AND state NOT IN ('accepted','cancelled','failed','expired')",
                    (
                        state,
                        reason,
                        run_id,
                    ),
                )
            return
        if run["state"] in TERMINAL:
            stop_attempts(home, run_id, run["state"])
            return
        time.sleep(0.5)


def advance(db, run):
    if run["kind"] == "task":
        return
    definition = json.loads(run["definition_json"])
    participants = db.execute("SELECT * FROM participants WHERE run_id=?", (run["id"],)).fetchall()
    accepted = {
        p["module"] for p in participants if p["role"] == "coordinator" and p["state"] == "accepted"
    }
    for module in definition["modules"]:
        if all(dep in accepted for dep in module.get("depends_on", [])):
            db.execute(
                "UPDATE participants SET state='ready' WHERE run_id=? AND module=? AND role='coordinator' AND state='idle'",
                (run["id"], module["id"]),
            )
    if len(accepted) == len(definition["modules"]):
        db.execute(
            "UPDATE participants SET state='ready' WHERE run_id=? AND role='integration' AND state IN ('idle','blocked')",
            (run["id"],),
        )


def reserve(home, run_id):
    with connect(home) as db, transaction(db):
        run = row_run(db, run_id)
        if run["state"] not in ("active", "waiting"):
            return None
        limits = json.loads(run["limits_json"])
        if time.time() >= run["deadline"]:
            db.execute(
                "UPDATE runs SET state='expired',reason='Execution deadline reached',revision=revision+1 WHERE id=?",
                (run_id,),
            )
            return None
        advance(db, run)
        running = db.execute(
            "SELECT count(*) FROM attempts WHERE run_id=? AND state IN ('reserved','running')",
            (run_id,),
        ).fetchone()[0]
        if running >= limits["concurrency"]:
            return None
        participant = db.execute(
            "SELECT * FROM participants WHERE run_id=? AND state='ready' ORDER BY CASE WHEN role='helper' THEN 0 ELSE 1 END,id LIMIT 1",
            (run_id,),
        ).fetchone()
        if participant is None:
            if running == 0:
                db.execute("UPDATE runs SET state='waiting' WHERE id=?", (run_id,))
            return None
        count = db.execute("SELECT count(*) FROM attempts WHERE run_id=?", (run_id,)).fetchone()[0]
        if count >= limits["max_attempts"]:
            db.execute(
                "UPDATE runs SET state='failed',reason='Shared attempt limit reached',revision=revision+1 WHERE id=?",
                (run_id,),
            )
            return None
        key = "a-" + uuid.uuid4().hex[:16]
        settings = json.loads(participant["profile_json"])
        deadline = min(
            run["deadline"],
            time.time() + limits["attempt_seconds"],
            time.time() + settings["seconds"],
        )
        output = str((directory(home, run_id) / f"{key}.log").relative_to(home.path))
        db.execute(
            "INSERT INTO attempts(id,run_id,participant_id,state,created,deadline,output_path) VALUES(?,?,?,?,?,?,?)",
            (key, run_id, participant["id"], "reserved", time.time(), deadline, output),
        )
        db.execute(
            "UPDATE participants SET state='running',next_state=NULL WHERE id=?",
            (participant["id"],),
        )
        db.execute("UPDATE runs SET state='active',revision=revision+1 WHERE id=?", (run_id,))
        return (
            dict(db.execute("SELECT * FROM attempts WHERE id=?", (key,)).fetchone()),
            dict(participant),
            dict(run),
        )


def drain(stream, path, overflow):
    total = 0
    with path.open("wb") as log:
        while True:
            chunk = stream.read(65536)
            if not chunk:
                break
            if total < LOG_LIMIT:
                log.write(chunk[: LOG_LIMIT - total])
                log.flush()
            total += len(chunk)
            if total > LOG_LIMIT:
                overflow.set()


def finish(home, attempt, participant, code, reason=None):
    from .providers import output

    path = home.path / attempt["output_path"]
    text = path.read_text(errors="replace") if path.exists() else ""
    _, usage = output(text)
    with connect(home) as db, transaction(db):
        run = row_run(db, attempt["run_id"])
        row = db.execute("SELECT * FROM participants WHERE id=?", (participant["id"],)).fetchone()
        state = "complete" if code == 0 and not reason else "failed"
        if run["state"] in ("cancelled", "expired", "interrupted"):
            state = "interrupted"
        db.execute(
            "UPDATE attempts SET state=?,ended=?,exit_code=?,reason=?,usage_json=? WHERE id=?",
            (
                state,
                time.time(),
                code,
                reason,
                json.dumps(usage) if usage is not None else None,
                attempt["id"],
            ),
        )
        if state == "interrupted":
            next_state = "interrupted"
        elif row["next_state"]:
            next_state = row["next_state"]
        elif participant["role"] in ("coordinator", "integration"):
            next_state = "waiting" if state == "complete" else "failed"
        else:
            next_state = state
        db.execute(
            "UPDATE participants SET state=?,next_state=NULL WHERE id=?",
            (next_state, participant["id"]),
        )
        if participant["role"] in ("worker", "helper") and run["state"] not in TERMINAL:
            if participant["role"] == "helper" and participant["parent_id"]:
                db.execute(
                    "UPDATE participants SET state='ready' WHERE id=? AND state='waiting'",
                    (participant["parent_id"],),
                )
                db.execute(
                    "UPDATE participants SET next_state='ready' WHERE id=? AND state='running' AND next_state='waiting'",
                    (participant["parent_id"],),
                )
            outstanding = db.execute(
                "SELECT id FROM participants WHERE run_id=? AND module=? AND role IN ('worker','helper') AND state IN ('running','ready')",
                (run["id"], participant["module"]),
            ).fetchone()
            if outstanding is None:
                db.execute(
                    "UPDATE participants SET state='ready' WHERE run_id=? AND module=? AND role='coordinator' AND state='waiting'",
                    (run["id"], participant["module"]),
                )
                db.execute(
                    "UPDATE participants SET next_state='ready' WHERE run_id=? AND module=? AND role='coordinator' AND state='running' AND next_state='waiting'",
                    (run["id"], participant["module"]),
                )
            db.execute(
                "INSERT INTO messages(id,run_id,sender,recipient,body,created) VALUES(?,?,?,?,?,?)",
                (
                    "m-" + uuid.uuid4().hex[:16],
                    run["id"],
                    participant["id"],
                    participant["parent_id"] or "operator",
                    f"Result available for {participant['id']}: {state}. Inspect it with run result; this is not an acceptance decision.",
                    time.time(),
                ),
            )
        db.execute("UPDATE runs SET revision=revision+1 WHERE id=?", (run["id"],))


def supervise(home, run_id):
    from . import providers

    active = {}
    halted = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: halted.set())
    signal.signal(signal.SIGINT, lambda *_: halted.set())
    identity = process_identity(os.getpid())
    guard_process = None
    with locked(home.path, "supervisor:" + run_id):
        with connect(home) as db, transaction(db):
            run = row_run(db, run_id)
            if run["state"] not in ("active", "waiting"):
                return
            db.execute(
                "UPDATE runs SET supervisor_pid=?,supervisor_identity=? WHERE id=?",
                (os.getpid(), identity, run_id),
            )
        guard_process = subprocess.Popen(
            [
                sys.executable,
                str(RUNTIME_ENTRY),
                "--root",
                str(home.path),
                "guard",
                run_id,
                str(os.getpid()),
                identity,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        try:
            while not halted.is_set():
                with connect(home) as db:
                    run = row_run(db, run_id)
                if run["state"] in TERMINAL or run["state"] == "interrupted":
                    break
                if guard_process.poll() is not None:
                    raise HarnessError("guard_lost", "The process guard stopped unexpectedly.")
                for key, entry in list(active.items()):
                    process, attempt, participant, thread, writer, overflow = entry
                    reason = None
                    if time.time() >= attempt["deadline"]:
                        reason = "Attempt deadline reached"
                    if overflow.is_set():
                        reason = "Attempt output limit reached"
                    if reason:
                        signal_group(process.pid, signal.SIGTERM)
                        try:
                            process.wait(timeout=0.2)
                        except subprocess.TimeoutExpired:
                            signal_group(process.pid, signal.SIGKILL)
                    code = process.poll()
                    if code is not None:
                        # Cleanup is tied to the process group created for this attempt.
                        signal_group(process.pid, signal.SIGKILL)
                        thread.join(timeout=2)
                        writer.join(timeout=2)
                        finish(home, attempt, participant, code, reason)
                        del active[key]
                reserved = reserve(home, run_id)
                if reserved:
                    attempt, participant, run = reserved
                    try:
                        argv = providers.command(home, participant)
                        tokens = read_json(directory(home, run_id) / "credentials.json")
                        with connect(home) as db:
                            siblings = [
                                dict(row)
                                for row in db.execute(
                                    "SELECT id,role,state,module FROM participants WHERE run_id=?",
                                    (run_id,),
                                )
                                if participant["role"] == "integration"
                                or row["module"] == participant["module"]
                            ]
                        brief = providers.prompt(home, run, participant, siblings)
                        child = launch(
                            home,
                            attempt,
                            participant,
                            argv,
                            providers.environment(
                                home, run, participant, tokens[participant["id"]]
                            ),
                        )
                        if child is None:
                            continue
                        overflow = threading.Event()
                        reader = threading.Thread(
                            target=drain,
                            args=(child.stdout, home.path / attempt["output_path"], overflow),
                            daemon=True,
                        )
                        reader.start()
                        writer = threading.Thread(
                            target=deliver,
                            args=(home, attempt, child.stdin, brief.encode()),
                            daemon=True,
                        )
                        active[attempt["id"]] = (
                            child,
                            attempt,
                            participant,
                            reader,
                            writer,
                            overflow,
                        )
                        writer.start()
                    except (OSError, HarnessError) as exc:
                        finish(home, attempt, participant, -1, str(exc))
                time.sleep(0.15)
        except BaseException as exc:
            with connect(home) as db, transaction(db):
                db.execute(
                    "UPDATE runs SET state='interrupted',reason=?,revision=revision+1 WHERE id=? AND state NOT IN ('accepted','cancelled','expired')",
                    (str(exc)[:500], run_id),
                )
        finally:
            if halted.is_set():
                with connect(home) as db, transaction(db):
                    db.execute(
                        "UPDATE runs SET state='interrupted',reason='Supervisor stopped',revision=revision+1 WHERE id=? AND state NOT IN ('accepted','cancelled','expired')",
                        (run_id,),
                    )
            errors = []
            try:
                stop_attempts(home, run_id, "Execution stopped")
            except (HarnessError, OSError) as exc:
                errors.append(str(exc))
            for process, attempt, participant, thread, writer, overflow in active.values():
                try:
                    signal_group(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
                    thread.join(timeout=2)
                    writer.join(timeout=2)
                    finish(home, attempt, participant, process.returncode, "Execution stopped")
                except (HarnessError, OSError, subprocess.TimeoutExpired) as exc:
                    errors.append(str(exc))
            try:
                if guard_process and guard_process.poll() is None:
                    guard_process.terminate()
                    guard_process.wait(timeout=5)
            finally:
                with connect(home) as db, transaction(db):
                    db.execute(
                        "UPDATE runs SET supervisor_pid=NULL,supervisor_identity=NULL WHERE id=?",
                        (run_id,),
                    )
                    if errors:
                        db.execute(
                            "UPDATE runs SET reason=? WHERE id=?",
                            ("Cleanup requires inspection: " + "; ".join(errors)[:1000], run_id),
                        )
