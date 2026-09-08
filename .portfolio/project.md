---
slug: harness
name: cekrause/harness
repositoryUrl: https://github.com/cekrauseee/harness
description: >-
  project context that agents can carry between conversations.
metaDescription: >-
  harness keeps project knowledge in local markdown files and helps agents
  recover context, coordinate shared work, and leave useful handoffs.
summary: >-
  i built harness to keep project knowledge available across agent
  conversations and workspaces. its skills guide agents through reading
  context, writing notes, coordinating files, and leaving handoffs. a small
  python helper checks shared reservations and document changes.
highlights:
  - "project knowledge in markdown"
  - "context shared across conversations and worktrees"
  - "file reservations for shared work"
  - "notes and handoffs that stay current"
---

harness gives agents a place to keep what matters about a project: decisions,
useful findings, and work that still needs attention.

i built it around ordinary markdown files, stored outside the project. an
agent can read the relevant notes when starting a task and update them as the
work changes. it works with repositories, git worktrees, and folders that
don't use git.

## picking up the work

the skills guide agents through finding context, recording what they learn,
and keeping the notes useful. sources and uncertainty stay alongside the
information, so the next agent can distinguish a confirmed decision from an
idea still being explored.

unfinished work gets a short handoff. completed work gets its useful knowledge
folded into the notes, with old coordination records cleared away.

## sharing files

i added a small python helper for the parts that need a reliable file
operation. agents can reserve files before editing and check for overlapping
work. the helper also checks whether a note has changed since it was read
before allowing a replacement.

these reservations coordinate agents that follow the same process. they don't
lock out other editors or decide whether the work is correct. the agent still
needs to read, think, and check the result.
