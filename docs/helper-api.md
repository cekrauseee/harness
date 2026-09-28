# Helper API

`src/harness.py` is the canonical Python 3.9+ standard-library helper. Its copies are generated only into skills that use it. Git and POSIX file locking are required on macOS/Linux. Each command returns JSON; errors return `error.code`, `message` and `details` with exit status 1.

## Resolve and initialize

```bash
python3 src/harness.py resolve --project /path/to/project
python3 src/harness.py init --project /path/to/project
python3 src/harness.py init --project /path/to/project --environment /external/dedicated/path
```

`HARNESS_HOME` defaults to `~/.harness`; `--home` before the command overrides it. Bindings live under `bindings/`, keyed by a digest of the canonical project identity. A default environment has the readable path `environments/<project-name>-<identity-hash10>/`. The suffix disambiguates identical project names without a user-managed ID process.

Git's common directory identifies a repository across all worktrees; the primary checkout provides its project root. The remote URL is not an identity: clones remain separate projects. A non-Git directory is identified by its resolved path, and its descendants resolve to that binding. A nested Git repository remains a separate project. Project moves are not automatically rebound; preserve the existing environment and make a deliberate binding update separately.

`init` is idempotent and publishes the initial descriptor and README as a complete directory. It does not create work, knowledge or worktree folders until needed, edit a target project or alter host configuration. `resolve` performs no writes. Initialization from an existing linked worktree identifies the primary repository correctly. Repeating initialization with another destination fails rather than moving data.

The current descriptor is `environment.json` with exactly `format: "harness-project-v1"` and one `project` containing `kind`, `identity` and `root`. Each binding records that same format/project and an absolute environment path. No legacy format, alias, automatic migration or multiproject membership is accepted. Existing unrelated data is not scanned or removed.

Commands other than `init` select either `--project` or `--environment`, never both. Resolution returns the environment, selected workspace, project identity and predictable `knowledge`, `work` and `worktrees` paths. New checkouts belong under the returned `worktrees` path; native Git or compatible host tools create them.

## Markdown

```bash
python3 src/harness.py read --project /path/to/project --file knowledge/architecture.md
python3 src/harness.py write --project /path/to/project --file knowledge/architecture.md --expect <hash-or-missing> --input /path/to/input.md
python3 src/harness.py delete --project /path/to/project --file knowledge/architecture.md --expect <hash>
```

The allowed paths are `README.md` and `.md` files under `knowledge/` or `work/`. Absolute document paths, traversal, hidden components and symlinks within storage are rejected. Explicit storage roots are canonicalized, including system path aliases such as macOS `/var`. `read` returns UTF-8 content and its SHA-256, or `missing`. `--input -` reads stdin. A mutation compares the observed hash under a cooperative filesystem lock and atomically replaces or removes the file. Repeating a write of the current bytes or deletion of a missing document is a no-op. Different stale contents produce `document_conflict` without overwriting data.

The lock covers individual file transactions, not agent ownership. Writers using other file tools do not acquire it and must coordinate their updates. It has no lease or expiry and is never deleted as a recovery shortcut. Pre-replacement failures preserve old bytes; `write_uncertain` requires inspecting the current state before retrying. No operation stores raw inputs beyond the requested document.

## Close a completed work item

```bash
python3 src/harness.py inspect-work --project /path/to/project --work access-control
python3 src/harness.py close-work --project /path/to/project --work access-control --expect <tree-hash>
```

`inspect-work` returns filenames and a digest of that one work tree. `close-work` checks that digest, atomically detaches `work/<name>/` and deletes it. It never removes knowledge, another work directory or Git worktrees. The caller must establish completion, consolidate useful knowledge and preserve active consumers before invoking it; Markdown is not interpreted as an agent state machine.

A process interruption during removal may leave `work/.closing-<name>/`. Retrying the same close finishes removal. If the work name was reused while that directory remains, the helper refuses to delete either. Successful completion leaves no archive or receipt. Other filesystem failures are reported as `io_error`; inspect the named work before retrying.
