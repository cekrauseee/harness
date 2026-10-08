---
slug: harness
portfolioIndex: 1
name: harness
repositoryUrl: https://github.com/cekrauseee/harness
description: >-
  External project context and focused engineering workflows for agents.
metaDescription: >-
  Harness keeps useful knowledge and continuation context in local Markdown files outside the repository. Ten independent skills support planning, peer deliberation, implementation, review and Git workflows on Codex and Claude Code.
summary: >-
  Harness gives each project an external environment shared by its Git worktrees. Ten independent skills cover context, modular planning, handoffs, agent coordination, peer deliberation and engineering workflows on Codex and Claude Code, backed by one shared instruction file. The workflows guide agents to the context relevant to each task.
highlights:
  - one environment per project and its worktrees
  - ten independent skills for Codex and Claude Code
  - file-based context retrieved only when needed
  - atomic Markdown updates without file reservations
---

Harness gives each project an external environment shared by its Git worktrees. Ten independent skills cover context, modular planning, handoffs, agent coordination, peer deliberation and engineering workflows on Codex and Claude Code, backed by one shared instruction file. The workflows guide agents to the context relevant to each task.

## Project context outside the repository

Each repository or monorepo has one local environment. Its short map helps agents discover applicable constraints and find relevant context. Useful knowledge lives in Markdown files organized by subject. Temporary plans, team configuration and continuation context exist only when needed; small solo changes require no work record.

## Focused workflows and scoped context

Macro plans are modular regardless of the number of agents. Implementation and review fronts can reference the same deliverables while keeping their execution context separate. Handoffs transfer responsibility through canonical file references rather than copied conversations.

When requested, peer deliberation brings agents together to develop an analysis, decision or proposal. Participants contribute and challenge ideas as equals, refine a shared synthesis and preserve material disagreement. Coordination organizes the exchange without deciding which view must prevail.

## Two hosts, one set of instructions

A single instruction file serves Codex and Claude Code: Codex reads it directly, Claude Code imports it, and each host applies a short section of its own. Host mechanics such as memory and managed worktrees are handled by the plugin, so the person sets only practical choices such as language, branch conventions and testing policy.

## Worktrees and safe persistence

Worktrees that Harness creates live inside the project environment; worktrees managed by the host are accepted where they are. Cooperating agents can alternate writes in one front; independent writing fronts use separate checkouts. The Python helper protects Markdown updates against overwriting an intervening change.

After a work item is complete, useful knowledge is consolidated and retained deliverables are preserved with updated references before temporary context is moved to the environment trash, which the person purges when convenient. Material still needed by another front or pending handoff remains available. Worktree retirement is a separate decision.
