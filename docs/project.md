# Project

## Purpose

Harness provides host-neutral project continuity and engineering standards for coding agents. A project should remain understandable when the host changes, a conversation restarts, or native host memory is disabled.

## Owned concerns

- Agent-facing policies and workflow standards.
- Machine-local project identity, memory, references, sessions, and scratch state.
- Deterministic task-branch naming and portable worktree creation and lifecycle semantics.
- Canonical developer documentation and neutral HTML artifacts when requested.

## Excluded concerns

- Product architecture or implementation.
- Application or infrastructure provisioning.
- Daemons, servers, databases, embeddings, or network services.
- Autonomous commits, pushes, pull requests, deployments, or destructive Git operations.
- Host UI, model selection, sandboxing, permissions, or tool execution.
- Worktree storage paths, storage layout, and host-native bookkeeping.

## Precedence

Apply instructions in this order:

1. Host and system rules.
2. Explicit user instructions.
3. Applicable repository instructions.
4. Project-specific Harness policy.
5. Global Harness defaults.

Surface conflicts instead of silently replacing repository policy.
