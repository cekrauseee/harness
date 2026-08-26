"""Versioned managed defaults shared by Harness initialization and hooks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable


DEFAULTS_VERSION = 5
CHARTER = """# Harness Charter

- Keep Harness state outside project directories.
- Treat project artifacts and documentation as canonical.
- Use the project's language and conventions unless the task requires otherwise.
- Keep language simple, direct, coherent, and concise.
- Never promote automatic observations into durable memory without classification.
- Do not persist raw prompts, responses, transcripts, secrets, or routine tool output.
- Do not publish, share, or remove work without user authorization.
- Report verification and uncertainty honestly.
"""
STANDARDS = {
    "commits.md": "# Commits\n\nUse English Conventional Commits: `type(scope): imperative description`. Use the Harness type vocabulary, lowercase types, and no final period. Classify each cohesive commit by its actual change.\n",
    "branches.md": "# Branches\n\nChoose the task's primary Conventional Commit type once. Use `type/short-kebab-case-description` for its branch. Never add an agent, host, person, or machine prefix such as `codex/` or `claude/`.\n",
    "worktrees.md": "# Worktrees\n\nUse the task's semantic `type/short-kebab-case-description` branch in an isolated checkout. Let the active host choose the physical path, directory name, storage root, and native bookkeeping while Harness controls branch naming, creation, validation, adoption, and retirement. Host-specific directory names must not alter the branch. Git remains authoritative.\n",
    "pull-requests.md": "# Pull requests\n\nUse an English Conventional Commit title whose primary type matches the head branch type. Describe Summary, Changes, Verification, and Risks from actual evidence. Do not publish a pull request from a host- or agent-prefixed branch.\n",
    "documentation.md": "# Documentation\n\nWrite canonical repository documentation in English with simple, direct, coherent, and concise language.\n",
    "reviews.md": "# Reviews\n\nReport only actionable findings with severity, evidence, impact, and a suggested direction. Review does not imply modification.\n",
    "continuity.md": "# Continuity\n\nFor material work that needs a handoff, use the Harness session skill without asking the user to record a concise title, summary, next step, and artifact references. Search Harness memory only when prior context can materially change the current work, then hydrate only selected records. Capture expensive-to-rediscover observations as candidates with the Harness memory skill. Never copy raw prompts, responses, transcripts, secrets, or routine tool output.\n",
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
WORKTREE_POLICY = """creation_protocol = "harness"
lifecycle = "harness"
path_provider = "host"
storage_provider = "host"
branch_template = "{type}/{slug}"
isolated_checkout = true
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
