# Mechanical helper

`src/harness.py` is the canonical, Python standard library helper. Each published
skill contains the same executable file at `scripts/harness.py`. It owns project
identity, current write reservations, and compare-and-swap (CAS) Markdown changes.
It does not interpret knowledge or decide what agents should remember or do.

## Storage

Storage defaults to `HARNESS_HOME`, or `~/.harness`. `--home DIRECTORY` overrides
it and precedes the command. Project roots and storage must be outside one another.
All state stays outside target repositories:

```text
HOME/
  .runtime.lock
  projects/<project UUID>/
    project.json
    knowledge/*.md
    references/                 # Optional existing reference assets
```

`project.json` is one atomic snapshot. Its current format is:

```json
{
  "format": 1,
  "id": "c3c93eec-9eab-4ed8-acfc-935fc02f64eb",
  "name": "Example",
  "roots": [{
    "path": "/work/example",
    "git_common_dir": "/work/example/.git",
    "workspace_id": "d266b810-228b-58cf-a78c-c7817374f993"
  }],
  "contributions": {
    "8b0f448a-3c04-4ae8-bd42-a23e1a90fc5e": {
      "id": "8b0f448a-3c04-4ae8-bd42-a23e1a90fc5e",
      "purpose": "Update the parser",
      "workspace": "/work/example",
      "workspace_id": "d266b810-228b-58cf-a78c-c7817374f993",
      "resources": ["/work/example/src/parser.py"],
      "active": true,
      "handoff": "",
      "version": 1,
      "updated_at": "2026-09-06T12:00:00+00:00"
    }
  }
}
```

Non-Git roots use an empty `git_common_dir`. Reference-only projects can have
`roots: []` and are selected by ID. Explicit release can add `release_reason` to a
contribution. `workspace` records the original writer's path; explicit root
replacement preserves its `workspace_id`, including on inactive contributions.
Only the current format is accepted; duplicate JSON keys and nonstandard JSON
constants are rejected. There are no compatibility readers, indexes,
event journals, receipts, session records, or checkpoint histories.

## Commands

Run `python3 /path/to/scripts/harness.py --version` to report `0.8.0`.
Commands print one JSON object. Helper errors print
`{"error":{"code":"...","message":"...","details":{}}}` and exit 1;
argument syntax errors exit 2. Success exits 0.

Except where a path is specifically required, select exactly one of
`--project PATH` and `--project-id UUID`.

| Command | Additional arguments | Effect |
| --- | --- | --- |
| `resolve` | Project selector | Read identity and the selected workspace. Never initializes. |
| `init` | `--project PATH [--name NAME]` | Create identity or register a worktree under the existing Git identity. |
| `bind` | `--project PATH --project-id UUID [--replace OLD_ROOT]` | Explicitly associate a root, or replace an old binding while preserving its workspace ID. Does not move files. |
| `status` | Project selector | Return every current contribution and active reservation with provenance. |
| `claim` | `--project PATH --purpose TEXT --resource PATH ...` | Create a separate owner UUID and version 1; reserve all requested resources atomically. |
| `claim` | `--project PATH --owner UUID --expect VERSION --resource PATH ...` | Extend an active owner, preserving its purpose and workspace. |
| `handoff` | Project selector, `--owner UUID --expect VERSION --input FILE [--release]` | Replace current Markdown handoff, optionally releasing ownership in the same snapshot replacement. |
| `release` | Project selector, `--owner UUID --expect VERSION --reason TEXT` | Explicitly relinquish ownership and preserve the reason. |
| `drop` | Project selector, `--owner UUID --expect VERSION` | Remove an inactive contribution after the agent consolidates useful knowledge. |
| `read` | Project selector, `--file NAME` | Read Markdown and its SHA-256 from the same bytes. |
| `write` | Project selector, `--file NAME --input FILE --expect HASH_OR_missing` | Replace opaque Markdown only if the observed version still matches. |
| `delete` | Project selector, `--file NAME --expect HASH` | Delete a knowledge file only if the observed version still matches. |

Use `--input -` to read UTF-8 Markdown from standard input. Handoffs must contain
non-whitespace text, including when releasing ownership. A contribution purpose
is required only when creating its owner. An extension cannot move ownership to a
different workspace. Resource paths are literal, without glob syntax; relative
paths resolve from the selected workspace root. Claims compare canonical absolute
paths, including symlink targets and parent/child overlap, across all registered
projects. Conflict details identify the owning project and contribution. Status
remains scoped to the selected project.
Existing file aliases, including hardlinks and filesystem case aliases, are
compared by physical identity. Existing directory aliases also cover future
descendants; paths are not unconditionally casefolded.
Reservations require cooperating writers; they do not restrict native file tools.

Git identity uses the local common directory, so worktrees share a project and
clones remain separate. `resolve` can identify an unregistered worktree without
writing; `init` or its first claim registers the returned workspace. Non-Git
resolution uses the closest registered ancestor. Cross-project root overlaps and
common-directory collisions are rejected. Changed Git topology requires an
explicit `bind --replace`. Replacement is forbidden while that workspace has active
contributions. An existing directory is required as the destination; the old
registered path may no longer exist.

Knowledge names are safe relative `.md` paths, optionally nested. Absolute paths,
`..`, symbolic links in the knowledge path, and access outside the knowledge
directory are rejected. References and the project snapshot cannot be edited by
the document commands. Native tools can list and search authored Markdown; use
`read` before a CAS edit to couple the content and observed hash correctly.

## Results and retries

Every successful result includes `project_id`, `project_dir`, `knowledge_dir`, and
`workspace`. The workspace is `{path, git_common_dir, workspace_id}` for path
selection and `null` for ID selection.

- `status` adds the `contributions` dictionary and `reservations` list. Each
  reservation contains `owner`, `purpose`, `workspace`, `workspace_id`, `version`,
  and `resource`.
- `claim`, `handoff`, and `release` add `contribution` and `changed`.
- `drop` adds `owner` and `changed`.
- `read`, `write`, and `delete` add `file`, `missing`, `sha256`, and `content`.
  Missing files use `missing: true`, `sha256: "missing"`, and `content: null`.
  Writes and deletes also add `changed`.

Mutations serialize with POSIX `flock` on `HOME/.runtime.lock`, waiting up to ten
seconds before `lock_busy`. The lock is never unlinked or broken by age. Snapshot
and Markdown replacements write a temporary file, flush and `fsync` it, replace
one destination atomically, then sync its directory. A failed replacement leaves
the prior contents unchanged. A failure after replacement returns
`write_uncertain`; inspect current state before deciding the next action.

Contribution CAS prevents lost updates by the same owner. Different owners' updates
serialize without overwriting one another. There is no automatic expiry: an agent
must establish independent evidence before releasing another writer's ownership.
The helper cannot establish that evidence or authorize the release.

Retries are based on current state, without retained operation history:

- Repeating a claim extension whose resources are already held is a no-op.
- An identical handoff and active/released state is a no-op, even when the supplied
  expected version predates that result. Different stale updates fail.
- Closed owners cannot reopen or acquire more resources. Releasing an already
  closed owner is a no-op and preserves its existing reason and handoff.
- Dropping an absent owner and deleting an absent knowledge file are no-ops.
- Writing bytes already present is a no-op, even with the earlier expected hash.
- Repeating a completed root replacement is a no-op when its old path is absent
  from the bindings and the destination already has the intended topology.

A new claim receives its owner UUID from the helper. If its response is lost,
inspect `status` and reconcile the current contribution; blindly creating another
claim cannot replay or recover a historical response. Similarly, no-op retries do
not prove which process produced the matching current state.

## Python entry point and tests

`execute(operation, data, home=None) -> dict` uses the same operation and argument
names as the CLI, with hyphens changed to underscores. Repeated resources use
`resource: ["path", ...]`; `input` is a file path or `"-"`. It raises
`Error(code, message, details)` for helper errors. It does not accept an alternate
JSON command language.

Run the kernel tests with:

```sh
python3 -m unittest discover -s tests -p test_kernel.py -v
```

Set `HARNESS_TEST_HELPER` to an absolute copied `scripts/harness.py` path to run the
same temporary-directory tests against a bundled or installed helper. Tests cover
separate-process contention, stale CAS, retry behavior, failed replacement,
worktrees, clones, root moves, Markdown integrity, and path escapes.
