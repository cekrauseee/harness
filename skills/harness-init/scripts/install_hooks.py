#!/usr/bin/env python3
"""Install Harness lifecycle hooks into supported host configuration files."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
from pathlib import Path
import shlex
import tempfile


MARKER = "harness-init/scripts/hook_adapter.py"
EVENTS = {
    "SessionStart": ("startup|resume|clear|compact", "session-start"),
}


def atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary)


def config_path(host: str) -> Path:
    if host == "codex":
        return Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser() / "hooks.json"
    if host == "claude-code":
        return Path("~/.claude/settings.json").expanduser()
    raise ValueError(f"Unsupported host: {host}")


def load_config(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Cannot install hooks into invalid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"Host configuration must contain a JSON object: {path}")
    return value


def managed(value: object) -> bool:
    return MARKER in json.dumps(value, sort_keys=True)


def preserve_unmanaged_group(value: object) -> object | None:
    """Remove Harness handlers without discarding unrelated handlers beside them."""
    if not isinstance(value, dict):
        return value
    handlers = value.get("hooks")
    if not isinstance(handlers, list):
        return None if managed(value) else value
    retained = [handler for handler in handlers if not managed(handler)]
    if retained == handlers:
        return value
    if not retained:
        return None
    updated = dict(value)
    updated["hooks"] = retained
    return updated


def hook_group(adapter: Path, matcher: str | None, event: str) -> dict:
    command = f"python3 {shlex.quote(str(adapter))} event {event}"
    group: dict = {
        "hooks": [
            {
                "type": "command",
                "command": command,
                "timeout": 15,
            }
        ]
    }
    if matcher:
        group["matcher"] = matcher
    return group


def install(host: str, adapter: Path) -> dict:
    path = config_path(host)
    config = load_config(path)
    hooks = config.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise RuntimeError(f"The hooks key must contain a JSON object: {path}")

    changed = False
    all_events = set(EVENTS) | {"UserPromptSubmit", "PreCompact", "Stop"}
    for event_name in sorted(all_events):
        existing = hooks.get(event_name, [])
        if not isinstance(existing, list):
            raise RuntimeError(f"hooks.{event_name} must contain a JSON array: {path}")
        retained = [
            preserved
            for item in existing
            if (preserved := preserve_unmanaged_group(item)) is not None
        ]
        if event_name in EVENTS:
            matcher, event = EVENTS[event_name]
            updated = retained + [hook_group(adapter, matcher, event)]
        else:
            updated = retained
        if updated != existing:
            if updated:
                hooks[event_name] = updated
            else:
                hooks.pop(event_name, None)
            changed = True

    if changed or not path.exists():
        atomic_write(path, json.dumps(config, indent=2, ensure_ascii=False) + "\n")
    return {"changed": changed, "host": host, "path": str(path)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--host",
        action="append",
        choices=("codex", "claude-code"),
        help="Host to configure. Repeat the option to configure both hosts.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    adapter = Path(__file__).resolve().with_name("hook_adapter.py")
    try:
        results = [install(host, adapter) for host in (args.host or ["codex", "claude-code"])]
    except (OSError, RuntimeError, ValueError) as exc:
        parser.exit(2, f"{exc}\n")
    if args.json:
        print(json.dumps({"results": results}, sort_keys=True))
    else:
        for result in results:
            state = "updated" if result["changed"] else "unchanged"
            print(f"{result['host']}: {state}: {result['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
