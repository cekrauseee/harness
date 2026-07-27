---
name: harness-worktree
description: Plan and create isolated Git worktrees with Harness branch semantics while delegating location, storage, and lifecycle to the active agent host. Use when planning, naming, creating, locating, validating, or adopting a worktree, or when a task needs the Harness `type/slug` branch convention.
---

# Harness Worktree

Apply portable Harness semantics and use the active host's native worktree workflow. Harness owns branch naming, base selection, isolation, and verification. The host owns the checkout path, storage layout, metadata, lifecycle, and cleanup.

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

## Create Through the Host

1. Detect the active host and its worktree mechanism from system instructions, available tools, and repository guidance.
2. Prefer that native mechanism and supply the resolved branch and base when its interface accepts them. In Codex, use the Codex-provided worktree flow when available.
3. Let the host select and manage the physical checkout path. Do not redirect it into Harness global state or reproduce another host's storage convention.
4. If the host creates a checkout before accepting a branch name, create or switch to the resolved branch inside that checkout only when worktree creation was authorized.
5. Use ordinary `git worktree add` only when the host exposes no native mechanism. Follow explicit user, repository, and host path conventions; Harness provides no fallback storage root.

If the host cannot preserve the resolved branch or create an isolated checkout, explain the incompatibility instead of silently weakening Harness semantics.

## Validate Isolation

After creation or adoption:

- confirm the checkout is registered by `git worktree list --porcelain`;
- confirm its current branch is the resolved `type/slug` branch and its base is the planned revision;
- keep implementation, generated files, dependency setup, and verification inside the worktree;
- run the relevant setup and tests from the worktree, then report the host-selected path and results;
- leave the source checkout and unrelated worktrees unchanged.

## Mutation Boundary

- Resolving branch semantics does not authorize worktree or branch creation, removal, pruning, or deletion.
- Materialize the plan only when the user explicitly asks to create the worktree.
- Never remove or overwrite a worktree with uncommitted changes.
- Do not create Harness metadata inside the repository.

## Portable Semantics

```text
branch:   <type>/<short-kebab-case-slug>
base:     <validated repository revision>
checkout: isolated and host-managed
```

Host, agent, and user names never appear in the Harness branch. Worktree directory names and locations are not part of the Harness contract.
