#!/usr/bin/env python3
"""Deterministic provider transport fixture; never contacts a model."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

mode = os.environ.get("HARNESS_FIXTURE_MODE", "graph")
if mode == "no-stdin":
    time.sleep(90)
brief = sys.stdin.read()
if not brief:
    raise SystemExit(0)
cli = os.environ["HARNESS_FIXTURE_CLI"]
run = os.environ["HARNESS_RUN"]
actor = os.environ["HARNESS_ACTOR"]


def call(*args, success=True):
    result = subprocess.run([cli, "--json", *args], capture_output=True, text=True)
    value = json.loads(result.stdout)
    if success and not value["ok"]:
        raise RuntimeError(value)
    return value


if mode in ("sleep", "orphan"):
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(90)"])
    with open("child.pid", "w") as out:
        out.write(str(child.pid))
    if mode == "orphan":
        while not Path("release-provider").exists():
            time.sleep(0.02)
        raise SystemExit(0)
    time.sleep(90)
elif mode == "fail":
    print("Fixture failure", flush=True)
    raise SystemExit(7)
elif mode == "effect":
    Path("executed_after_stop").write_text("Provider received a prompt.")
elif mode.startswith("graph"):
    for retry in range(8):
        state = call("run", "status", run)["data"]
        me = next(p for p in state["participants"] if p["id"] == actor)
        if me["role"] == "helper":
            if mode == "graph-helper-retry" and not Path("helper-attempted").exists():
                Path("helper-attempted").touch()
                raise SystemExit(7)
            time.sleep(1)
            break
        if me["role"] == "worker":
            if mode == "graph-resume" and not Path("allow-worker").exists():
                Path("worker-started").touch()
                time.sleep(90)
            # Exercise stale-snapshot handling deterministically in the race case.
            denied = call(
                "run",
                "decide",
                run,
                "--event",
                "accept",
                "--reason",
                "Worker cannot accept",
                "--revision",
                str(state["revision"] - (mode == "graph-race" and retry == 0)),
                success=False,
            )
            if denied.get("error", {}).get("code") == "conflict":
                continue
            assert denied.get("error", {}).get("code") == "scope_denied", denied
            break
        if me["role"] == "integration":
            worker = next(p for p in state["participants"] if p["role"] == "worker")
            coordinator = next(
                p
                for p in state["participants"]
                if p["role"] == "coordinator" and p["module"] == worker["module"]
            )
            if worker["rounds"] < 3:
                event, extra = "request_changes", ["--to", coordinator["id"]]
            elif mode in ("graph-helpers", "graph-helper-retry") and not any(
                p["role"] == "helper" for p in state["participants"]
            ):
                call(
                    "run",
                    "spawn",
                    run,
                    "--provider",
                    "claude",
                    "--model",
                    "fixture-helper",
                    "--effort",
                    "low",
                    "--reason",
                    "A bounded economical check with a clear fixture result.",
                    "--read-only",
                    "--text",
                    "Check the integrated result.",
                )
                state = call("run", "status", run)["data"]
                denied = call(
                    "run",
                    "decide",
                    run,
                    "--event",
                    "accept",
                    "--reason",
                    "Premature acceptance.",
                    "--revision",
                    str(state["revision"]),
                    success=False,
                )
                assert denied.get("error", {}).get("code") in ("invalid_state", "conflict"), denied
                break
            elif mode == "graph-helper-retry" and any(
                p["role"] == "helper" and p["state"] == "failed" for p in state["participants"]
            ):
                helper = next(
                    p
                    for p in state["participants"]
                    if p["role"] == "helper" and p["state"] == "failed"
                )
                call(
                    "run",
                    "retry",
                    run,
                    helper["id"],
                    "--reason",
                    "The fixture's transient failure is resolved.",
                )
                break
            else:
                event, extra = "accept", []
        else:
            worker = next(
                p
                for p in state["participants"]
                if p["role"] == "worker" and p["module"] == me["module"]
            )
            if worker["state"] == "idle":
                event, extra = "delegate", ["--to", worker["id"]]
            elif worker["state"] in ("failed", "interrupted"):
                event, extra = "request_changes", ["--to", worker["id"]]
            elif worker["state"] == "complete" and (
                worker["rounds"] == 1
                or (worker["rounds"] == 2 and "## Integration correction" in brief)
            ):
                event, extra = "request_changes", ["--to", worker["id"]]
            else:
                event, extra = "accept", []
        decision = call(
            "run",
            "decide",
            run,
            "--event",
            event,
            "--reason",
            "Implement and verify the assigned behavior.",
            "--revision",
            str(state["revision"]),
            *extra,
            success=False,
        )
        if decision["ok"]:
            if mode == "graph-race" and event == "delegate":
                time.sleep(2)
            break
        if decision["error"]["code"] != "conflict":
            raise RuntimeError(decision)
    else:
        raise RuntimeError("Fixture decision conflict did not resolve")

result_text = "Fixture result verified."
if mode == "selection":
    provider = os.path.basename(sys.argv[0])
    model = sys.argv[sys.argv.index("-m" if provider == "codex" else "--model") + 1]
    effort = (
        next(
            arg.split("=", 1)[1].strip('"')
            for arg in sys.argv
            if arg.startswith("model_reasoning_effort=")
        )
        if provider == "codex"
        else sys.argv[sys.argv.index("--effort") + 1]
    )
    result_text = json.dumps({"provider": provider, "model": model, "effort": effort})
if "claude" in os.path.basename(sys.argv[0]):
    print(
        json.dumps(
            {
                "type": "result",
                "result": result_text,
                "usage": {"input_tokens": 10, "output_tokens": 5},
            }
        ),
        flush=True,
    )
else:
    print(
        json.dumps(
            {
                "type": "item.completed",
                "item": {"type": "agent_message", "text": result_text},
            }
        ),
        flush=True,
    )
    print(
        json.dumps({"type": "turn.completed", "usage": {"input_tokens": 10, "output_tokens": 5}}),
        flush=True,
    )
