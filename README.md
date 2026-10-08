# Harness

Harness keeps project context in external files and provides focused engineering workflows for agents on Codex and Claude Code. It combines predictable places for knowledge, plans and continuation with ten skills that load only when they serve the task. There are no lifecycle hooks, automatic context injection, mandatory task records or agent reservations.

## Skills

| Environment | Purpose |
| --- | --- |
| [environment](skills/environment/SKILL.md) | Locate, read and save the project's external context; set it up when needed |
| [close-work](skills/close-work/SKILL.md) | Preserve outputs and knowledge, then move completed work context to the trash (user-invoked) |

| Workflow | Purpose |
| --- | --- |
| [plan](skills/plan/SKILL.md) | Produce a modular macro plan |
| [implement](skills/implement/SKILL.md) | Implement changes and apply review corrections |
| [review](skills/review/SKILL.md) | Review an identified version for concrete defects |
| [handoff](skills/handoff/SKILL.md) | Transfer or assume work between agents or chats |
| [orchestrate](skills/orchestrate/SKILL.md) | Coordinate an explicitly requested team |
| [deliberate](skills/deliberate/SKILL.md) | Develop analyses and decisions through peer deliberation |
| [worktree](skills/worktree/SKILL.md) | Create, reuse or retire an isolated checkout and its branch |
| [commit-pr](skills/commit-pr/SKILL.md) | Prepare Conventional Commits and prose pull requests |

Skills are selected by the responsibility of the requested outcome or a necessary operation, without the user naming them, except `close-work`, which the user invokes because it moves files. Suboperations covered by the active skill need no separate skill: a worktree covers its branch, and planning inside authorized implementation returns to implementation. A planning-only request still stops at the plan. Conventions that must hold in every session, such as commit format, documentation boundaries and integration rules, live in the user's global instructions rather than in skills; see [host integration](skills/environment/references/host-integration.md) for the shared instruction file, the host sections and the settings checklist.

These are independent entry points, not a pipeline. A small solo correction can use implementation alone, or no skill at all. A large plan can be handed to an orchestrator; implementation and review fronts can share module specifications while using separate execution context. Workflows respect the user's testing, QA and delegation policies and the project's requirements.

## Project environments

A repository, including a monorepo and all its worktrees, is one project. A non-Git project can be an identified directory. Each project has one environment; different projects reference each other's context explicitly rather than sharing membership.

```text
environment/
  README.md
  knowledge/<subject>.md
  work/<work>/
    README.md
    modules/<module>.md
    team.md
    fronts/<front>/context.md
    fronts/<review-front>/findings.md
    handoffs/<recipient-scope>.md
  worktrees/<checkout>/
  trash/<work>-<timestamp>/
```

Create only the files the current work needs. When project context is unknown, locate the environment and read its short map, then follow relevant references. With a supplied continuation entry, start there. Reuse sufficient current context; discovery is neither a repository survey nor a reason to initialize empty storage.

Preserve decisions, useful investigation and continuation when losing the conversation would cause meaningful loss, without a separate save request. Reading knowledge needs no work record. Macro plans describe modular deliverables independently of agent trees and PR boundaries; a single table may suffice. Team and front files exist only when shared coordination or continuation needs them; short teams can use native messages and results alone. Messages carry pointers and instructions; files retain useful context, not authority to perform new actions.

Worktrees Harness creates default to the environment's `worktrees/` directory; worktrees the host manages are accepted where they are, and every checkout resolves to the same environment. Cooperating agents can alternate writes in one front; independent writing fronts use separate checkouts. Retiring a checkout is separate from closing a work item.

When the whole work is complete, consolidate durable knowledge and preserve retained deliverables with updated references, then close the work: the helper moves `work/<work>/` to `trash/` in one atomic rename, and the user purges the trash. Preserve anything still needed by active fronts, pending handoffs or other ongoing work. See the [file context contract](docs/file-context.md) for the canonical responsibilities and destinations.

Storage is currently local. The [remote storage boundary](docs/remote-storage.md) specifies requirements for a separate future file service; this release does not synchronize environments or expose an MCP service.

## Product documentation and internal context

Code and developer documentation must make sense without the agents' execution plan. Architecture, interfaces, development instructions and durable technical explanations belong in the repository when intended for its developers. Assignments, temporary module labels, attempts, continuation state and handoffs belong in the environment. Preserve useful technical detail while translating it into concepts meaningful to the reader.

## Install

For standalone skills in supported hosts:

```bash
pnpx skills add cekrauseee/harness --skill '*' -g -a codex claude-code -y
```

Use `.` for a local checkout. Each skill is self-contained. Native Codex and Claude plugin manifests are also included; choose one discovery route per host to avoid duplicates. See [installation](docs/install.md) for plugin setup, the global instruction layout and deliberate replacement of earlier versions.

The bundled helper uses Python 3.9+, Git and POSIX locking. It initializes only external project storage and accepts the current Harness format, with no legacy compatibility or automatic migration. Setup example:

```bash
python3 skills/environment/scripts/harness.py init --project /path/to/project
```

Read the [helper API](docs/helper-api.md) for command contracts, the [development guide](docs/development.md) for contribution checks and [host integration](skills/environment/references/host-integration.md) for the shared instruction file. Repository publication and installation do not modify user environments or host instructions by themselves.

[MIT license](LICENSE), Henrique Krause.
