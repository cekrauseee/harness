# Harness

Harness keeps project context in external files and provides focused engineering workflows for agents. It combines predictable places for plans, knowledge and worktrees with skills that load only when they serve the task. There are no lifecycle hooks, automatic context injection, mandatory task records or agent reservations.

## Skills

| Environment | Purpose |
| --- | --- |
| [environment-setup](skills/environment-setup/SKILL.md) | Bind one project and all its worktrees to an external environment |
| [environment-context](skills/environment-context/SKILL.md) | Retrieve missing knowledge or scoped continuation context |
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

These are independent process entry points, not a mandatory pipeline. A small solo correction can use implementation alone. A large plan can be handed to another orchestrator; implementation and review fronts can then share module specifications while using separate execution context. Integration is used only when the work requires it. Applying review findings is a mode of implementation, not an additional process.

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

Create only the files needed for the current work. Macro plans are always modular; modules describe deliverables independently of agent trees and PR boundaries. Executors start from their own front/module, not the whole environment. Temporary team configuration records logical roles and native host IDs when agents actually start. Messages carry pointers and instructions; files retain the context needed to continue.

All new worktrees belong under the environment's `worktrees/` directory. Cooperating agents can alternate writes in one front; independent writing fronts use separate checkouts. Retiring a checkout is separate from closing a work item.

When the whole work is complete, consolidate useful durable knowledge and remove its temporary material without an archive or receipt. Preserve anything still needed by active fronts, pending handoffs or other ongoing work. See the [file context contract](docs/file-context.md) for the canonical responsibilities and destinations.

## Product documentation and internal context

Code and developer documentation must make sense without the agents' execution plan. Architecture, interfaces, development instructions and durable technical explanations belong in the repository when intended for its developers. Assignments, temporary module labels, attempts, continuation state and handoffs belong in the environment. Preserve useful technical detail while translating it into concepts meaningful to the reader.

## Install

For standalone skills in supported hosts:

```bash
npx skills add cekrauseee/harness --skill '*' -g -a codex claude-code -y
```

Use `.` for a local checkout. Each skill is self-contained. Native Codex and Claude plugin manifests are also included; choose one discovery route per host to avoid duplicates. See [installation](docs/install.md) for plugin setup and deliberate replacement of existing installations.

The bundled helper uses Python 3.9+, Git and POSIX locking. It initializes only external project storage and accepts the current Harness format. It has no legacy compatibility or automatic migration. Setup example:

```bash
python3 skills/environment-setup/scripts/harness.py init --project /path/to/project
```

Read the [helper API](docs/helper-api.md) for command contracts, [development guide](docs/development.md) for contribution checks and [host integration](skills/environment-setup/references/host-integration.md) for requested instruction updates. Repository publication and installation do not modify user environments or host instructions by themselves.

[MIT license](LICENSE), Henrique Krause.
