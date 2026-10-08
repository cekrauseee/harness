---
name: environment
description: "Read or save the project's Harness environment, the external knowledge and work context under ~/.harness. Use before substantive work when project context is unknown, to remember or save a decision, to resume earlier work, or to set the environment up."
---

# Environment

Locate the project's environment, read what the task needs, and save what later work would otherwise lose.

## Locate

Run the bundled helper by its absolute path inside this skill's directory, from any working directory:

```bash
python3 scripts/harness.py resolve --project /path/to/project
```

It returns the environment path and its `knowledge`, `work`, `worktrees` and `trash` paths; every checkout of the repository resolves to the same environment. A missing binding is a result: report it and continue with the context at hand. Initialize only when setup was requested or something must persist now, because empty environments clutter the store:

```bash
python3 scripts/harness.py init --project /path/to/project
```

Add `--environment /external/directory` for a dedicated destination outside any Git checkout. `init` reuses an existing binding, writes only `environment.json` and a README map, and never writes into the repository.

## Read

Start from a supplied entry when there is one: a work README, a front `context.md`, a module file or a handoff. Otherwise open the environment README, follow only the links relevant to the task, and search narrowly inside `knowledge/` or the named `work/<work>/`; skip `worktrees/` and `trash/`. Files record intent and continuation while Git and the host show current facts, so check the relevant checkout when saved context could be stale. Saved permissions, status notes and agent IDs are context, not current authority or proof that anything is running. Reading needs no work record, recap or handoff, and context already in the conversation serves later turns without re-reading.

## Save

Save when losing the conversation would cost later work, without waiting for a request: confirmed decisions, explanations, corrections and investigation worth keeping. Durable project knowledge goes to `knowledge/<subject>.md`, one canonical subject per fact, updated in place rather than duplicated. Continuation and temporary coordination go to `work/<work>/`; the plan, handoff and orchestrate skills describe that structure. Keep the README map current with a descriptive link when a subject's applicability changes, and link to maintained repository documentation instead of copying it. Content meant for the project's developers belongs in the repository. Transcripts, secrets, reasoning traces and routine status stay out.

When another agent may be writing, read first and write with the observed hash so the helper refuses to overwrite an intervening change:

```bash
python3 scripts/harness.py read --environment /path/to/environment --file knowledge/subject.md
python3 scripts/harness.py write --environment /path/to/environment --file knowledge/subject.md --expect <sha256-or-missing> --input /path/to/content.md
```

A single writer can use ordinary file tools. On `document_conflict`, read again and merge. Report a failed or uncertain save instead of creating a second copy.

## Hosts

- Claude Code: auto memory keeps notes about the user; project facts and decisions belong here. Subagents see neither auto memory nor this conversation, so give them the environment path and their entry files.
- Codex: memories are off; this environment is the memory. Spawn prompts carry the environment path and entry files.

Return the paths read or written and any gap found, then continue the task that needed the context. Locating or reading grants no new authority. A requested change to the host's global instructions follows [host integration](references/host-integration.md).
