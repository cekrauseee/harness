---
name: commit-pr
description: "Draft or create Conventional Commits and pull requests for a finished change: cohesive staging, commit messages, PR title and prose description. Use when asked to commit, write a commit message, or open or update a pull request."
---

# Commit and pull request

Match the requested result: a message or description only, a staging plan, local commits, or a remote PR creation or update. Wording-only requests stay read-only.

## Commits

Group files or hunks by cohesive intent, including the documentation and verification changes that belong with the behavior. Preserve unrelated modifications and existing staging; another writer's staged work is not yours to commit. If the index mixes scopes, build the intended commit without discarding that staging, or settle a truly inseparable boundary with the user.

Write English Conventional Commits, `type(scope): description` with the scope optional, for example `feat(auth): enforce resource-level permissions`; mark a breaking change with `!` before the colon or a `BREAKING CHANGE:` footer, and add an explanatory body in prose when useful. Classify each commit by its own change, independently of the branch or PR type. Inspect the final staged scope and reuse valid verification before committing.

## Pull requests

Establish repository, base, head and the complete proposed change from current evidence; local uncommitted changes are not part of a published PR. Title in Conventional Commits form describing the macro change, for example `feat(auth): add resource-level access control`, unless the project convention differs; keep the branch semantically aligned without renaming it for title edits.

Write the description as prose for a reviewer without the chat history: the problem, the resulting behavior, relevant implications, the verification actually performed and material limitations. Follow the repository template, scale detail to the change, and leave out commit prefixes on paragraphs, temporary module labels, assignments and abandoned approaches. Before creating or updating remotely, confirm the target and the current remote state; pass the body through a file or structured argument to preserve newlines, then verify the published content and attach the PR to the chat where the host supports it.

Hosts: Claude Code adds its own commit and attribution guidance unless the owner's settings turn it off, so the owner's conventions win where they differ; Codex applies its configured branch prefix to branches it creates.

Return the commit hashes and included scope, the PR link, or the drafted text, with any remaining work. A commit request includes staging but not amending, bypassing hooks, pushing or publishing; a PR request includes no merge, release or deployment.
