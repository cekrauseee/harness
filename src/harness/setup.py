"""Idempotent preparation and narrowly owned host integration."""

from __future__ import annotations

import re
import shlex
import shutil
import sys
import tomllib
from pathlib import Path

from .access import operator_only
from .database import connect
from .errors import require
from .files import atomic_write, locked, read_json, write_json
from .runs import PACKAGE_ROOT

BEGIN = "<!-- Harness managed context -->"
END = "<!-- End Harness managed context -->"


def instructions(home):
    source = (PACKAGE_ROOT / "instructions" / "global.md").read_text().strip()
    return source + f"\n\nHarness CLI: `{home.path / 'bin' / 'harness'}`.\n"


def upsert_instructions(home, path):
    with locked(home.path, str(path)):
        text = path.read_text() if path.exists() else ""
        require(
            text.count(BEGIN) == text.count(END) and text.count(BEGIN) <= 1,
            "invalid_integration",
            "The existing Harness instruction block is malformed.",
        )
        block = BEGIN + "\n" + instructions(home) + END
        if BEGIN in text:
            start, end = text.index(BEGIN), text.index(END) + len(END)
            updated = text[:start] + block + text[end:]
        else:
            updated = text.rstrip() + ("\n\n" if text.strip() else "") + block + "\n"
        atomic_write(path, updated.encode())


def codex_memory(home, path):
    with locked(home.path, str(path)):
        text = path.read_text() if path.exists() else ""
        parsed = tomllib.loads(text)
        require(
            isinstance(parsed.get("memories", {}), dict),
            "invalid_integration",
            "Codex memories configuration is not a table.",
        )
        lines = text.splitlines(keepends=True)
        start = next(
            (
                i
                for i, line in enumerate(lines)
                if re.fullmatch(r"\s*\[memories\]\s*(?:#.*)?\n?", line)
            ),
            None,
        )
        if start is None:
            require(
                "memories" not in parsed,
                "unsupported_configuration",
                "An inline or dotted memories table needs a manual format adjustment before setup can preserve it safely.",
            )
            text = (
                text.rstrip() + "\n\n[memories]\ngenerate_memories = false\nuse_memories = false\n"
            )
        else:
            end = next(
                (i for i in range(start + 1, len(lines)) if lines[i].lstrip().startswith("[")),
                len(lines),
            )
            section = lines[start + 1 : end]
            for key in ("generate_memories", "use_memories"):
                matches = [i for i, line in enumerate(section) if re.match(rf"\s*{key}\s*=", line)]
                if matches:
                    section[matches[0]] = f"{key} = false\n"
                else:
                    section.append(f"{key} = false\n")
            text = "".join(lines[: start + 1] + section + lines[end:])
        tomllib.loads(text)
        atomic_write(path, text.encode())


def codex_hooks(home, path):
    command = shlex.quote(str(home.path / "bin" / "harness")) + " hook"
    with locked(home.path, str(path)):
        config = read_json(path, {})
        require(isinstance(config, dict), "invalid_integration", "Codex hooks must be an object.")
        hooks = config.setdefault("hooks", {})
        require(isinstance(hooks, dict), "invalid_integration", "Codex hooks needs an event map.")
        for event, timeout, status in (
            ("SessionStart", 10, "Harness: load session context"),
            ("PostToolUse", 5, "Harness: check pending messages"),
        ):
            groups = hooks.setdefault(event, [])
            require(
                isinstance(groups, list), "invalid_integration", f"{event} hooks must be a list."
            )
            owned = []
            for group in groups:
                require(
                    isinstance(group, dict) and isinstance(group.get("hooks"), list),
                    "invalid_integration",
                    f"{event} groups need a hooks list.",
                )
                for handler in group["hooks"]:
                    require(
                        isinstance(handler, dict),
                        "invalid_integration",
                        "Hook handlers must be objects.",
                    )
                    if handler.get("type") == "command" and handler.get("command") == command:
                        owned.append(handler)
            handler = {
                "type": "command",
                "command": command,
                "timeout": timeout,
                "statusMessage": status,
            }
            if owned:
                for existing in owned:
                    existing.update(handler)
            else:
                groups.append({"hooks": [handler]})
        write_json(path, config)
    return str(path)


def prepare(home, host=None, host_home=None, actor=None):
    operator_only(actor)
    home.ensure()
    with connect(home):
        pass
    launcher = home.path / "bin" / "harness"
    with locked(home.path, "launcher"):
        if launcher.exists():
            require(
                "# Harness managed launcher" in launcher.read_text(),
                "path_in_use",
                "The Harness launcher path contains an unowned file.",
            )
        text = "#!/bin/sh\n# Harness managed launcher\n"
        text += "export HARNESS_PYTHON=" + shlex.quote(sys.executable) + "\n"
        text += (
            'export HARNESS_ROOT="${HARNESS_ROOT:-'
            + str(home.path).replace('"', '\\"').replace("$", "\\$").replace("`", "\\`")
            + '}"\n'
        )
        text += "exec " + shlex.quote(str(PACKAGE_ROOT / "bin" / "harness")) + ' "$@"\n'
        atomic_write(launcher, text.encode(), 0o755)
    integrations = []
    hook_file = None
    if host:
        base = Path(host_home).expanduser().resolve() if host_home else Path.home()
        if host == "codex":
            hook_file = codex_hooks(home, base / ".codex" / "hooks.json")
            upsert_instructions(home, base / ".codex" / "AGENTS.md")
            codex_memory(home, base / ".codex" / "config.toml")
        elif host == "claude":
            upsert_instructions(home, base / ".claude" / "CLAUDE.md")
            path = base / ".claude" / "settings.json"
            with locked(home.path, str(path)):
                config = read_json(path, {})
                config["autoMemoryEnabled"] = False
                config.setdefault("attribution", {}).update(commit="", pr="")
                write_json(path, config)
        integrations.append(host)
    return {
        "root": str(home.path),
        "command": str(launcher),
        "integrations": integrations,
        "hook_file": hook_file,
        "hooks": "Native trust remains controlled by the host.",
    }


def doctor(home):
    return {
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "prepared": (home.path / "config.json").is_file(),
        "root": str(home.path),
        "providers": {
            name: {"available": shutil.which(name) is not None} for name in ("codex", "claude")
        },
        "scope": "Local macOS/Linux execution; provider authentication and hook trust are host prerequisites.",
    }
