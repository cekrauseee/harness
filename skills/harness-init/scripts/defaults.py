"""Versioned managed defaults shared by Harness initialization and hooks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable


DEFAULTS_VERSION = 1
CHARTER = """# Harness Charter

- Keep Harness state outside repositories.
- Use English for repository documentation and engineering metadata.
- Keep language simple, direct, coherent, and concise.
- Follow project standards for commits, branches, worktrees, pull requests, and reviews.
- Never promote automatic observations into durable memory without classification.
- Do not persist raw prompts, responses, transcripts, secrets, or routine tool output.
- Do not commit, push, publish, or remove work without user authorization.
- Report verification and uncertainty honestly.
"""
STANDARDS = {
    "commits.md": "# Commits\n\nUse Conventional Commits: `type(scope): imperative description`. Use English, lowercase types, and no final period.\n",
    "branches.md": "# Branches\n\nUse `type/short-kebab-case-description` with Conventional Commit types. Do not include an agent or person name.\n",
    "worktrees.md": "# Worktrees\n\nDerive the directory name from the branch as `type-short-description-<short-id>`. Git remains authoritative.\n",
    "pull-requests.md": "# Pull requests\n\nUse a Conventional Commit title in English. Describe Summary, Changes, Verification, and Risks from actual evidence.\n",
    "documentation.md": "# Documentation\n\nWrite canonical repository documentation in English with simple, direct, coherent, and concise language.\n",
    "reviews.md": "# Reviews\n\nReport only actionable findings with severity, evidence, impact, and a suggested direction. Review does not imply modification.\n",
    "continuity.md": "# Continuity\n\nFor material work, use the Harness session skill without asking the user to record a concise task, outcome, blocker, and next step. Capture expensive-to-rediscover observations as candidates with the Harness memory skill. Never copy raw prompts, responses, transcripts, secrets, or routine tool output.\n",
}
QUERY_ALIASES = {
    "artefato": ["artifact"], "artifacts": ["artefatos"],
    "autenticacao": ["authentication", "auth"], "authentication": ["autenticacao"],
    "commit": ["commits"], "documentacao": ["documentation", "docs"],
    "erro": ["error", "bug"], "memoria": ["memory"],
    "movel": ["mobile"], "projeto": ["project"],
    "revisao": ["review"], "worktree": ["worktrees"],
}
WORKSPACE_POLICY = {"managed_by": "harness", "max_age_days": 7, "schema_version": 1}
WORKTREE_POLICY = """root = "project-container"
directory_template = "{type}-{slug}-{short_id}"
branch_template = "{type}/{slug}"
agent_prefix = false
"""


def refresh_global(home: Path, write: Callable[[Path, str], None]) -> None:
    (home / "adapters").mkdir(parents=True, exist_ok=True)
    (home / "projects").mkdir(parents=True, exist_ok=True)
    (home / "standards").mkdir(parents=True, exist_ok=True)
    (home / "overrides/standards").mkdir(parents=True, exist_ok=True)
    try:
        current = json.loads((home / "managed.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        current = {}
    required = [home / "charter.md", *(home / "standards" / name for name in STANDARDS), home / "standards/query-aliases.json"]
    if current.get("defaults_version") == DEFAULTS_VERSION and all(path.is_file() for path in required):
        return
    write(home / "charter.md", CHARTER)
    for name, content in STANDARDS.items():
        write(home / "standards" / name, content)
    write(home / "standards/query-aliases.json", json.dumps(QUERY_ALIASES, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    write(home / "managed.json", json.dumps({"defaults_version": DEFAULTS_VERSION}, indent=2) + "\n")


def refresh_project(base: Path, write: Callable[[Path, str], None]) -> None:
    workspace = base / "workspace/policy.json"
    worktrees = base / "worktrees/policy.toml"
    try:
        current_workspace = json.loads(workspace.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        current_workspace = None
    if current_workspace != WORKSPACE_POLICY:
        write(workspace, json.dumps(WORKSPACE_POLICY, indent=2, sort_keys=True) + "\n")
    try:
        current_worktrees = worktrees.read_text(encoding="utf-8")
    except OSError:
        current_worktrees = ""
    if current_worktrees != WORKTREE_POLICY:
        write(worktrees, WORKTREE_POLICY)
