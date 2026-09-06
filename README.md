# Harness

The agent owns investigation, judgment, writing and verification. A helper succeeding proves only its mechanical operation, not that the task is correct or complete.

Harness gives agents shared project knowledge and current handoffs without depending on a conversation or model. Knowledge is ordinary Markdown. Agents search, interpret and maintain it using their existing tools.

One small Python helper handles the operations that need a shared transaction: external project identity, overlapping resource reservations, current handoff publication, and document writes checked against the content the agent read. Harness does not classify knowledge, generate prose, run agents or maintain execution histories.

## Install

```bash
npx skills add cekrauseee/harness --skill '*' -g -a codex -a claude-code -y
```

Use `npx skills add . --list` to inspect a local checkout. Add `--copy` when independent copies are needed. Every skill contains the same helper generated from `src/harness.py`; installing one skill does not require the repository or other skills. The helper uses Python 3.10+ standard library on macOS or Linux. Workflows is a [separate instruction-only package](https://github.com/cekrauseee/workflows).

Install or update the short [host instruction](skills/harness-init/references/host-integration.md) through the host's normal file tools. It provides the triggers for reading context, reserving shared files and leaving a handoff. No hooks or configuration installer are included.

## Start working

From an installed skill directory:

```bash
python3 scripts/harness.py init --project /path/to/project
python3 scripts/harness.py claim --project /path/to/project --purpose 'Revise introduction' --resource introduction.md
```

Keep the returned contribution ID and version. After the authorized work, write the outcome, evidence and next action as Markdown, then publish it and release the reservation together:

```bash
python3 scripts/harness.py handoff --project /path/to/project --owner <id> --expect <version> --input /path/to/handoff.md --release
```

Use `--input -` for stdin. Without `--release`, the writer retains its resources. A handoff replaces the current account; it does not append previous versions or imply user acceptance/publication. `status` shows current contributions and reservations.

## Storage and skills

State stays under `${HARNESS_HOME:-~/.harness}/projects/<id>/`:

- `project.json` holds identity, registered roots and current contributions.
- `knowledge/*.md` holds documents written and curated by agents.
- `references/` may contain useful source documents or assets.

Git worktrees share project identity through their common Git directory and preserve workspace provenance. Ordinary folders use explicit path bindings. Reference-only projects can be selected by project ID. Remote URLs never join identities automatically.

| Skill | Responsibility |
| --- | --- |
| `harness-init` | Locate, establish or explicitly rebind project storage. |
| `harness-recall` | Find and read the smallest relevant set of documents and handoffs. |
| `harness-remember` | Write or consolidate sourced Markdown knowledge. |
| `harness-task` | Reserve shared resources and leave current handoffs. |
| `harness-maintain` | Review and remove explicitly authorized obsolete material. |

Reservations coordinate participating agents; they cannot stop external editors. Silence never releases ownership. Knowledge-file hashes prevent overwriting an unobserved change. Sources, uncertainty and semantic decisions remain the agent's responsibility. Do not store secrets, transcripts or private reasoning.

See [architecture](docs/architecture.md), [helper operations](docs/kernel-api.md), and [development](docs/development.md). [MIT](LICENSE), Henrique Krause.
