---
slug: harness
portfolioIndex: 1
name: cekrause/harness
repositoryUrl: https://github.com/cekrauseee/harness
description: >-
  External project context and focused engineering workflows for agents.
metaDescription: >-
  Harness keeps useful knowledge and continuation context in local Markdown files outside the repository. Fifteen independent skills support planning, implementation, review and Git workflows.
summary: >-
  Harness gives each project an external environment shared by its Git worktrees. Fifteen independent skills cover context, modular planning, handoffs, agent coordination and engineering workflows. Agents load only the material their task needs.
highlights:
  - one environment per project and its worktrees
  - fifteen independent skills
  - file-based context retrieved only when needed
  - atomic Markdown updates without file reservations
---

Harness gives each project an external environment shared by its Git worktrees. Fifteen independent skills cover context, modular planning, handoffs, agent coordination and engineering workflows. Agents load only the material their task needs.

## Project context outside the repository

Each repository or monorepo has one environment. Useful knowledge lives in Markdown files organized by subject. Temporary plans, team configuration and continuation context exist only when needed; small solo changes require no work record.

## Focused workflows and scoped context

Macro plans are modular regardless of the number of agents. Implementation and review fronts can reference the same deliverables while keeping their execution context separate. Handoffs transfer responsibility through canonical file references rather than copied conversations.

## Worktrees and safe persistence

New worktrees live inside the project environment. Cooperating agents can alternate writes in one front; independent writing fronts use separate checkouts. The Python helper protects Markdown updates against overwriting an intervening change.

After a work item is complete, useful knowledge is consolidated and temporary context is removed. Material still needed by another front or pending handoff remains available. Worktree retirement is a separate decision.
