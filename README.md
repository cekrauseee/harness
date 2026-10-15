# Harness

Harness keeps project context in external files and provides focused engineering workflows for agents on Codex and Claude Code. It combines predictable places for knowledge, plans and continuation with eleven skills that load only when they serve the task. Orchestrations also leave execution records, from which a change map is built for review and shown in a local viewer. There are no lifecycle hooks, automatic context injection or agent reservations, and solo work needs no records.

This repository holds three parts: the plugin (the skills and their bundled Python scripts), the file contract they write (the environment layout and versioned JSON formats) and local applications that read those files, starting with the change map viewer. [Architecture](docs/architecture.md) describes the layout, the boundaries between the parts and where Harness is heading.

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
| [map](skills/map/SKILL.md) | Consolidate execution records into a change map for review and QA |

Skills are selected by the responsibility of the requested outcome or a necessary operation, without the user naming them, except `close-work`, which the user invokes because it moves files. Suboperations covered by the active skill need no separate skill: a worktree covers its branch, and planning inside authorized implementation returns to implementation. A planning-only request still stops at the plan. Conventions that must hold in every session, such as commit format, documentation boundaries and integration rules, live in the user's global instructions rather than in skills; see [host integration](docs/host-integration.md) for the shared instruction file, the host sections and the settings checklist.

These are independent entry points, not a pipeline. A small solo correction can use implementation alone, or no skill at all. A large plan can be handed to an orchestrator; implementation and review fronts can share module specifications while using separate execution context. Workflows respect the user's testing, QA and delegation policies and the project's requirements.

## Project environments

A repository, including a monorepo and all its worktrees, is one project. A non-Git project can be an identified directory. Each project has one environment; different projects reference each other's context explicitly rather than sharing membership.

```text
environment/
  README.md                   short map of knowledge and ongoing work
  knowledge/<subject>.md      confirmed durable knowledge
  work/<work>/                plan, modules, team, fronts, records, handoffs and change map, only while needed
  worktrees/<checkout>/       checkouts Harness creates
  trash/<work>-<timestamp>/   closed work, until the user purges it
```

Create only the files the current work needs. When project context is unknown, locate the environment and read its short map, then follow relevant references. With a supplied continuation entry, start there. Reuse sufficient current context; discovery is neither a repository survey nor a reason to initialize empty storage.

Preserve decisions, useful investigation and continuation when losing the conversation would cause meaningful loss, without a separate save request. Reading knowledge needs no work record. Macro plans describe modular deliverables independently of agent trees and PR boundaries; a single table may suffice. Team and front files exist only when shared coordination or continuation needs them; short teams can use native messages and results alone. Messages carry pointers and instructions; files retain useful context, not authority to perform new actions.

Worktrees Harness creates default to the environment's `worktrees/` directory; worktrees the host manages are accepted where they are, and every checkout resolves to the same environment. Cooperating agents can alternate writes in one front; independent writing fronts use separate checkouts. Retiring a checkout is separate from closing a work item.

When the whole work is complete, consolidate durable knowledge and preserve retained deliverables with updated references, then close the work: the helper moves `work/<work>/` to `trash/` in one atomic rename, and the user purges the trash. Preserve anything still needed by active fronts, pending handoffs or other ongoing work. See the [file context contract](docs/file-context.md) for the layout inside a work item, the canonical responsibilities and destinations, and [execution records](docs/records.md) for attention points, run records, events and the change map.

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

Viewing a change map uses the [local viewer](apps/viewer/README.md) from a checkout of this repository; it needs Node and pnpm and is not installed with the skills, and the map data stays valid without it. Repository publication and installation do not modify user environments or host instructions by themselves.

## Documentation

| Topic | Documents |
| --- | --- |
| Using Harness | [Installation](docs/install.md), [host integration](docs/host-integration.md) |
| Reference | [File context](docs/file-context.md), [execution records](docs/records.md), [helper API](docs/helper-api.md), JSON Schemas in [`schema/`](schema) |
| Design | [Architecture](docs/architecture.md), [remote storage boundary](docs/remote-storage.md) |
| Contributing | [Contributor guidance](AGENTS.md), [development](docs/development.md), [behavior validation](docs/behavior-validation.md), [viewer](apps/viewer/README.md) |

[MIT license](LICENSE), Henrique Krause.
