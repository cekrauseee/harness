# Continuity

Continuity keeps useful knowledge and needed continuations in external local files. Agents retrieve only the context their task needs and coordinate shared writes through a small atomic helper.

| Skill | Use |
| --- | --- |
| [continuity-init](skills/continuity-init/SKILL.md) | Create an environment, bind projects or update host integration |
| [continuity-recall](skills/continuity-recall/SKILL.md) | Retrieve missing knowledge or a specific continuation |
| [continuity-remember](skills/continuity-remember/SKILL.md) | Retain durable guidance or correct reusable knowledge |
| [continuity-task](skills/continuity-task/SKILL.md) | Reserve shared writes and manage contributions |

## Environments

An **environment** is a named continuity scope containing one or more project folders or repositories. Its members share knowledge and contributions. For example, one environment can group Continuity and Workflows; another can group a portfolio and notes. It stores continuity state, not an execution sandbox or an archive of agent activity.

A **workspace** identifies one bound project folder or checkout. Git worktrees of a member repository resolve to the same environment while retaining distinct workspace identities. Each project belongs to one environment. Membership is explicit; similar repository URLs do not join projects.

From this checkout, create a shared environment in one atomic operation:

```bash
python3 skills/continuity-init/scripts/continuity.py init --name agent-tools \
  --project /work/continuity --project /work/workflows
```

Repeat `--project` for each member. Initialization reuses an existing common environment and can add unbound projects to it. Repeating the same group is a no-op. If members already belong to different environments, initialization fails without changing them; it does not merge their knowledge or contributions. `--name` names a newly created environment.

Use the returned ID to inspect all members or explicitly bind another project:

```bash
python3 skills/continuity-init/scripts/continuity.py resolve --environment-id <id>
python3 skills/continuity-init/scripts/continuity.py bind --environment-id <id> --project /work/notes
```

`resolve --project /work/workflows` selects that project's environment and workspace. The environment stores one `environment.json`, shared `knowledge/` and optional reference assets under `${CONTINUITY_HOME:-~/.continuity}/environments/<id>/`. Knowledge can describe one project or a cross-project decision; make that scope explicit in the note. Shared storage does not require reading every project's context.

Contributions retain their originating workspace. They can reserve files across projects using absolute paths; relative paths and `.` refer only to the selected workspace. Conflicting claims are checked across all environments. Completion removes the contribution atomically; genuine pending work retains a handoff. Reservations are cooperative and do not expire by age.

## Install and integration

```bash
npx skills add cekrauseee/harness --skill '*' -g -a codex -a claude-code -y
```

The source repository URL remains `cekrauseee/harness`; the package and skill names are Continuity. Use `.` for a local checkout. Each skill includes its own generated helper and works independently. Python 3.10+ and Git are required, with POSIX locking on macOS and Linux.

[Workflows](https://github.com/cekrauseee/workflows) remains optional and owns execution procedures. Continuity owns environment membership, knowledge and cooperative ownership. See [host integration](skills/continuity-init/references/host-integration.md) for routing; the host owns tools and execution permissions.

Existing Harness installations and `~/.harness` data are not modified by these source changes. Replacing installed skills and moving existing knowledge into the environment layout are separate, deliberate operations. The runtime accepts only the current layout; it has no legacy aliases, automatic migration or background maintenance. Repository URLs and live host configuration are unchanged by the rebranding in this checkout.

See [helper contracts](docs/kernel-api.md), [development](docs/development.md) and [contributor guidance](AGENTS.md). The Codex and Claude manifests share a package version; instruction-only changes need not change the helper version.

[MIT license](LICENSE), Henrique Krause.
