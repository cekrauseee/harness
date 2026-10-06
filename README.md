# Harness

Harness keeps project context in external files and provides focused engineering workflows for agents. It combines predictable places for plans, knowledge and worktrees with skills that load only when they serve the task. There are no lifecycle hooks, automatic context injection, mandatory task records or agent reservations.

## Skills

| Environment | Purpose |
| --- | --- |
| [environment-setup](skills/environment-setup/SKILL.md) | Bind one project and all its worktrees to an external environment |
| [environment-context](skills/environment-context/SKILL.md) | Discover applicable constraints, retrieve missing knowledge or resume scoped work |
| [environment-knowledge](skills/environment-knowledge/SKILL.md) | Preserve and correct confirmed durable internal knowledge |
| [environment-close-work](skills/environment-close-work/SKILL.md) | Consolidate useful knowledge and remove completed work context |

| Workflow | Purpose |
| --- | --- |
| [workflows-plan](skills/workflows-plan/SKILL.md) | Produce a modular macro plan |
| [workflows-handoff](skills/workflows-handoff/SKILL.md) | Prepare or assume a transfer to another agent or chat |
| [workflows-orchestrate](skills/workflows-orchestrate/SKILL.md) | Configure and coordinate authorized agent work |
| [workflows-implement](skills/workflows-implement/SKILL.md) | Implement changes and directed corrections |
| [workflows-review](skills/workflows-review/SKILL.md) | Review an identified version for concrete defects |
| [workflows-document](skills/workflows-document/SKILL.md) | Create, update, simplify and consolidate project documentation |
| [workflows-integrate](skills/workflows-integrate/SKILL.md) | Merge, rebase and resolve conflicts when integration is needed |
| [workflows-branch](skills/workflows-branch/SKILL.md) | Prepare a branch named for the intended change |
| [workflows-worktree](skills/workflows-worktree/SKILL.md) | Create, reuse or retire a checkout inside the environment |
| [workflows-commit](skills/workflows-commit/SKILL.md) | Prepare cohesive Conventional Commits |
| [workflows-pr](skills/workflows-pr/SKILL.md) | Describe and publish the requested macro change for review |

Select a skill by the responsibility of the requested outcome or a distinct necessary operation, without requiring the user to name it. Read its current instructions or reuse them when already available. Suboperations fully covered by the active skill do not require separate workflows: creating a worktree can cover its branch setup, and finishing a plan within authorized implementation returns to implementation. A planning-only request still stops at the plan.

These are independent process entry points, not a mandatory pipeline. A small solo correction can use implementation alone. A large plan can be handed to another orchestrator; implementation and review fronts can then share module specifications while using separate execution context. Integration is used only when the work requires it. Applying review findings is a mode of implementation, not an additional process. Workflows respect the user's testing, QA and delegation policies and project requirements; they do not prescribe tests for every edit or audit every delivery again.

## Project environments

A repository, including a monorepo and all its worktrees, is one project. A non-Git project can be an identified directory. Each project has one environment; different projects reference each other's context explicitly rather than sharing membership.

```text
environment/
  README.md
  knowledge/<subject>.md
  worktrees/<checkout>/
  work/<work>/
    README.md
    modules/<module>.md
    team.md
    fronts/<front>/context.md
    fronts/<review-front>/findings.md
    handoffs/<recipient-scope>.md
```

Create only the files needed for the current work. When project context is unknown, locate the existing environment and inspect its short map, then follow relevant references. With a supplied continuation entry, start there. Reuse sufficient current context; discovery is neither a repository survey nor a reason to initialize empty storage.

Preserve decisions, useful investigation and continuation when losing the conversation would cause meaningful loss, without requiring a separate save request. Reading knowledge does not require a work record. Macro plans describe modular deliverables independently of agent trees and PR boundaries; a single table may suffice. Team/front files exist only when shared coordination or continuation needs them. Short teams can use native messages and results alone. Messages carry pointers and instructions; files retain useful context, not authority to perform new actions.

All new worktrees belong under the environment's `worktrees/` directory. Cooperating agents can alternate writes in one front; independent writing fronts use separate checkouts. Retiring a checkout is separate from closing a work item.

When the whole work is complete, consolidate useful durable knowledge and preserve retained deliverables before removing temporary material without an archive or receipt. Inspect all file types, including HTML outputs, and update consumer references to durable destinations outside the closing subtree. Preserve anything still needed by active fronts, pending handoffs or other ongoing work. See the [file context contract](docs/file-context.md) for the canonical responsibilities and destinations.

Storage is currently local. The [remote storage boundary](docs/remote-storage.md) specifies requirements for a separate future file service; this release does not synchronize environments or expose an MCP service.

## Product documentation and internal context

Code and developer documentation must make sense without the agents' execution plan. Architecture, interfaces, development instructions and durable technical explanations belong in the repository when intended for its developers. Assignments, temporary module labels, attempts, continuation state and handoffs belong in the environment. Preserve useful technical detail while translating it into concepts meaningful to the reader.

## Install

For standalone skills in supported hosts:

```bash
pnpx skills add cekrauseee/harness --skill '*' -g -a codex claude-code -y
```

Use `.` for a local checkout. Each skill is self-contained. Native Codex and Claude plugin manifests are also included; choose one discovery route per host to avoid duplicates. See [installation](docs/install.md) for plugin setup and deliberate replacement of existing installations.

The bundled helper uses Python 3.9+, Git and POSIX locking. It initializes only external project storage and accepts the current Harness format. It has no legacy compatibility or automatic migration. Setup example:

```bash
python3 skills/environment-setup/scripts/harness.py init --project /path/to/project
```

Read the [helper API](docs/helper-api.md) for command contracts, [development guide](docs/development.md) for contribution checks and [host integration](skills/environment-setup/references/host-integration.md) for requested instruction updates. Repository publication and installation do not modify user environments or host instructions by themselves.

[MIT license](LICENSE), Henrique Krause.
