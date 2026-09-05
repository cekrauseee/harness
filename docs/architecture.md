# Architecture

## One project, several workspaces

A project is a stable UUID and its knowledge and tasks. A workspace identifies a concrete directory. A task describes an outcome; a session identifies a participant and does not require a host conversation ID. These records live in one project snapshot under `projects/<uuid>/state.json` inside `${HARNESS_HOME:-~/.harness}`. No marker, database or operational state is added to the project.

Registered ancestor paths support non-Git projects and subdirectories. Git common-directory identity links worktrees, while each tree keeps its workspace and checkpoints. Remote URL equality is never identity evidence. Explicit bindings and moves preserve identity where filesystem paths change; conflicting evidence requires reconciliation. Host project IDs are optional. Machine-local paths are not a cross-machine synchronization protocol.

## Persistence and concurrency

The snapshot is canonical: project bindings, workspaces, tasks, participants, claims, knowledge, checkpoints, revision, event journal and idempotency receipts are saved together. There is no second authoritative catalog. Query cards and reports are derived views. A failed or unsupported snapshot produces an error, never a fresh empty project.

Mutations take a short operating-system advisory lock on the Harness home, then read, validate and atomically replace a snapshot with filesystem synchronization. The operating system releases the lock when a process dies. The lock protects Harness files; cooperative claims protect project work. A timestamp is never grounds for breaking either protection. Serialization across the local home simplifies cross-project identity checks at the cost of brief contention among unrelated projects.

A `request_id` identifies a semantic mutation. An exact retry returns its prior receipt instead of repeating the action; changed input under the same key fails. The receipt and data commit together. Expected revisions detect stale updates. The journal records state operations and checkpoint references, not tool transcripts; revision cursors prevent skipped update pages. A returned success means the operation completed its persistence path. Inspect failed or uncertain responses before changing a retry key.

This is deliberately a small file system, not a database service. Reading and rewriting a snapshot costs time proportional to its project history. Current history and receipts are retained rather than silently discarded; large archives need an explicit future storage evolution. The implementation targets local macOS/Linux filesystems with advisory locking and atomic replacement. Network filesystem locking semantics and automatic machine synchronization are not supported guarantees.

## Responsibility and delivery

A task start/join acquires its resources in the same transaction as registration. Claims use canonical paths and include directory descendants. `.` claims a workspace. Overlaps are checked independently of recall ranking or output budgets. Distinct worktrees share context but do not claim each other's independent files; paths resolving to the same physical resource still overlap.

Checkpoints explain results, evidence and next actions with session and workspace provenance. Active and blocked sessions retain claims. Delivery releases only that participant's claims; another participant may still be writing. Inactivity changes presence to uncertainty, not task completion or safe ownership release. Interrupted work remains discoverable through its last persisted checkpoint.

A consolidation report alone is a read. Acquire an exclusive `.` claim before a stable consolidation, then inspect the real files and checks. Claims cannot stop an editor or a nonparticipating agent. Even a stable cooperative report is not proof that a commit includes every contribution; the Git diff and actual artifact state remain evidence.

Acceptance, commit, publication and follow-up resolution are explicit events backed by evidence. A resolution names the checkpoint follow-ups or released predecessors being reconciled; the old records remain history. Delivery does not invent those events. Migration preserves unknown historical completion as uncertainty, not approval.

## Knowledge and context

Knowledge records carry title, summary, content, sources, scope, aliases, kind, status and dates. Facts, hypotheses, established decisions and historical context remain distinct. Stored text never becomes host instructions automatically. Knowledge may point to canonical project documentation without copying it.

Recall ranks compact cards lexically, with aliases including a limited Portuguese/English vocabulary and record-specific translations. This is an aid, not semantic equivalence across languages. A relevant unanswered query warrants targeted reformulation or translation. Hydration returns selected content under a character budget. Responses distinguish no match, omitted/truncated content, stale state and errors. Coordination uses direct workspace/resource inspection and never relies on knowledge search.

## Integration and maintenance

The host loads a short explicitly installed instruction block. It routes substantive entry/resume, shared writes, significant outcomes and consolidation to the runtime. All skills have the same standalone runtime, so selective installation does not create hidden skill dependencies. The host controls tools, models and permissions; Harness launches no agents.

There are no default hooks, prompt injections, model calls or background maintenance. Diagnostic maintenance is incremental in the sense that the caller chooses when a concrete need warrants it; it reports duplicates, stale information and integrity problems without deleting active work or reclassifying knowledge. Safe repairs and legacy cleanup require their documented explicit operation. Outside invocations, nothing runs.
