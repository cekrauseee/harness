# Harness

Harness is a file-native continuity and engineering behavior layer for coding agents. It gives Codex, Claude Code, and other skill-compatible hosts a shared way to recover project context, manage concise handoffs, produce canonical documentation, and follow consistent Git and review conventions.

Harness is not an application, daemon, database, deployment tool, or product framework. Its non-versioned state lives outside repositories. Only canonical developer documentation and user-facing documentation artifacts are written to a project, and only when the task requires them.

## Install

Install every skill globally for Codex and Claude Code:

```bash
npx skills add cekrauseee/harness --skill '*' -g -a codex -a claude-code -y
```

List the available skills without installing them:

```bash
npx skills add cekrauseee/harness --list
```

The `skills.sh` installer copies skills but does not execute lifecycle hooks. `harness-init` installs supported host adapters idempotently on first project initialization. Full plugin installations can discover the bundled hook configuration directly.

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
      references/
      sessions/
      workspace/
      worktrees/
```

A Git repository stores only a local, non-versioned project identifier in Git configuration. Harness adds no state files to the checkout. Linked worktrees resolve the same project identifier and global container.

Lifecycle adapters automate the normal flow:

- session start or resume resolves the project and recalls scoped context;
- each user prompt recalls only task-relevant memory and handoffs;
- the injected continuity rule makes the agent maintain concise structured handoffs without asking the user;
- pre-compact and stop hooks flush timestamps and any structured state already supplied by the agent;
- a compacted session starts again with the minimum required context;
- stop updates session continuity without persisting raw host messages; explicit structured summaries may become memory candidates;
- explicit skills remain available for recovery, inspection, and exceptional maintenance.

Native host memory is optional. Harness is designed so a fresh task can recover project continuity with host memory disabled.

Managed defaults refresh by schema version. Machine-local overrides live under `~/.harness/overrides/`; workspace cleanup overrides use `workspace/policy.local.json`.

## Engineering standards

Harness uses Conventional Commits for commits and pull request titles. Branch and worktree names extend the same vocabulary:

```text
commit:  docs(harness): document artifact routing
branch:  docs/artifact-routing
worktree: docs-artifact-routing-a31f
```

Repository-facing documentation is always English, simple, objective, coherent, concise, and factual. Reviews contain only evidence-backed, actionable findings classified from `P0` through `P3`.

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
| `harness-worktree` | Resolve conventional branch and worktree names and locations. |
| `harness-commit` | Organize authorized changes into Conventional Commits. |
| `harness-pr` | Draft or publish conventional pull requests. |
| `harness-review` | Report evidence-backed findings with calibrated severity. |
| `harness-docs-init` | Create the canonical English documentation baseline. |
| `harness-docs-maintain` | Maintain concise canonical documentation. |
| `harness-docs-audit` | Check documentation routing, links, size, and drift. |
| `harness-artifact` | Create and index neutral user-facing HTML visualizations. |

See [the documentation index](docs/index.md) for architecture, standards, development, privacy, and lifecycle details.

## Security and privacy

Harness state can outlive a local clone. Do not store secrets, credentials, raw transcripts, routine command output, or hidden reasoning. Memory candidates require classification before they become durable context. Workspace files are excluded from recall and cleaned by policy.

## License

[MIT](LICENSE)
