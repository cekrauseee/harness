# Harness

Harness is a lean, file-native continuity and orchestration layer for agents. It gives Codex, Claude Code, and other skill-compatible hosts a shared way to identify local projects, find only relevant stored context, maintain concise handoffs, and coordinate bounded multi-agent work. Harness works with coding and non-coding projects. Git, engineering conventions, developer documentation, and HTML artifacts remain available when the task needs them, but they are not requirements for project continuity.

## Install

Install every skill globally for Codex and Claude Code:

```bash
npx skills add cekrauseee/harness --skill '*' -g -a codex -a claude-code -y
```

List the available skills without installing them:

```bash
npx skills add cekrauseee/harness --list
```

The `skills.sh` installer copies skills. Host adapters are opt-in and silent: install them only through the explicit adapter command when maintenance hooks are wanted. They do not inject project memory or create a work session for every conversation.

## Operating model

Harness stores machine-local state under `${HARNESS_HOME:-~/.harness}`:

```text
~/.harness/
  charter.md
  managed.json
  standards/
  overrides/
  projects/
    <project-uuid>/
      manifest.json
      index.md
      decisions.md
      memory/
        catalog.jsonl
      references/
      sessions/
      workspace/
      worktrees/
        policy.toml
```

Each project has a stable UUID and one or more machine-local bindings. A registered path is sufficient; Git identity and host project IDs are optional bindings. Harness writes no identity marker or state into the project.

Agents pull context in two stages:

1. Search a compact semantic catalog by title, summary, read rule, tags, status, and recency.
2. Hydrate only the selected memory or session under an explicit context budget.

An empty or weak search returns no context. IDs remain stable internal handles, while agents select records through semantic cards. Large records stay discoverable because their compact cards are indexed separately from full content. Sessions are episodic handoffs, not automatic transcripts. Agents create one only when material work may need continuation, update it with current outcomes and next actions, and mark it dormant or closed when appropriate. Native host memory and lifecycle hooks are optional. Hooks remain disabled until explicitly installed. A fresh task can recover continuity through the agent-facing Harness skills alone.

## Bounded orchestration

When delegation is already appropriate, `harness-orchestrate` turns the work into a small dependency graph. The root agent only coordinates. It is the sole spawn authority; child agents do not delegate, graph depth stays at one, and every writable artifact has one owner at a time.

Each node receives a minimal context packet and explicit limits for nodes, waves, retries, review cycles, context, output, and reasoning effort. Reviewers and verifiers are read-only. Fixers run only for accepted findings, and the graph stops as soon as acceptance evidence is complete.

Managed defaults refresh by schema version. Machine-local overrides live under `~/.harness/overrides/`; workspace cleanup overrides use `workspace/policy.local.json`.

## On-demand engineering

Harness uses Conventional Commits for commits and pull request titles. Task branches extend the same vocabulary while worktree paths and storage stay host-native:

```text
branch:       docs/artifact-routing
commit:       docs(harness): document artifact routing
pull request: docs(harness): document artifact routing
checkout:     isolated, host-stored, Harness-managed
```

The branch and pull request share the task's primary type. Each cohesive commit classifies its actual change with the same vocabulary. Host-specific worktree directory names never become Git branch prefixes.

Pull request bodies package Goal, Desired behavior, Change map, Verification, Review focus, and Risks into a bounded reviewer context. Reviewers use that contract to order inspection, verify the complete diff, and load broader repository context only when dependency or risk boundaries require it.

These conventions load only for relevant engineering work. Repository-facing documentation is English, simple, objective, coherent, concise, and factual. Reviews contain only evidence-backed, actionable findings classified from `P0` through `P3`.

## Documentation and artifacts

Stable project knowledge belongs in versioned documentation:

```text
README.md
docs/
  index.md
  project.md
  architecture.md
  development.md
  modules/
  artifacts/
    index.md
    <slug>.html
```

Artifacts are static, self-contained HTML visualizations for users. They use a neutral Harness presentation, never infer the product's visual identity, and require no framework, build, backend, or external dependency. Drafts may use the temporary Harness workspace; final artifacts are versioned under `docs/artifacts/`.

## Skills

| Skill | Purpose |
| --- | --- |
| `harness-init` | Initialize, link, and resolve global Harness state and adapters. |
| `harness-recall` | Build a task-scoped context packet under a fixed budget. |
| `harness-remember` | Capture and consolidate project memory. |
| `harness-session` | Maintain concise continuation and handoff state. |
| `harness-audit` | Check identity, memory, sessions, cleanup, and repository boundaries. |
| `harness-orchestrate` | Coordinate bounded, depth-one multi-agent work graphs. |
| `harness-worktree` | Control creation and lifecycle while using host-selected worktree storage. |
| `harness-commit` | Organize authorized changes into Conventional Commits. |
| `harness-pr` | Draft reviewer-ready pull request context contracts. |
| `harness-review` | Route focused review and report evidence-backed findings. |
| `harness-docs-init` | Create the canonical English documentation baseline. |
| `harness-docs-maintain` | Maintain concise canonical documentation. |
| `harness-docs-audit` | Check documentation routing, links, size, and drift. |
| `harness-artifact` | Create and index neutral user-facing HTML visualizations. |

See [the documentation index](docs/index.md) for architecture, standards, development, privacy, and lifecycle details.

## Security and privacy

Harness state can outlive a local project path. Do not store secrets, credentials, raw transcripts, routine command output, or hidden reasoning. Memory candidates require classification before they become durable context. Workspace files are excluded from recall and cleaned by policy.

## License

[MIT](LICENSE)
