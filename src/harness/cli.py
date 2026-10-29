"""The single operational entry point used by people, skills, and hooks."""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from pathlib import Path

from . import __version__, context, memory, messages, runs, setup, workflows
from .access import Actor, operator_only
from .config import Home, validate_limits
from .errors import HarnessError, require
from .files import locked, write_json
from .presentation import emit, failure


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise HarnessError(
            "invalid_arguments", message, "Use harness --help or a command's --help."
        )


def content(path=None, text=None, required=True):
    if path:
        value = sys.stdin.read(262145) if path == "-" else Path(path).expanduser().read_text()
    else:
        value = text or ""
    require(
        not required or bool(value.strip()), "missing_content", "Provide text or a content file."
    )
    require(len(value.encode()) <= 262144, "content_too_large", "Input is limited to 256 KiB.")
    return value


def input_options(parser, text="--text", file="--file", required=True):
    group = parser.add_mutually_exclusive_group(required=required)
    group.add_argument(text, dest="text")
    group.add_argument(file, dest="file")


def pagination(parser):
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--offset", type=int, default=0)


def parser():
    root = Parser(
        prog="harness",
        description="Local context, memory, and managed agent execution.",
        epilog="Place global options before the command. Use --json for agent-readable output.",
    )
    root.add_argument("--version", action="version", version=__version__)
    root.add_argument("--root", help="Data root (default: HARNESS_ROOT or ~/.harness)")
    root.add_argument("--environment", help="Explicit environment context")
    root.add_argument("--work", help="Explicit work context")
    root.add_argument("--json", action="store_true", help="Compact structured results")
    root.add_argument("--plain", action="store_true", help="Plain presentation without color")
    root.add_argument("--debug", action="store_true", help="Include diagnostic tracebacks")
    groups = root.add_subparsers(dest="group", required=True)
    p = groups.add_parser("setup", help="Prepare the Harness and optional host integration")
    p.add_argument("--host", choices=("codex", "claude"))
    p.add_argument("--host-home", help="Explicit home directory for a host installation")
    groups.add_parser("doctor", help="Inspect local prerequisites")

    env = groups.add_parser("environment", help="Manage environments").add_subparsers(
        dest="op", required=True
    )
    p = env.add_parser("ensure")
    p.add_argument("id")
    p.add_argument("--title")
    p = env.add_parser("list")
    pagination(p)
    p = env.add_parser("show")
    p.add_argument("id")
    p = env.add_parser("archive")
    p.add_argument("id")
    work = groups.add_parser("work", help="Manage continuity of purpose").add_subparsers(
        dest="op", required=True
    )
    p = work.add_parser("create")
    p.add_argument("id")
    p.add_argument("--title", required=True)
    p.add_argument("--purpose", required=True)
    p = work.add_parser("list")
    pagination(p)
    p = work.add_parser("show")
    p.add_argument("id")
    p = work.add_parser("archive")
    p.add_argument("id")
    resource = groups.add_parser(
        "resource", help="Bind resources to an environment"
    ).add_subparsers(dest="op", required=True)
    resource.add_parser("list")
    p = resource.add_parser("add")
    p.add_argument("id")
    p.add_argument("--location", required=True)
    p.add_argument(
        "--kind",
        choices=("directory", "repository", "worktree", "url", "branch", "pull-request"),
        default="directory",
    )
    p.add_argument("--owned", action="store_true")
    p = resource.add_parser("remove")
    p.add_argument("id")

    record = groups.add_parser("record", help="Read and maintain Markdown records").add_subparsers(
        dest="op", required=True
    )
    p = record.add_parser("read")
    p.add_argument("path")
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--limit", type=int, default=12000)
    p = record.add_parser("write")
    p.add_argument("path")
    p.add_argument("--revision")
    input_options(p)
    p = record.add_parser("delete")
    p.add_argument("path")
    p.add_argument("--revision", required=True)
    for op in ("list", "search"):
        p = record.add_parser(op)
        p.add_argument("--prefix", required=True)
        p.add_argument("--query", default="")
        pagination(p)
    mem = groups.add_parser(
        "memory", help="Capture candidates and maintain knowledge"
    ).add_subparsers(dest="op", required=True)
    p = mem.add_parser("capture")
    p.add_argument("--title", required=True)
    p.add_argument("--source", default="")
    p.add_argument("--global", dest="global_scope", action="store_true")
    input_options(p)
    p = mem.add_parser("put")
    p.add_argument("id")
    p.add_argument("--revision")
    p.add_argument("--global", dest="global_scope", action="store_true")
    input_options(p)
    for op in ("search", "list"):
        p = mem.add_parser(op)
        p.add_argument("--query", default="")
        p.add_argument("--captures", action="store_true")
        p.add_argument("--global", dest="global_scope", action="store_true")
        pagination(p)

    profile = groups.add_parser("profile", help="Configure explicit model profiles").add_subparsers(
        dest="op", required=True
    )
    profile.add_parser("list")
    p = profile.add_parser("set")
    p.add_argument("id")
    p.add_argument("--file", required=True)
    p = profile.add_parser("default")
    p.add_argument("role", choices=("scout", "worker", "coordinator"))
    p.add_argument("profile")
    conf = groups.add_parser(
        "config", help="Inspect configuration and set execution defaults"
    ).add_subparsers(dest="op", required=True)
    conf.add_parser("show")
    p = conf.add_parser("limits")
    p.add_argument("--file", required=True)

    workflow = groups.add_parser(
        "workflow", help="Define explicit development and review graphs"
    ).add_subparsers(dest="op", required=True)
    p = workflow.add_parser("create")
    p.add_argument("id")
    p.add_argument("--mode", choices=("develop", "review"), required=True)
    p.add_argument("--module", required=True)
    p.add_argument("--resource", required=True)
    p.add_argument("--context", action="append", default=[])
    p = workflow.add_parser("write")
    p.add_argument("id")
    p.add_argument("--file", required=True)
    p.add_argument("--revision")
    p = workflow.add_parser("read")
    p.add_argument("id")
    p = workflow.add_parser("validate")
    p.add_argument("--file", required=True)

    run = groups.add_parser(
        "run", help="Start, inspect, decide, and stop managed execution"
    ).add_subparsers(dest="op", required=True)
    p = run.add_parser("start")
    input_options(p)
    p.add_argument("--resource")
    p.add_argument("--profile")
    p.add_argument("--workflow")
    p.add_argument("--authorization", help="Record the user's authorization for this execution")
    p.add_argument(
        "--autonomous",
        action="store_true",
        help="Use a configured economical profile within its bounded allowance",
    )
    p = run.add_parser("list")
    p.add_argument("--limit", type=int, default=20)
    p = run.add_parser("status")
    p.add_argument("id")
    p = run.add_parser("wait")
    p.add_argument("id")
    p.add_argument("--seconds", type=float, default=30)
    p.add_argument("--after", type=int)
    p = run.add_parser("result")
    p.add_argument("id")
    p.add_argument("participant")
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--limit", type=int, default=12000)
    p = run.add_parser("decide")
    p.add_argument("id")
    p.add_argument(
        "--event", choices=("delegate", "request_changes", "accept", "fail"), required=True
    )
    p.add_argument("--participant")
    p.add_argument("--to")
    p.add_argument("--context", action="append", default=[])
    p.add_argument("--revision", type=int, required=True)
    input_options(p, "--reason", "--reason-file")
    p = run.add_parser("stop")
    p.add_argument("id")
    p.add_argument("--reason", default="Stopped by the user.")
    p = run.add_parser("resume")
    p.add_argument("id")
    p.add_argument("--reason", required=True)
    p = run.add_parser("recover")
    p.add_argument("id")
    p.add_argument("--confirm-stopped", action="store_true")
    p = run.add_parser("spawn")
    p.add_argument("id")
    p.add_argument("--profile", required=True)
    input_options(p)
    p = run.add_parser("retry", help="Retry a failed helper within the original execution budget")
    p.add_argument("id")
    p.add_argument("participant")
    p.add_argument("--reason", required=True)

    msg = groups.add_parser(
        "message", help="Send, read, and acknowledge execution messages"
    ).add_subparsers(dest="op", required=True)
    p = msg.add_parser("send")
    p.add_argument("run")
    p.add_argument("--to", required=True)
    input_options(p)
    p = msg.add_parser("inbox")
    p.add_argument("run")
    p.add_argument("--recipient")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--unread", action="store_true")
    for op in ("read", "ack"):
        p = msg.add_parser(op)
        p.add_argument("id")
    groups.add_parser("hook", help="Handle a lifecycle event from stdin")
    return root


def execute(args, home, actor):
    group, op = args.group, getattr(args, "op", None)
    env, work = args.environment, args.work
    if group == "setup":
        return setup.prepare(home, args.host, args.host_home, actor)
    if group == "doctor":
        return setup.doctor(home)
    if group == "environment":
        if op == "ensure":
            return context.ensure_environment(home, args.id, args.title, actor)
        if op == "list":
            return context.list_context(
                home, group, limit=args.limit, offset=args.offset, actor=actor
            )
        if op == "show":
            name = context.environment_id(home, args.id, actor)
            return context.read_record(home, f"environments/{name}/environment.md", actor)
        return context.archive_context(home, group, args.id, actor=actor)
    if group == "work":
        if op == "create":
            return context.create_work(home, env, args.id, args.title, args.purpose, actor)
        if op == "list":
            return context.list_context(home, group, env, args.limit, args.offset, actor)
        if op == "show":
            name = context.environment_id(home, env, actor)
            key = context.work_id(home, name, args.id, actor)
            return context.read_record(home, f"environments/{name}/work/{key}/work.md", actor)
        return context.archive_context(home, group, args.id, env, actor)
    if group == "resource":
        return context.resources(
            home,
            env,
            op,
            getattr(args, "id", None),
            getattr(args, "location", None),
            getattr(args, "kind", "directory"),
            work,
            getattr(args, "owned", False),
            actor,
        )
    if group == "record":
        if op == "read":
            return context.read_record(home, args.path, actor, args.offset, args.limit)
        if op == "write":
            return context.write_record(
                home, args.path, content(args.file, args.text), args.revision, actor
            )
        if op == "delete":
            return context.delete_record(home, args.path, args.revision, actor)
        return context.search_records(home, args.prefix, args.query, actor, args.limit, args.offset)
    if group == "memory":
        if op == "capture":
            return memory.capture(
                home,
                args.title,
                content(args.file, args.text),
                args.source,
                env,
                args.global_scope,
                actor,
            )
        if op == "put":
            return memory.put(
                home,
                args.id,
                content(args.file, args.text),
                args.revision,
                env,
                args.global_scope,
                actor,
            )
        return memory.search(
            home, args.query, env, args.global_scope, args.captures, actor, args.limit, args.offset
        )
    if group == "profile":
        if op == "list":
            return {"profiles": home.config()["profiles"], "defaults": home.config()["defaults"]}
        operator_only(actor)
        if op == "set":
            return home.set_profile(args.id, json.loads(content(args.file)))
        home.profile(args.profile)
        with locked(home.path, "config.json"):
            config = home.config()
            config["defaults"][args.role] = args.profile
            write_json(home.path / "config.json", config)
        return {"role": args.role, "profile": args.profile}
    if group == "config":
        if op == "show":
            return home.config()
        operator_only(actor)
        limits = validate_limits(json.loads(content(args.file)))
        home.ensure()
        with locked(home.path, "config.json"):
            config = home.config()
            config["limits"] = limits
            write_json(home.path / "config.json", config)
        return {"limits": limits}
    if group == "workflow":
        if op == "create":
            definition = workflows.template(
                home, args.mode, args.module, args.resource, args.context
            )
            return workflows.put(home, env, work, args.id, definition, actor=actor)
        if op == "write":
            return workflows.put(
                home, env, work, args.id, json.loads(content(args.file)), args.revision, actor
            )
        if op == "validate":
            operator_only(actor)
            workflows.validate(
                home, json.loads(content(args.file)), context.environment_id(home, env)
            )
            return {"valid": True}
        return workflows.get(home, env, work, args.id, actor)
    if group == "run":
        if op == "start":
            return runs.create(
                home,
                env,
                work,
                args.resource,
                content(args.file, args.text),
                args.profile,
                args.workflow,
                args.authorization,
                args.autonomous,
                actor,
            )
        if op == "list":
            return runs.list_runs(home, env, args.limit, actor)
        if op == "status":
            return runs.status(home, args.id, actor)
        if op == "result":
            return runs.result(home, args.id, args.participant, actor, args.offset, args.limit)
        if op == "decide":
            return runs.decide(
                home,
                args.id,
                args.event,
                content(args.file, args.text),
                args.revision,
                args.participant,
                args.to,
                args.context,
                actor,
            )
        if op == "stop":
            return runs.stop(home, args.id, args.reason, actor)
        if op == "resume":
            return runs.resume(home, args.id, args.reason, actor)
        if op == "recover":
            return runs.recover(home, args.id, args.confirm_stopped, actor)
        if op == "spawn":
            return runs.spawn_helper(
                home, args.id, args.profile, content(args.file, args.text), actor
            )
        if op == "retry":
            return runs.retry_helper(home, args.id, args.participant, args.reason, actor)
        if op == "wait":
            require(
                0 <= args.seconds <= 60, "invalid_wait", "Wait for at most 60 seconds per call."
            )
            end = time.monotonic() + args.seconds
            while True:
                value = runs.status(home, args.id, actor)
                if (
                    value["state"] != "active"
                    or (args.after is not None and value["revision"] != args.after)
                    or time.monotonic() >= end
                ):
                    return value
                time.sleep(0.25)
    if group == "message":
        if op == "send":
            return messages.send(home, args.run, args.to, content(args.file, args.text), actor)
        if op == "inbox":
            return messages.inbox(home, args.run, args.recipient, actor, args.limit, args.unread)
        return messages.read(home, args.id, actor, op == "ack")
    raise HarnessError("invalid_operation", "Unknown operation.")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    structured = "--json" in argv
    try:
        args = parser().parse_args(argv)
        require(
            sys.platform in ("darwin", "linux"),
            "unsupported_platform",
            "Managed Harness execution supports macOS and Linux.",
        )
        home = Home(args.root)
        if args.group == "hook":
            from .hooks import handle

            try:
                raw = sys.stdin.read(262145)
                payload = json.loads(raw) if len(raw) <= 262144 and raw.strip() else {}
                result = handle(home, payload)
            except (HarnessError, OSError, ValueError, TypeError, KeyError):
                print(
                    "Harness notification unavailable; inspect harness doctor or run status.",
                    file=sys.stderr,
                )
                result = {}
            print(json.dumps(result, ensure_ascii=False))
            return 0
        if args.group in ("run", "message") and getattr(args, "op", None) not in ("start", "list"):
            require(
                (home.path / "state.sqlite").exists(),
                "not_initialized",
                "No execution state exists.",
                "Start an execution through run start.",
            )
        actor = Actor.current(home)
        result = execute(args, home, actor)
        emit(result, args.group, getattr(args, "op", None), args.json, args.plain)
        return 0
    except HarnessError as exc:
        failure(exc, structured)
        return exc.exit_code
    except (OSError, ValueError, TypeError, KeyError) as exc:
        if "--debug" in argv:
            traceback.print_exc(file=sys.stderr)
        failure(
            HarnessError(
                "operation_failed",
                str(exc),
                "Check the input and local configuration. Use --debug for diagnostics.",
            ),
            structured,
        )
        return 2
    except KeyboardInterrupt:
        failure(HarnessError("interrupted", "Operation interrupted."), structured)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
