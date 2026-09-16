---
slug: harness
portfolioIndex: 1
name: cekrause/continuity
repositoryUrl: https://github.com/cekrauseee/harness
description: >-
  Persistent knowledge and coordination across agents, tasks, and repositories.
metaDescription: >-
  Continuity keeps relevant decisions, useful findings, and unfinished work
  available between agent tasks. Knowledge lives in local Markdown files outside
  the repositories.
summary: >-
  Continuity keeps relevant decisions, useful findings, and unfinished work
  available between agent tasks. I built it so that context could remain
  available when work moves to a new conversation or another agent. Four
  independent skills guide environment setup, context retrieval, knowledge
  maintenance, and coordination of shared changes.
highlights:
  - knowledge in local Markdown files outside repositories
  - four independent skills
  - retrieving context when the task needs it
  - file reservations and atomic coordination
---

Continuity keeps relevant decisions, useful findings, and unfinished work available between agent tasks. I built it so that context could remain available when work moves to a new conversation or another agent.

Four independent skills guide environment setup, context retrieval, knowledge maintenance, and coordination of shared changes.

## Sharing knowledge across projects

Knowledge lives in local Markdown files outside the repositories. Related projects can belong to the same environment and share notes and contributions, while each working directory retains its own identity.

Environment membership is explicit. A contribution can span files in several repositories while retaining a record of the project where it started. Git worktrees share their repository’s environment but remain distinct workspaces.

## Retrieving context when the task needs it

The skills instruct agents to begin with the request and the information already available. Stored knowledge is consulted when an earlier decision or a missing fact could affect how the task is approached.

Notes preserve their scope, sources, and uncertainty. Confirmed decisions remain distinct from hypotheses, and information already documented adequately in a project can stay at its original source.

## Coordinating changes and unfinished work

A Python helper checks for overlapping file reservations and protects knowledge updates from overwriting content that has changed since it was last read.

When a task needs to be resumed later, its contribution record holds a summary of the current state and next steps. Once the work is complete, relevant knowledge is consolidated, and the contribution and its reservations are removed in a single atomic operation.

Reservations coordinate agents that follow the same procedure. They do not prevent edits made through other tools, an important limitation of this approach.
