---
name: harness-worktree
description: Plan, create, validate, adopt, and retire isolated Git worktrees with Harness-controlled semantics and lifecycle while delegating only physical path and storage to the active agent host. Use when naming, creating, locating, validating, adopting, reusing, or removing a worktree, or when a task needs the Harness `type/slug` branch convention.
---

# Harness Worktree

Apply a Harness-controlled creation protocol and lifecycle while using the active host's storage convention. Harness owns branch naming, base selection, creation, isolation, validation, adoption, reuse, and retirement. The host owns only the physical checkout path, storage layout, and native bookkeeping required to integrate that path.

## Plan a Worktree

1. Read applicable repository instructions and identify the task's primary intent.
2. Choose an allowed Conventional Commit type and translate the task into a short English kebab-case slug. Read [references/worktrees.md](references/worktrees.md) when classification or collision behavior is unclear.
3. Run:

   ```bash
   python3 scripts/resolve_branch.py \
     --project <checkout> \
     --type <type> \
     --slug "<short English description>" \
     --require-available
   ```

4. Use the returned `branch` and validated `base` exactly. The resolver derives the remote default or current branch when `--base` is omitted. It never chooses a worktree path.
5. If the branch exists, adopt it only when the user requested adoption and its Git identity matches. Otherwise choose a distinct slug; never silently rename or reuse an existing branch.

## Create with Host Storage

1. Detect how the active host allocates and records worktree paths from system instructions, available tools, and repository guidance.
2. Obtain or accept the path selected by that host. In Codex, use Codex path allocation; in Claude Code, use Claude Code path allocation. Never substitute a Harness global path.
3. Create the worktree from the resolved base on the resolved branch. Prefer the host's native operation when it preserves that plan and native bookkeeping; otherwise use ordinary Git at the host-selected path.
4. When a native operation combines path allocation and creation, treat it as the execution mechanism for the Harness plan, not as ownership of the creation protocol or lifecycle.
5. Validate the result before starting task work. If the host cannot provide compatible storage or preserve the Harness plan, explain the incompatibility instead of weakening the semantics.

Harness provides no fallback storage root. If the host exposes no allocator, follow explicit user, repository, and host path conventions while keeping the path outside Harness global state.

## Validate Isolation

After creation or adoption:

- confirm the checkout is registered by `git worktree list --porcelain`;
- confirm its current branch is the resolved `type/slug` branch and its base is the planned revision;
- keep implementation, generated files, dependency setup, and verification inside the worktree;
- run the relevant setup and tests from the worktree, then report the host-selected path and results;
- leave the source checkout and unrelated worktrees unchanged.

## Control the Lifecycle

- Adopt or reuse an existing worktree only when requested and after its repository, branch, base, and path identity match the plan.
- Keep the host-selected path in session or handoff context when continuity requires it; do not turn that path into a Harness storage convention.
- Before retirement, inspect worktree registration and status. Never remove a checkout with uncommitted or untracked work.
- Remove or prune only with explicit authorization. Prefer the host's native removal operation when it updates host bookkeeping; otherwise use ordinary Git.
- Confirm retirement removed only the intended registration and checkout. Leave the branch intact unless branch deletion was separately authorized.

## Mutation Boundary

- Resolving branch semantics does not authorize worktree or branch creation, removal, pruning, or deletion.
- Materialize the plan only when the user explicitly asks to create the worktree.
- Never remove or overwrite a worktree with uncommitted changes.
- Do not create Harness metadata inside the repository.

## Portable Semantics

```text
branch:   <type>/<short-kebab-case-slug>
base:     <validated repository revision>
checkout: isolated, host-stored, Harness-managed
```

Host, agent, and user names never appear in the Harness branch. Worktree directory names and locations are selected by the host and are not part of the portable Harness contract.
