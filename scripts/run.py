#!/usr/bin/env python3
"""Harness launcher: start, resume and wait for one Codex or Claude CLI run under an orchestration front.

Each command acts once, on an agent's explicit request: no queue, no autonomous dispatch. A detached
supervisor runs the host CLI with stdin closed, keeps its raw output as evidence under runs/raw/,
appends events, and retries rate limits or transient failures only when --retry asks for it.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import Error, atomic_write, encoded, fail, make_directory, safe_path  # noqa: E402
from records import SLUG, append_event, changed_paths, commit, environment, front_directory  # noqa: E402

HOSTS = ("codex", "claude")
FINAL = ("delivered", "failed", "rate_limited")
RATE_LIMIT = re.compile(r"\b429\b|rate[ _-]?limit|too many requests|usage limit|quota", re.I)
TRANSIENT = re.compile(r"\b5(?:00|02|03|04|29)\b|overloaded|timed out|timeout|connection (?:reset|refused|closed)"
                       r"|econnreset|network error|stream (?:disconnected|error)|temporarily unavailable", re.I)
CONTINUE = "Continue the assigned task from where it stopped; the previous attempt was interrupted."
MESSAGE_LIMIT = 2000


# --- Host commands and output ----------------------------------------------------------------

def command(state, prompt, attempt, resume):
    """Host CLI arguments for one attempt. Extra options must suit both start and resume when retrying."""
    session, extra = state.get("session"), state.get("extra", [])
    if state["host"] == "codex":
        last = str(raw_path(state, attempt, "last.md"))
        options = (["-m", state["model"]] if state.get("model") else []) + \
                  (["-c", f"model_reasoning_effort={state['effort']}"] if state.get("effort") else [])
        if resume:
            return ["codex", "exec", "resume", "--json", "-o", last, *options, *extra, session, prompt]
        return ["codex", "exec", "--json", "-C", state["cwd"], "-o", last, *options, *extra, prompt]
    options = (["--model", state["model"]] if state.get("model") else []) + \
              (["--effort", state["effort"]] if state.get("effort") else [])
    flag = "--resume" if resume else "--session-id"
    return ["claude", "-p", flag, session, "--output-format", "json", *options, *extra, prompt]


def parse_codex(lines):
    session, tokens, errors, completed, message = None, {}, [], False, None
    for line in lines:
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        kind = event.get("type")
        if kind == "thread.started":
            session = event.get("thread_id") or session
        elif kind == "turn.completed":
            completed = True
            usage = event.get("usage") or {}
            for name, key in (("input", "input_tokens"), ("cached", "cached_input_tokens"), ("output", "output_tokens")):
                if isinstance(usage.get(key), int):
                    tokens[name] = tokens.get(name, 0) + usage[key]
        elif kind == "turn.failed":
            completed = False
            errors.append(str((event.get("error") or {}).get("message", "turn failed")))
        elif kind == "error":
            errors.append(str(event.get("message", "error")))
        elif kind == "item.completed" and (event.get("item") or {}).get("type") == "agent_message":
            message = event["item"].get("text", message)
    return {"session": session, "tokens": tokens, "error": None if completed else "; ".join(errors[-2:]) or None,
            "message": message}


def parse_claude(text):
    try:
        result = json.loads(text.strip().split("\n")[-1]) if text.strip() else {}
    except ValueError:
        result = {}
    if not isinstance(result, dict):
        result = {}
    usage, tokens = result.get("usage") or {}, {}
    parts = [usage.get(k) for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")]
    if any(isinstance(p, int) for p in parts):
        tokens["input"] = sum(p for p in parts if isinstance(p, int))
    if isinstance(usage.get("cache_read_input_tokens"), int):
        tokens["cached"] = usage["cache_read_input_tokens"]
    if isinstance(usage.get("output_tokens"), int):
        tokens["output"] = usage["output_tokens"]
    failed = not result or result.get("is_error") or result.get("subtype", "success") != "success"
    message = result.get("result") if isinstance(result.get("result"), str) else None
    return {"session": result.get("session_id"), "tokens": tokens,
            "error": (message or result.get("subtype") or "no result") if failed else None, "message": message}


def classify(exit_code, parsed, stderr_tail):
    if exit_code == 0 and not parsed["error"]:
        return "delivered"
    text = f"{parsed['error'] or ''} {stderr_tail}"
    if RATE_LIMIT.search(text):
        return "rate_limited"
    return "transient" if TRANSIENT.search(text) else "failed"


# --- State -----------------------------------------------------------------------------------

def raw_path(state, attempt, suffix):
    return Path(state["front_dir"]) / "runs" / "raw" / f"{state['run']}.{attempt}.{suffix}"


def state_path(front_dir, run):
    if not SLUG.fullmatch(run or ""):
        fail("invalid_input", "Use a readable lowercase run id with hyphens.")
    return safe_path(front_dir / "runs" / "raw" / f"{run}.state.json")


def load_state(path):
    try:
        return json.loads(safe_path(path).read_text())
    except FileNotFoundError:
        fail("run_missing", "No launcher state for that run.", state=str(path))


def save_state(state):
    atomic_write(Path(state["front_dir"]) / "runs" / "raw" / f"{state['run']}.state.json", encoded(state))


def event(state, kind, **fields):
    data = {"kind": kind, "run": state["run"], "host": state["host"], "iteration": state["iteration"],
            **{k: state[k] for k in ("actor", "model", "effort", "session") if state.get(k)}, **fields}
    append_event(Path(state["environment"]), state["work"], state["front"], data)


def tail(path, limit=2000):
    try:
        with open(path, "rb") as stream:
            stream.seek(max(0, os.path.getsize(path) - limit))
            return stream.read().decode(errors="replace")
    except OSError:
        return ""


def write_draft(state, final=False):
    """Pre-fill the run record draft: identity and base at start, head and changed paths after the run."""
    runs = Path(state["front_dir"]) / "runs"
    if (runs / f"{state['run']}.record.json").exists():
        return None
    draft = {"format": "harness-record-v1", "work": state["work"], "front": state["front"], "run": state["run"],
             "kind": state["kind"], "iteration": state["iteration"], "host": state["host"], "base": state["base"],
             "owned": state["owned"]}
    for key in ("model", "session"):
        if state.get(key):
            draft[key] = state[key]
    if final:
        draft["head"] = commit(state["cwd"], "HEAD")
        draft["changed"] = changed_paths(state["cwd"], state["base"], draft["head"])
    path = runs / f"{state['run']}.draft.json"
    atomic_write(path, encoded(draft))
    return path


# --- Supervisor ------------------------------------------------------------------------------

def supervise(path):
    state = load_state(path)
    prompt = Path(state["prompt"]).read_text()
    delay = state["retry_delay"]
    for attempt in range(1, state["retry"] + 2):
        # Retries continue a session the host already created; otherwise they start over.
        resuming = bool(state.get("resume") or attempt > 1 and state.get("session_started"))
        if not resuming and attempt > 1 and state["host"] == "claude":
            state["session"] = str(uuid.uuid4())
        arguments = command(state, prompt if attempt == 1 or not resuming else CONTINUE, attempt, resuming)
        event(state, "resume" if resuming else "spawn", ref=state["prompt"][-500:])
        output = raw_path(state, attempt, "jsonl" if state["host"] == "codex" else "json")
        errors = raw_path(state, attempt, "stderr")
        started = time.monotonic()
        with open(output, "wb") as stdout, open(errors, "wb") as stderr:
            try:
                exit_code = subprocess.run(arguments, cwd=state["cwd"], stdin=subprocess.DEVNULL, stdout=stdout,
                                           stderr=stderr).returncode
            except OSError as exc:
                stderr.write(str(exc).encode())
                exit_code = 127
        duration = int((time.monotonic() - started) * 1000)
        # Raw output is parsed here, line by line, and never returned whole.
        with open(output, errors="replace") as stream:
            parsed = parse_codex(stream) if state["host"] == "codex" else parse_claude(stream.read())
        if state["host"] == "codex" and raw_path(state, attempt, "last.md").is_file():
            parsed["message"] = raw_path(state, attempt, "last.md").read_text(errors="replace")
        state["session"] = parsed["session"] or state.get("session")
        state["session_started"] = bool(state.get("session_started") or parsed["session"])
        outcome = classify(exit_code, parsed, tail(errors))
        state["attempts"].append({"attempt": attempt, "exit": exit_code, "outcome": outcome, "duration_ms": duration,
                                  "tokens": parsed["tokens"], "error": (parsed["error"] or "")[:500] or None})
        state["message"] = (parsed["message"] or "")[-MESSAGE_LIMIT:] or None
        fields = {"duration_ms": duration, **({"tokens": parsed["tokens"]} if parsed["tokens"] else {})}
        retry = outcome in ("rate_limited", "transient") and attempt <= state["retry"]
        if outcome == "delivered":
            event(state, "delivered", **fields)
        else:
            note = f"{'retrying: ' if retry else ''}{parsed['error'] or f'exit {exit_code}'}"
            event(state, "rate_limited" if outcome == "rate_limited" else "failed", note=note[:140], **fields)
        state["status"] = outcome if outcome != "transient" else "failed"
        if not retry:
            break
        state["status"] = "running"
        save_state(state)
        time.sleep(delay)
        delay = min(delay * 2, 600)
    state["finished"] = time.time()
    try:
        state["draft"] = str(write_draft(state, final=True) or "") or None
    except Error as exc:
        state["draft_error"] = exc.message
    save_state(state)


# --- Commands --------------------------------------------------------------------------------

def launch(state):
    make_directory(Path(state["front_dir"]) / "runs" / "raw")
    path = state_path(Path(state["front_dir"]), state["run"])
    if path.exists():
        fail("run_exists", "Run ids are unique per front; resume under a new run id.", run=state["run"])
    if not Path(state["prompt"]).is_file():
        fail("invalid_input", "The prompt must be a readable file.", prompt=state["prompt"])
    state["draft"] = str(write_draft(state) or "") or None
    save_state(state)
    log = raw_path(state, 0, "supervisor.log")
    with open(log, "wb") as stream:
        process = subprocess.Popen([sys.executable, "-B", str(Path(__file__).resolve()), "supervise", "--state", str(path)],
                                   stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT,
                                   start_new_session=True)
    state["supervisor"] = process.pid
    save_state(state)
    return {"run": state["run"], "status": "running", "session": state.get("session"), "state": str(path),
            "draft": state["draft"], "wait": f"run.py wait --run {state['run']}"}


def start(folder, args):
    front_dir = front_directory(folder, args["work"], args["front"])
    if args["host"] not in HOSTS:
        fail("invalid_input", "Host must be codex or claude.")
    cwd = str(Path(args["cwd"]).expanduser().resolve())
    owned = [i for i in (args.get("owned") or "").replace(",", " ").split() if i]
    state = {"environment": str(folder), "work": args["work"], "front": args["front"], "front_dir": str(front_dir),
             "run": args["run"], "host": args["host"], "cwd": cwd, "prompt": str(Path(args["prompt"]).resolve()),
             "kind": args["kind"], "iteration": args["iteration"], "owned": owned, "actor": args.get("actor"),
             "model": args.get("model"), "effort": args.get("effort"), "extra": args.get("extra") or [],
             "retry": args["retry"], "retry_delay": args["retry_delay"], "base": commit(cwd, "HEAD"),
             "session": str(uuid.uuid4()) if args["host"] == "claude" else None,
             "status": "running", "attempts": [], "started": time.time()}
    return launch(state)


def resume(folder, args):
    front_dir = front_directory(folder, args["work"], args["front"])
    previous = load_state(state_path(front_dir, args["source"]))
    if previous["status"] not in FINAL:
        fail("run_active", "The previous run has not finished; wait for it first.", run=args["source"])
    if not previous.get("session"):
        fail("session_missing", "The previous run has no session to resume; start a new run.", run=args["source"])
    state = {**{k: previous[k] for k in ("environment", "work", "front", "front_dir", "host", "cwd", "kind", "owned",
                                         "actor", "model", "effort", "session", "base")},
             "run": args["run"], "iteration": previous["iteration"] + 1, "resume": True, "session_started": True,
             "prompt": str(Path(args["prompt"]).resolve()), "extra": args.get("extra") or previous.get("extra", []),
             "retry": args["retry"], "retry_delay": args["retry_delay"], "status": "running", "attempts": [],
             "started": time.time(), "from": args["source"]}
    return launch(state)


def summary(state):
    tokens = {}
    for attempt in state["attempts"]:
        for name, value in attempt["tokens"].items():
            tokens[name] = tokens.get(name, 0) + value
    record = Path(state["front_dir"]) / "runs" / f"{state['run']}.record.json"
    message = state.get("message") or ""
    lines = message.split("\n")
    if len(lines) > 25:
        message = "\n".join(lines[:25]) + f"\n[{len(lines) - 25} more lines in the raw last message]"
    result = {"run": state["run"], "status": state["status"], "attempts": len(state["attempts"]),
              "session": state.get("session"), "tokens": tokens,
              "duration_ms": sum(a["duration_ms"] for a in state["attempts"]),
              "record": str(record) if record.exists() else None, "draft": state.get("draft"),
              "error": state["attempts"][-1]["error"] if state["attempts"] else None, "message": message or None}
    return {k: v for k, v in result.items() if v not in (None, {}, "")}


def alive(pid):
    if not pid:
        return True  # supervisor not recorded yet
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass
    return True


def wait(folder, args):
    path = state_path(front_directory(folder, args["work"], args["front"]), args["run"])
    deadline = time.monotonic() + args["timeout"] if args.get("timeout") is not None else None
    while True:
        state = load_state(path)
        if state["status"] in FINAL and state.get("finished"):
            return summary(state)
        if not alive(state.get("supervisor")):
            state = load_state(path)
            if not (state["status"] in FINAL and state.get("finished")):
                return {**summary(state), "status": "failed", "error": "the launcher supervisor is no longer running"}
            return summary(state)
        if deadline is not None and time.monotonic() >= deadline:
            return {**summary(state), "status": "running", "timeout": True}
        time.sleep(1)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--home", help="Binding storage (HARNESS_HOME or ~/.harness)")
    commands = parser.add_subparsers(dest="operation", required=True)
    for name in ("start", "resume", "wait"):
        sub = commands.add_parser(name)
        group = sub.add_mutually_exclusive_group(required=True)
        group.add_argument("--environment")
        group.add_argument("--project")
        sub.add_argument("--work", required=True)
        sub.add_argument("--front", required=True)
        sub.add_argument("--run", required=True, help="Unique run id in the front, one per iteration")
        if name == "wait":
            sub.add_argument("--timeout", type=float, help="Seconds; returns the running state when reached")
            continue
        sub.add_argument("--prompt", required=True, help="File holding the prompt")
        sub.add_argument("--retry", type=int, default=0, help="Retries for rate limits and transient failures")
        sub.add_argument("--retry-delay", type=float, default=60.0, help="First retry delay in seconds, doubled each time")
        sub.add_argument("extra", nargs="*", help="Host CLI options after --, such as permission or sandbox flags")
        if name == "resume":
            sub.add_argument("--from", dest="source", required=True, help="Earlier run whose session continues")
        else:
            sub.add_argument("--host", required=True, choices=HOSTS)
            sub.add_argument("--cwd", required=True, help="Checkout the run works in")
            sub.add_argument("--kind", default="implement", choices=("implement", "test", "review"))
            sub.add_argument("--iteration", type=int, default=1)
            sub.add_argument("--owned", help="Owned attention point and flow ids, comma separated")
            sub.add_argument("--actor", help="Logical agent name")
            sub.add_argument("--model")
            sub.add_argument("--effort")
    supervisor = commands.add_parser("supervise")
    supervisor.add_argument("--state", required=True)
    args = vars(parser.parse_args(argv))
    try:
        if args["operation"] == "supervise":
            try:
                supervise(Path(args["state"]))
            except Exception as exc:  # never leave a run looking active
                state = load_state(Path(args["state"]))
                state.update(status="failed", finished=time.time(), supervisor_error=str(exc)[:500])
                save_state(state)
                event(state, "failed", note=f"launcher error: {exc}"[:140])
                raise
            return 0
        folder = environment(args)
        result = {"start": start, "resume": resume, "wait": wait}[args["operation"]](folder, args)
    except Error as exc:
        print(json.dumps({"error": {"code": exc.code, "message": exc.message, "details": exc.details}}, ensure_ascii=False))
        return 1
    except OSError as exc:
        print(json.dumps({"error": {"code": "io_error", "message": "Inspect state before retrying.", "details": {"reason": str(exc)}}}))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    if result.get("timeout"):
        return 2
    return 0 if result.get("status") in ("running", "delivered") else 1


if __name__ == "__main__":
    sys.exit(main())
