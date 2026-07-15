#!/usr/bin/env python3
"""Initialize and resolve global Harness projects using only the standard library."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Iterator
import uuid

from defaults import refresh_global, refresh_project


SCHEMA_VERSION = 1


def harness_home() -> Path:
    return Path(os.environ.get("HARNESS_HOME", "~/.harness")).expanduser().resolve()


def utc_now() -> str:
    import datetime

    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def git(repo: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], text=True, capture_output=True, check=False
    )
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or "Git command failed")
    return result.stdout.strip()


def repo_root(path: str | Path) -> Path:
    candidate = Path(path).expanduser().resolve()
    root = git(candidate, "rev-parse", "--show-toplevel")
    if not root:
        raise RuntimeError(f"Not a Git repository: {candidate}")
    return Path(root).resolve()


def valid_project_id(value: str) -> str:
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise RuntimeError(f"Invalid Harness project id: {value}") from exc
    return str(parsed)


def atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temp_name)


def write_json(path: Path, value: object) -> None:
    atomic_write(path, json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


@contextlib.contextmanager
def lock(path: Path, timeout: float = 5.0) -> Iterator[None]:
    deadline = time.monotonic() + timeout
    while True:
        try:
            path.mkdir(parents=True)
            atomic_write(path / "owner", f"{os.getpid()} {time.time()}\n")
            break
        except FileExistsError:
            try:
                if time.time() - path.stat().st_mtime > 300:
                    for child in path.iterdir():
                        child.unlink()
                    path.rmdir()
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise RuntimeError(f"Timed out waiting for Harness lock: {path}")
            time.sleep(0.05)
    try:
        yield
    finally:
        with contextlib.suppress(FileNotFoundError):
            for child in path.iterdir():
                child.unlink()
            path.rmdir()


def remotes(repo: Path) -> list[str]:
    values: list[str] = []
    for name in git(repo, "remote", check=False).splitlines():
        value = git(repo, "remote", "get-url", name, check=False)
        if value:
            values.append(value)
    return sorted(set(values))


def project_dir(project_id: str) -> Path:
    return harness_home() / "projects" / valid_project_id(project_id)


def seed(path: Path, content: str) -> None:
    if not path.exists():
        atomic_write(path, content.rstrip() + "\n")


def make_global_layout(home: Path) -> None:
    refresh_global(home, atomic_write)


def make_layout(base: Path) -> None:
    for relative in (
        "memory/candidates",
        "memory/topics",
        "memory/archive",
        "sessions/active",
        "sessions/closed",
        "references/product",
        "references/technical",
        "references/operations",
        "references/investigations",
        "workspace",
        "worktrees",
    ):
        (base / relative).mkdir(parents=True, exist_ok=True)
    catalog = base / "memory/catalog.jsonl"
    if not catalog.exists():
        atomic_write(catalog, "")
    seed(base / "index.md", """# Harness project

Read `project.md` for orientation and `decisions.md` for current decisions. Read topic memory, references, and active sessions only when relevant to the task. Treat repository documentation as canonical.
""")
    seed(base / "project.md", "# Project\n\nRecord concise, agent-facing project orientation here.\n")
    seed(base / "decisions.md", "# Decisions\n\nRecord current provisional decisions here. Promote stable decisions to repository documentation.\n")
    refresh_project(base, atomic_write)


def read_manifest(base: Path) -> dict:
    try:
        return json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Missing or invalid Harness manifest: {base}") from exc


def current_id(repo: Path) -> str | None:
    value = git(repo, "config", "--local", "--get", "harness.project-id", check=False)
    return valid_project_id(value) if value else None


def init_project(repo: Path, name: str | None = None) -> tuple[dict, bool]:
    home = harness_home()
    home.mkdir(parents=True, exist_ok=True)
    with lock(home / ".lock"):
        make_global_layout(home)
        existing = current_id(repo)
        if existing:
            base = project_dir(existing)
            manifest = read_manifest(base)
            make_layout(base)
            return manifest, False

        project_id = str(uuid.uuid4())
        base = project_dir(project_id)
        make_layout(base)
        manifest = {
            "created_at": utc_now(),
            "display_name": name or repo.name,
            "id": project_id,
            "remote_urls": remotes(repo),
            "repository_paths": [str(repo)],
            "schema_version": SCHEMA_VERSION,
            "updated_at": utc_now(),
        }
        write_json(base / "manifest.json", manifest)
        git(repo, "config", "--local", "harness.project-id", project_id)
        return manifest, True


def install_lifecycle_hooks() -> dict:
    """Install host hooks by default while keeping an explicit test/repair escape hatch."""
    if os.environ.get("HARNESS_SKIP_HOOK_INSTALL") == "1":
        return {"skipped": True}
    script = Path(__file__).resolve()
    plugin_roots = [os.environ.get("PLUGIN_ROOT"), os.environ.get("CLAUDE_PLUGIN_ROOT")]
    if any(root and script.is_relative_to(Path(root).expanduser().resolve()) for root in plugin_roots):
        return {"skipped": True, "reason": "plugin-bundled hooks are active"}
    path_text = str(script)
    if "/plugins/cache/" in path_text or "/.claude/plugins/" in path_text:
        return {"skipped": True, "reason": "plugin-bundled hooks are active"}
    installer = Path(__file__).resolve().with_name("install_hooks.py")
    result = subprocess.run(
        [sys.executable, str(installer), "--json"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        return {"installed": False, "warning": result.stderr.strip() or "Hook installation failed"}
    try:
        return {"installed": True, **json.loads(result.stdout)}
    except json.JSONDecodeError:
        return {"installed": False, "warning": "Hook installer returned invalid JSON"}


def link_project(repo: Path, project_id: str) -> dict:
    base = project_dir(project_id)
    home = harness_home()
    with lock(home / ".lock"):
        make_global_layout(home)
        manifest = read_manifest(base)
        paths = sorted(set(manifest.get("repository_paths", [])) | {str(repo)})
        manifest["repository_paths"] = paths
        manifest["remote_urls"] = sorted(set(manifest.get("remote_urls", [])) | set(remotes(repo)))
        manifest["updated_at"] = utc_now()
        write_json(base / "manifest.json", manifest)
        git(repo, "config", "--local", "harness.project-id", valid_project_id(project_id))
    return manifest


def emit(value: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, sort_keys=True, ensure_ascii=False))
    else:
        for key in sorted(value):
            print(f"{key}: {value[key]}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p_init = sub.add_parser("init")
    p_init.add_argument("--repo", default=".")
    p_init.add_argument("--name")
    p_init.add_argument("--json", action="store_true")
    p_link = sub.add_parser("link")
    p_link.add_argument("--repo", default=".")
    p_link.add_argument("--project-id", required=True)
    p_link.add_argument("--json", action="store_true")
    p_resolve = sub.add_parser("resolve")
    p_resolve.add_argument("--repo", default=".")
    p_resolve.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        repo = repo_root(args.repo)
        if args.command == "init":
            manifest, created = init_project(repo, args.name)
            emit({
                "created": created,
                "hooks": install_lifecycle_hooks(),
                "project": manifest,
                "project_dir": str(project_dir(manifest["id"])),
            }, args.json)
        elif args.command == "link":
            manifest = link_project(repo, args.project_id)
            emit({"linked": True, "project": manifest, "project_dir": str(project_dir(manifest["id"]))}, args.json)
        else:
            project_id = current_id(repo)
            if not project_id:
                raise RuntimeError("Repository is not linked to Harness")
            manifest = read_manifest(project_dir(project_id))
            emit({"project": manifest, "project_dir": str(project_dir(project_id))}, args.json)
        return 0
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
