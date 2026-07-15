---
name: harness-worktree
description: Resolve host-neutral Harness branch names and global worktree paths without changing Git state. Use when planning, naming, locating, creating, or adopting a Git worktree, or when a task needs the Harness `type/slug` branch convention.
---

# Harness Worktree

Resolve a conventional branch and its global Harness worktree path. The resolver is read-only: Git remains the source of truth, and worktree creation or removal requires a separate explicit user request.

## Resolve a Worktree

1. Read applicable repository instructions and identify the task's primary intent.
2. Choose an allowed Conventional Commit type and translate the task into a short English kebab-case slug. Read [references/worktrees.md](references/worktrees.md) when classification or collision behavior is unclear.
3. Run:

   ```bash
   python3 scripts/resolve_worktree.py \
     --project <checkout> \
     --type <type> \
     --slug "<short English description>" \
     --require-available
   ```

4. Use the returned `branch`, `path`, validated `base`, and `worktree_id` exactly. The resolver derives the remote default or current branch when `--base` is omitted. Do not add a host, agent, or user prefix.
5. If the branch or path exists, adopt it only when the user requested adoption and its Git identity matches. Otherwise choose a distinct slug; never silently rename an existing branch.

## Mutation Boundary

- Resolving names and paths does not authorize `git worktree add`, branch creation, removal, pruning, or deletion.
- Materialize the returned plan with ordinary Git only when the user explicitly asks to create the worktree.
- Never remove or overwrite a worktree with uncommitted changes.
- Do not create Harness metadata inside the repository.

## Naming Standard

```text
branch:   <type>/<short-kebab-case-slug>
worktree: <harness-home>/projects/<project-id>/worktrees/<type>-<slug>-<short-id>
```

The short ID prevents directory collisions and never appears in the branch name. The default Harness home is `$HARNESS_HOME`, falling back to `~/.harness`.
