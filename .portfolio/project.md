---
slug: harness
name: cekrause/continuity
repositoryUrl: https://github.com/cekrauseee/harness
description: >-
  shared project knowledge for agents working across repositories.
metaDescription: >-
  continuity groups projects in shared environments, keeping useful knowledge,
  pending work, and file coordination in local files.
summary: >-
  i built continuity to keep useful decisions and unfinished work available
  between agent tasks. environments bring related repositories and folders
  together. four independent skills guide context retrieval, knowledge,
  and coordination, with a small python helper protecting shared writes.
highlights:
  - "shared environments for several projects"
  - "knowledge in local markdown files"
  - "context retrieved when the task needs it"
  - "file reservations and useful handoffs"
---

continuity, previously called harness, gives agents a place to keep decisions,
useful findings, and work that still needs attention. i wanted that knowledge
to belong to the work, so another conversation or agent could pick it up.

i built it around ordinary markdown files outside the repositories. four
independent skills handle environment setup, finding needed context, maintaining
useful knowledge, and coordinating shared writes. the host still provides the
model, tools, and execution environment.

## related projects, one environment

an environment groups repositories or folders that share knowledge and work.
continuity and workflows can belong to one environment; a portfolio and its
notes can belong to another. each workspace keeps its identity, including git
worktrees, while the environment holds the shared notes and contributions.

i made the grouping explicit. projects already in different environments are
not silently combined. work spanning several repositories can reserve the
relevant paths while retaining where the contribution started.

## only the context a task needs

an agent starts with the request and the information already available. it
looks up stored knowledge when a previous decision or missing fact matters.
sharing an environment doesn't mean loading every project's notes.

notes keep their scope, sources, and uncertainty. a confirmed decision stays
distinct from an idea being explored. information already captured well in the
project's own documentation can stay there.

## keep the work moving

pending work gets a concise handoff when someone needs to continue it. completed
contributions are removed after useful knowledge has been consolidated. i kept
this focused on the current work, without an archive of agent activity.

a small python helper checks overlapping file reservations and protects notes
from being overwritten after an unseen change. it can close a completed
contribution and release its reservations in one atomic operation.

these guarantees apply to agents cooperating through the same process. they
don't block other editors or judge the quality of an implementation. workflows
can guide execution and delegation; continuity keeps the shared knowledge and
coordination state available when needed.
