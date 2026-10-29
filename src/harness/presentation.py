"""A compact human surface alongside an unambiguous agent contract."""

from __future__ import annotations

import json
import os
import sys

TITLES = {
    ("setup", None): "Harness ready",
    ("doctor", None): "Harness status",
    ("environment", "ensure"): "Environment ready",
    ("work", "create"): "Work created",
    ("memory", "capture"): "Memory captured",
    ("memory", "put"): "Knowledge saved",
    ("record", "write"): "Record saved",
    ("workflow", "create"): "Workflow created",
    ("workflow", "write"): "Workflow saved",
    ("run", "start"): "Execution started",
    ("run", "stop"): "Execution stopped",
    ("run", "resume"): "Execution resumed",
    ("run", "decide"): "Decision recorded",
    ("message", "send"): "Message sent",
    ("message", "ack"): "Message acknowledged",
}


def emit(data, group, operation, structured=False, plain=False):
    if structured:
        print(json.dumps({"ok": True, "data": data}, ensure_ascii=False, separators=(",", ":")))
        return
    tty = sys.stdout.isatty() and not plain and "NO_COLOR" not in os.environ
    marker = "\033[32m✓\033[0m" if tty else "OK"
    title = TITLES.get(
        (group, operation),
        " ".join(x for x in (group, operation) if x).replace("-", " ").capitalize(),
    )
    print(f"{marker} {title}")

    def show(value, depth=0):
        indent = "  " * (depth + 1)
        if isinstance(value, dict):
            width = min(max((len(k.replace("_", " ")) for k in value), default=0), 24)
            for key, item in value.items():
                if key == "content":
                    print("\n" + str(item).rstrip())
                elif isinstance(item, (dict, list)):
                    print(f"{indent}{key.replace('_', ' ').capitalize()}")
                    show(item, depth + 1)
                elif item is not None:
                    display = str(item).lower() if isinstance(item, bool) else str(item)
                    print(f"{indent}{key.replace('_', ' ').capitalize():<{width}}  {display}")
        elif isinstance(value, list):
            if not value:
                print(indent + "None")
            for item in value:
                show(item, depth)
                if isinstance(item, dict) and len(value) > 1:
                    print()
        else:
            print(indent + str(value))

    show(data)


def failure(error, structured=False):
    if structured:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": {"code": error.code, "message": str(error), "hint": error.hint},
                },
                separators=(",", ":"),
            )
        )
    else:
        print(f"! {error}", file=sys.stderr)
        if error.hint:
            print(f"  Next  {error.hint}", file=sys.stderr)
