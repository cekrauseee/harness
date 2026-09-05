# Examples

Use the installed `scripts/harness.py` path for each command. JSON examples go in `--data`, or a file supplied by `--input`.

## Five chats and one consolidation

Five participants share a writing project's workspace. Each calls `task.start` with a separate resource: introduction, methods, results, references and illustrations. The runtime registers responsibility atomically. If two participants request the same file or overlapping directories, one receives a conflict and does not write that area.

Three finish and record delivered checkpoints with evidence and pending editorial decisions. One records a blocker and one remains active. A sixth participant calls `consolidate`: it sees the three contributions and both remaining owners without receiving any conversation histories. A `task.start` request with `resources:["."]` cannot reserve the workspace while those owners remain. The consolidator can inspect work read-only or continue an unrelated task; it cannot claim a stable complete delivery.

Once participants explicitly deliver or release responsibility, the consolidator reserves `.` and checks actual files against reported contributions. If a commit is requested, the optional Workflows commit skill inspects and groups the real diff. Harness does not decide how commits are made and does not interpret delivery as commit authorization.

## Interruption without closing

After a meaningful result, record an active checkpoint with next action. If the process disappears, no final hook is needed to preserve that checkpoint. A later participant reads it, verifies artifact state and reconciles the uncertain claim before resuming. Age alone never allows taking ownership.

If work is already delivered, its checkpoint releases the participant's scope automatically. Outstanding acceptance or publication remains in `next_action` and is visible to the next reader. The user does not need to close a session.

## A project without Git

```bash
python3 /installed/harness-init/scripts/harness.py init --project /projects/oral-history
python3 /installed/harness-task/scripts/harness.py task.start --project /projects/oral-history --data '{"objective":"Check interview quotations","resources":["chapter-one.md"],"request_id":"quotations-start"}'
```

The project uses path bindings and a directory workspace. Checkpoints and sourced knowledge work as they do in a repository. Canonical edited chapters stay in the project, while private research hypotheses and continuity stay outside it in Harness.

## Different worktrees

Initialize/resolve each worktree. Common Git directory identity links the same project; workspace IDs remain different. Project knowledge is shared, but a checkpoint from tree A is labeled as tree A's contribution. Tree B must verify that the relevant commit or file change is actually available before using that result as local evidence.

## Portuguese queries over English records

A record titled “Source ownership” may include aliases such as `fontes`, `citacoes` and `origem das citacoes`. Query `origem das citacoes` to discover its compact card, then hydrate the ID. If lexical matching misses a concept without aliases, reformulate the query with a relevant English translation. No match does not prove that the project has no useful knowledge.
