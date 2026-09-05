# Runtime API

The canonical implementation is `src/harness_runtime/core.py`. Each published skill includes the same generated runtime. The CLI accepts an operation and a JSON object; `guide` describes its inputs. The separate host integration module is described in [host integration](host-integration.md).

## Contract and storage

`execute(operation: str, data: dict, home: Path | None = None) -> dict` returns `success: true`, `project_id`, and the current project `revision`, plus operation-specific fields. Failures raise `HarnessError(code, message, details={})`. The CLI serializes that error and exits with status 2. Core callers supply `project`, an existing directory. `home` defaults to `HARNESS_HOME` or `~/.harness`.

One snapshot, `HOME/projects/<project-uuid>/state.json`, contains schema version 3, defaults version 8, project bindings, workspaces, tasks, participant sessions, checkpoints, claims, memories, lifecycle events, the change journal, and retry receipts. All writes hold the OS advisory lock at `HOME/.runtime.lock` and atomically replace the snapshot after flushing it. A successful transaction updates its records, receipt, journal event, and revision together. Lock-file age does not grant access; process termination releases the OS lock. Writes require POSIX `flock`; unsupported platforms return `unsupported_platform`. The filesystem must support local advisory locks and atomic replacement. This is cooperative coordination, not enforcement against unrelated filesystem writers.

All mutations except `init` require a non-empty `request_id`. Reusing the same operation and exact inputs returns the saved result with `replayed: true`, `original_revision`, and the current `revision`. Different input under the same key fails with `request_id_reused`. Memory receipts contain only the record ID and its original record revision; a replay directs the caller to `hydrate` for current canonical content. Other operations retain their structured original results. Keep the original input and key when retrying an uncertain write. `expected_revision` optionally checks the project revision, except `memory.update`, where it is required and checks the selected memory record's revision.

Reads never initialize state or refresh presence. Malformed or unsupported snapshots, missing journal revisions, incomplete project state and ambiguous identities produce explicit errors. A read failure is not absence of prior work. Runtime state must remain outside every registered project directory. Never supply secrets, transcripts, internal reasoning, or routine tool output as stored content; write concise summaries and source references.

## Identity

| Operation | Inputs beyond `project` | Result or effect |
| --- | --- | --- |
| `init` | Optional `title`, `request_id`, `host` with `host_project_id` | Creates or resolves one UUID; returns `created`, `project`, and `workspace`. Repeated initialization without changes preserves revision. |
| `resolve` | Optional `project_id`, `host` with `host_project_id` | Returns project and workspace identity without enrolling new workspaces. |
| `project.bind` | `project_id`, non-empty `evidence` array, `request_id` | Explicitly associates an additional directory with an existing project. |
| `project.move` | `project_id`, `from_path`, non-empty `evidence` array, `request_id` | Relocates a registered workspace whose former directory no longer exists; preserves project/workspace UUIDs and relocates its contained claim paths. |

Git's physical common directory joins linked worktrees; remote URLs never join separate clones. A registered directory project resolves from its descendants. If that directory becomes a Git repository, verified physical topology preserves its identity and the next mutation enrolls the Git workspace. Distinct workspaces share project coordination while retaining their physical paths. A changed established Git identity requires explicit reconciliation. Initialization, binding, and relocation reject overlapping scopes owned by different project UUIDs. Host identifiers are optional metadata and do not silently enroll an unrelated directory.

## Tasks and claims

| Operation | Inputs beyond `project` and `request_id` | Result or effect |
| --- | --- | --- |
| `task.start` | `objective`; `resources` array; optional `title` | Creates a task and server-generated participant session. Returns `task_id`, `session_id`, `task`, `session`, `claims`. |
| `task.join` | `task_id`; `resources` array | Creates a separate participant on an existing task, including a delivered task being resumed. |
| `task.claim` | `session_id`; `resources` array | Atomically claims additional files or directory subtrees. |
| `task.checkpoint` | `session_id`, `summary`; `evidence` array; `next_action`; `status` | Appends an immutable checkpoint. Returns scalar IDs and the checkpoint, session, task, and released claim IDs. Status is `active`, `blocked`, or `delivered`. |
| `task.release` | `session_id`, `reason` | Releases this participant's claims and closes its participation. Release does not establish delivery. |
| `task.event` | `session_id`, `kind`, non-empty `evidence` array; optional `summary`, `resolves_checkpoint_ids`, `resolves_session_ids` | Records an explicit lifecycle or follow-up resolution event with its evidence. |

Use `resources: []` deliberately when no files are owned. Resources are relative to the registered workspace root or absolute paths. `.` claims the entire workspace. Parent directories, descendants, files, and symlink aliases conflict by physical path, including a shared absolute path used from different workspaces of the same project. Globs are rejected. A conflict leaves the complete transaction unchanged and includes owner task, session, workspace, resource, and presence information. Sessions are cooperative participant identifiers, not authentication credentials. Filesystems writers outside Harness remain outside this protocol.

Presence is `recent`, `unknown`, or `closed`. Silence beyond 30 minutes means unknown presence and retains all claims. A blocked checkpoint retains claims. A delivered checkpoint releases only its author's claims, preserving its reported next action. Released or delivered sessions cannot claim or checkpoint again; `task.join` creates a new participant. The runtime never infers acceptance, a commit, or publication from delivery.

`task.event.kind` is `accepted`, `committed`, `published`, or `resolved`. No kind or summary text automatically clears pending work. `resolves_checkpoint_ids: [id]` explicitly resolves those checkpoints' follow-up actions. `resolves_session_ids: [id]` explicitly reconciles released participants' outstanding responsibility; each target must belong to the same task and own no remaining claims. Active and blocked participants cannot be resolved this way. A `resolved` event must name at least one target. Original checkpoints and released-session history remain intact.

A task is active while a participant is active. It is delivered when at least one participant has delivered and every participant has either delivered or been explicitly reconciled after release. Otherwise it remains blocked. Outstanding follow-up actions are reported separately from contribution delivery. For a replacement contribution: release the predecessor, join and deliver the replacement, then record evidence with `resolves_session_ids` for the predecessor. Explicitly resolve any remaining checkpoint follow-up IDs as well.

## Inspection and consolidation

These operations do not require `request_id`:

| Operation | Inputs beyond `project` | Result |
| --- | --- | --- |
| `task.list` | Optional `scope: "workspace"` (default), `"current"`, or `"all"` | Tasks, participant provenance/presence, and active claims. |
| `task.show` | `task_id` | One task, all its participants, lifecycle events, claims, and checkpoints. |
| `consolidate` | Optional `include_history: true` | All active project claims, latest current-workspace contribution per participant, unknown-workspace contributions, pending actions, and relevant `task_events`. |
| `changes` | `since` revision, or returned `cursor`; optional `limit` and `budget_chars` | Ordered change events, a reliable continuation cursor, and omission diagnostics. |
| `maintain` | None | Read-only integrity, unknown presence, stale memory, missing local sources, and possible duplicate/contradiction reports. |

Consolidation never applies a claim budget. Each contribution includes its latest summary, evidence, next action, and resolution-event IDs (`next_action_resolved_by`, `participant_resolved_by`). It retains all pending and unknown-workspace participants. Historical checkpoints are available through `task.show`, `hydrate`, or `include_history: true`; they are not duplicated by default. Consolidation is a snapshot at the reported revision, not an exclusive review lock. Acquire the necessary claims before editing or preparing a cooperative stable point.

`changes` defaults to 100 events and 16,000 characters. A continuation cursor fixes the upper revision of that pagination sequence; later changes can be read from its final `next_revision`. An event that does not fit is not skipped. Increase the budget and retry the same cursor when `blocked_by_budget` is true. A future or foreign cursor fails with `invalid_cursor`. `has_more`, `omitted_budget`, and `omitted_limit` distinguish unavailable page content from absence. Canonical journal revisions are consecutive; a missing revision is corruption.

## Knowledge

| Operation | Inputs beyond `project` | Result or effect |
| --- | --- | --- |
| `remember` | `title`, `summary`, `content`, `kind`, `sources` array, `scope`, `request_id`; optional `aliases` array and timezone-aware `review_after` | Stores a classified record; returns `memory` with its ID and revision. |
| `memory.update` | `id`, record `expected_revision`, `request_id`, explicit fields to change | Replaces the canonical record fields while preserving unchanged provenance; never silently promotes a hypothesis or historical record. |
| `recall` | `query`; optional `scope`, `limit` (default 10), `budget_chars` (default 8,000) | Compact cards with classification, scope, sources, dates, revision, and stale/supersession status. |
| `hydrate` | `id`; optional `budget_chars` (default 16,000) | Complete selected memory or checkpoint when it fits. |

Kinds are `fact`, `hypothesis`, `decision`, and `historical`. Status is `current`, `stale`, `superseded`, or `retracted`. An explicit update can change either. Supersession requires a different existing `superseded_by` record and cannot create a cycle. Clear `superseded_by` explicitly when reversing supersession. Review dates mark cards stale without rewriting their epistemic kind or status. Updates do not retain prior content inside the memory record.

Recall searches canonical title, aliases, summary, and content lexically; cards omit full content. It accent-folds terms and expands a small Portuguese/English vocabulary. Explicit multilingual aliases improve matching. Diagnostics report this limited method; lack of a lexical match does not prove conceptual absence. Stale and conflicting records stay discoverable with their classification. Maintenance reports lexical duplicate or contradiction candidates for source review and never merges or deletes semantic records automatically.

`status` distinguishes `found`, `absent`, `omitted_budget`, and `omitted_limit`; actual failures are errors. Character budgets cover serialized selected records, excluding response metadata; an empty selection uses zero content characters. Hydration returns a whole current record or `omitted_budget` with `required_chars`, never an unlabeled partial record. Recall is contextual knowledge and must never substitute for the claim ledger when determining ownership.

## Python helpers

Administrative tools and adapters can use `home_path()`, `state_path(home, project_id)`, `new_state(project_id, title="")`, `read_state(path)`, `atomic_json(path, data)`, and the `locked(home)` context manager. `resolve_state(home, project, project_id="", host="", host_project_id="")` returns `(state, workspace)` without writes. These are low-level helpers: a caller performing an authorized transaction must hold the shared lock and preserve the complete snapshot invariants. Ordinary clients should use `execute`.
