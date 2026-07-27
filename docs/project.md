# Project

## Purpose

Harness provides host-neutral continuity and bounded orchestration for agents working on any local project. A project should remain understandable when the host changes, a conversation restarts, or native host memory is disabled.

## Owned concerns

- Agent-facing continuity and orchestration policies.
- Machine-local identity bindings, semantic memory, references, episodic sessions, and scratch state.
- Pull-based context discovery and selective hydration.
- Bounded, depth-one multi-agent work graphs when delegation is authorized.
- Optional engineering conventions, developer documentation, and neutral HTML artifacts when requested.

## Excluded concerns

- Project architecture, domain policy, or substantive task work.
- Application or infrastructure provisioning.
- Daemons, servers, databases, embeddings, or network services.
- Autonomous commits, pushes, pull requests, deployments, or destructive Git operations.
- Host UI, model availability, sandboxing, permissions, or tool execution.
- Worktree storage paths, storage layout, and host-native bookkeeping.

## Precedence

Apply instructions in this order:

1. Host and system rules.
2. Explicit user instructions.
3. Applicable repository instructions.
4. Project-specific Harness policy.
5. Global Harness defaults.

Surface conflicts instead of silently replacing repository policy.

## Project model

A stable UUID is canonical. Registered paths and host project identifiers are first-class bindings; Git identity is an optional compatibility binding. Moving or cloning work should add or update a binding rather than create Harness files in the project.

The user does not need to invoke Harness skills by name. Skill descriptions let the agent identify the relevant workflow, while mutation and publication boundaries still follow explicit authority.
