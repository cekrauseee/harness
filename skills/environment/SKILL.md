---
name: environment
description: Select or maintain a Harness environment and its resource bindings.
---

# Environment

An environment is a meaningful context boundary, not a synonym for a repository. It may contain several repositories or a non-code project. Resources belong to that environment; several environments may intentionally refer to the same external resource.

Use existing task context and `environment list` to select the environment. Inspect relevant resource bindings with `resource list`. A working directory is evidence, not an automatic identity. When the choice is ambiguous and materially changes the work, ask; otherwise reuse the established context.

Use `environment ensure ID --title TITLE` when a new boundary is justified. Describe its purpose in `environment.md` through `record write`, retaining the revision returned by `record read`. Bind local directories, repositories, worktrees, URLs, branches, or PRs with `resource add`; identify owned temporary resources and their work when applicable.

Pass `--environment ID` before the command or inherit the managed execution context. There is no global active environment. Archive through `environment archive` only when appropriate; active execution references prevent archival.

See [tools](../../docs/tools.md) for command syntax and [records](../../docs/records.md) for formatting and revisions.
