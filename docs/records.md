# Context and records

```text
~/.harness/
├── config.json
├── state.sqlite
├── bin/harness
├── memory/
│   ├── captures/
│   └── knowledge/
├── environments/<environment>/
│   ├── environment.md
│   ├── resources.json
│   ├── memory/{captures,knowledge}/
│   ├── code/repositories/<repository-resource>/worktrees/<checkout>/
│   └── work/<work>/
│       ├── work.md
│       ├── workflows/*.json
│       └── optional context records
├── archive/
└── .runtime/<run>/
```

Directories appear when used. The environment and work IDs are supplied by their paths, not repeated in Markdown frontmatter. Global memory is explicitly selected; there is no global active environment. Resource bindings carry kind, location, ownership, and optional work association.

## Temporary worktrees

Additional Git worktrees use `<root>/environments/<environment>/code/repositories/<repository-resource>/worktrees/<checkout>`. Resolve the effective root from `--root` or `HARNESS_ROOT` (default `~/.harness`), select the existing environment, and use its repository resource ID and a unique checkout identifier. The [Git skill](../skills/git/SKILL.md#worktrees) permits creation when requested or when concrete parallel work requires isolation; ordinary sequential work uses the primary checkout.

The repository directory is its resource area in Harness. The primary checkout can remain elsewhere, referenced by its resource binding. Git creates and removes additional linked checkouts. Harness records their actual paths as owned `worktree` resources, with work associations when applicable. Existing bindings remain in `resources.json`; this layout does not migrate that registry or work records.

The `worktrees` directory is reserved for application files. Record reads, writes, and deletion reject paths within it, and context searches skip it entirely. Keep durable context outside checkouts. Environment archival refuses to move a nonempty worktree area, including an unregistered checkout, so Git registrations remain valid. After Git cleanup leaves the area empty, normal archival can proceed.

The location is an agent delivery convention; resource tools register existing paths and do not create worktrees or enforce their placement. Existing checkouts at other registered locations can remain until normal cleanup. After a confirmed merge, the [cleanup skill](../skills/clean/SKILL.md) synchronizes the local target, removes integrated temporary resources, and updates their bindings. Environment or work archival does not replace Git cleanup.

## Human content

Write English Markdown with a meaningful level-one title. Use a short purpose or actionable statement first, then sections appropriate to the content. For example:

```markdown
# Checkout retry deadline

Bound retries by the request's total deadline.

## Conditions

Apply this to the checkout API's retryable upstream errors.

## Source

Endpoint behavior documented in the application contract.
```

Do not add empty template sections or repeat the same metadata everywhere. Include sources, conditions, uncertainty, and dates when they help interpret or revalidate the statement. Code documentation remains in the owning application; internal plans and execution context stay here.

## Record operations

`record read` returns a revision and a bounded text slice. Creating a record requires that it does not exist. Updating or deleting requires its current revision. Writers compare the revision while holding a process lock, then atomically replace the file. A conflict is a request to reread and reconcile; it is not permission to force an overwrite.

Generic record operations address Markdown in context, memory, or archive scopes. Configuration and workflow definitions have separate tools. Paths are relative to the Harness root; traversal and symlink record paths are rejected. Records are limited to 256 KiB, and one read returns at most 40000 characters.

Search returns titles and short excerpts with pagination. Memory search defaults to consolidated knowledge; `--captures` explicitly searches candidates. Source references support evaluation without promising that the original source is archived or will remain available forever.

## Operational content

SQLite stores runs, participants, attempts, decisions, messages, and receipts. Runtime files contain credentials and bounded provider transport logs. These are not canonical knowledge, and they are not automatically injected into future tasks. Tokens are local participant capabilities, never part of public tool output.

Do not version the data root. Archive environments or work through their tools; active or unresolved executions prevent archival, and environment archival requires empty worktree areas. Archival preserves knowledge and history rather than deleting it.
