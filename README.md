# Harness

Harness keeps project knowledge and needed continuations in external local files. Agents retrieve information when the task needs it, curate useful knowledge and coordinate shared writes. A single Python helper provides atomic identity, ownership and protected Markdown updates.

| Skill | Use |
| --- | --- |
| [harness-init](skills/harness-init/SKILL.md) | Set up storage, bind a project or update host integration |
| [harness-recall](skills/harness-recall/SKILL.md) | Retrieve missing prior knowledge or a specific continuation |
| [harness-remember](skills/harness-remember/SKILL.md) | Retain durable guidance or correct reusable knowledge |
| [harness-task](skills/harness-task/SKILL.md) | Reserve shared writes and manage needed contributions |

## Install and use

```bash
npx skills add cekrauseee/harness --skill '*' -g -a codex -a claude-code -y
```

Choose the skills and hosts you need. Every skill includes its own generated helper and works when installed alone. Python 3.10+ and Git are required; locking uses POSIX facilities on macOS and Linux. Select one installation route per host to avoid duplicate discovery. Package updates and host instruction changes require updating the actual installation separately from this source checkout.

Use [host integration](skills/harness-init/references/host-integration.md) to configure task-specific triggers. [Workflows](https://github.com/cekrauseee/workflows) is an independent, optional package for engineering procedures. Neither package requires loading the other for every task.

## Design

Knowledge is ordinary Markdown under `${HARNESS_HOME:-~/.harness}/projects/<id>/knowledge/`. Agents search it with existing tools. `guidelines.md` can retain contextual user-confirmed guidance; rules needed for every task belong in applicable host or repository instructions.

One `project.json` holds identity and current contributions. Git worktrees share identity through the physical common Git directory. A contribution reserves paths and may carry one handoff. Atomic operations protect against races and partial writes; agents decide relevance, authorization and completion.

Completed contributions can be removed atomically after the result and useful knowledge are settled. A genuine continuation retains a handoff. Reservations are cooperative and do not expire by age. There are no hooks, execution histories, model calls or background cleanup processes. State stays outside target repositories.

See [helper contracts](docs/kernel-api.md) for operations and [development](docs/development.md) for proportional verification. The Codex and Claude manifests share a package version; instruction-only changes do not require changing the helper version. [Contributor guidance](AGENTS.md) defines repository conventions.

[MIT license](LICENSE), Henrique Krause.
