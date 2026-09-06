#!/usr/bin/env python3
"""Opt-in skills.sh packaging checks; every installation uses a disposable home."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(command, cwd, env):
    result = subprocess.run(command, cwd=cwd, env=env, text=True,
                            capture_output=True, timeout=60)
    if result.returncode:
        raise RuntimeError(f"{command}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def files(directory):
    return {path.relative_to(directory): path.read_bytes()
            for path in directory.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts}


def check_install(package, skill, copy_mode, command, env):
    with tempfile.TemporaryDirectory(prefix="skills-install-check-") as temporary:
        root = Path(temporary).resolve()
        source, home, project = root / "source", root / "home", root / "project"
        home.mkdir()
        project.mkdir()
        # Select from the whole package so a broken --skill filter cannot pass.
        shutil.copytree(package / "skills", source / "skills",
                        ignore=shutil.ignore_patterns("__pycache__"))
        child = dict(env, HOME=str(home), CODEX_HOME=str(home / ".codex"),
                     CLAUDE_CONFIG_DIR=str(home / ".claude"), XDG_CONFIG_HOME=str(home / ".config"),
                     HARNESS_HOME=str(root / "state"), PYTHONPATH="", CI="1")
        install = command + ["add", str(source), "--skill", skill.name,
                             "-g", "-a", "codex", "claude-code", "-y"]
        if copy_mode:
            install.append("--copy")
        run(install, project, child)
        shutil.rmtree(source)

        expected = files(skill)
        canonical = home / ".agents" / "skills" / skill.name
        claude = home / ".claude" / "skills" / skill.name
        for target in (canonical, claude):
            assert {path.name for path in target.parent.iterdir()} == {skill.name}, target.parent
            assert files(target) == expected, f"Installed payload differs: {target}"
        assert claude.is_symlink() == (not copy_mode), claude
        if not copy_mode:
            assert claude.resolve() == canonical.resolve(), claude

        helper = canonical / "scripts" / "harness.py"
        if helper.is_file():
            # Payload equality covers every helper copy; one operation proves it runs alone.
            identity = json.loads(run([sys.executable, str(helper), "init", "--project", str(project)],
                                      project, child))
            assert (root / "state" / "projects" / identity["project_id"] / "project.json").is_file()
        assert not list(project.iterdir()), "Installation or initialization wrote into the project"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflows", type=Path, help="Optional Workflows checkout to verify too")
    parser.add_argument("--cli", type=Path, help="Existing skills bin/cli.mjs")
    args = parser.parse_args()
    env = dict(os.environ, DISABLE_TELEMETRY="1", NO_COLOR="1")
    cli = args.cli or Path(run(["npx", "--yes", "--package", "skills@1.5.23", "--", "which", "skills"],
                              ROOT, env).strip().splitlines()[-1]).resolve()
    command = [shutil.which("node") or "node", str(cli)]
    print("skills CLI " + run(command + ["--version"], ROOT, env).strip(), flush=True)
    packages = [ROOT] + ([args.workflows.resolve()] if args.workflows else [])
    count = 0
    for package in packages:
        skills = sorted(path.parent for path in (package / "skills").glob("*/SKILL.md"))
        if not skills:
            raise RuntimeError(f"No skills found in {package}")
        for skill in skills:
            for copy_mode in (False, True):
                check_install(package, skill, copy_mode, command, env)
                count += 1
                mode = "copy" if copy_mode else "symlink"
                print(f"{package.name}/{skill.name}: {mode} passed", flush=True)
    print(f"{count} isolated selective installations passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
