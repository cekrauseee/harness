# Harness

Harness gives agents shared project continuity in local files: identity, relevant knowledge, tasks, contributions and checkpoints. Several chats can work in the same folder and a new participant can discover their results and pending work without reading their conversations. Code, research, writing and planning projects are supported. Git is optional.

Operational state stays under `${HARNESS_HOME:-~/.harness}`, outside the project. Worktrees share project knowledge while retaining separate workspace provenance. The host remains responsible for execution, tools, permissions, models and delegation. Git delivery and documentation workflows belong to the separate [Workflows](https://github.com/cekrauseee/workflows) plugin.

## Install

Requirements: Python 3.10+ on macOS or Linux. No Python packages, model API, database or background service are required.

Install the published source for Codex and Claude Code:

```bash
npx skills add cekrauseee/harness --list
npx skills add cekrauseee/harness --skill '*' -g -a codex -a claude-code -y
```

To test a local checkout before publishing, replace `cekrauseee/harness` with `.`.

The CLI's default uses a canonical installed copy and agent symlinks; add `--copy` for independent copies. Each selected skill includes the complete runtime and works without the source checkout or the other four skills. Install the full set for operation-specific discovery. A deterministic build generates those copies from one source; do not edit them manually. `skills.sh.json` controls catalog presentation, not dependency installation.

**Skill installation alone does not activate the continuity discipline.** Preview and explicitly install the short [host integration](docs/host-integration.md). It registers scope before shared writes and checkpoints before delivery, without loading project memory on every prompt. It preserves existing instructions and installs no hooks.

## First use

Use the absolute script path from any installed Harness skill. From this checkout:

```bash
python3 skills/harness-init/scripts/harness.py init --project /path/to/project
python3 skills/harness-task/scripts/harness.py task.start --project /path/to/project --data '{"objective":"Revise the introduction","resources":["notes/introduction.md"],"request_id":"intro-start"}'
```

Save the returned session ID, make the authorized change, then persist its outcome:

```bash
python3 skills/harness-task/scripts/harness.py task.checkpoint --project /path/to/project --data '{"session_id":"<returned-id>","summary":"Revised the introduction and checked its sources.","evidence":["notes/introduction.md; checked cited archive"],"next_action":"User acceptance pending.","status":"delivered","request_id":"intro-delivery"}'
python3 skills/harness-recall/scripts/harness.py consolidate --project /path/to/project
```

A delivered checkpoint releases that participant's claims. It does not imply approval, a commit or publication. The user need not close a session. For longer inputs use `--input file.json`, or `--input -` for stdin. `guide` lists operations and their minimum inputs. Commands return JSON; exit 2 means failure.

## Skills

| Skill | Use |
| --- | --- |
| `harness-init` | Resolve or set up identity and the explicit host instruction link. |
| `harness-recall` | Find relevant knowledge and contributions, then load selected content. |
| `harness-task` | Register responsibility and persist results, blockers and handoffs. |
| `harness-remember` | Preserve sourced facts, hypotheses, decisions and historical context. |
| `harness-maintain` | Diagnose integrity, consolidate knowledge and guide authorized cleanup. |

## Boundaries

Scope claims coordinate participating agents; they do not prevent edits outside the protocol. Silence never releases responsibility. Search is lexical with aliases and explicit budget diagnostics, not a multilingual semantic model. Knowledge is context, not a new instruction source. Keep secrets, credentials, raw conversations and private reasoning out of stored records.

The [documentation index](docs/index.md) covers architecture, installation, examples, verification and limits. [MIT license](LICENSE), Henrique Krause.
