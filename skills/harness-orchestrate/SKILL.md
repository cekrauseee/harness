---
name: harness-orchestrate
description: Coordinate authorized multi-agent work as a bounded dependency graph. Use when a task benefits from independent planning, implementation, review, repair, or verification and delegation is already appropriate; keep one root orchestrator, depth one, isolated write ownership, and explicit token and retry limits.
---

# Harness Orchestrate

Coordinate the graph without doing its substantive research, implementation, review, or repair. Inspect only enough task state and evidence to route work, enforce boundaries, integrate compatible outputs, and report the result.

## Authorization boundary

- Apply this protocol only when delegation is already allowed by the user, host, or applicable instructions.
- Do not turn ordinary work into multi-agent work merely because the capability exists.
- Keep the root as the only spawn authority. Tell every child not to delegate or create subagents.
- Keep graph depth at one. A child returns an output to the root; it never branches the graph.
- If delegation becomes unavailable, report the blocked graph instead of silently doing the delegated work at the root.

## Build the graph

1. Define the final outcome, acceptance evidence, mutation authority, and resource envelope.
2. Create the smallest directed acyclic graph that can produce that outcome. Give every node an ID, role, dependencies, inputs, owned outputs, and completion condition.
3. Use roles by behavior:
   - `planner`: decompose or design; read-only.
   - `worker`: produce an assigned result; may write only its owned artifacts.
   - `reviewer`: inspect completed outputs; read-only.
   - `fixer`: apply accepted findings; becomes the sole writer for the affected artifact during that cycle.
   - `verifier`: run or inspect final evidence; read-only unless a verification tool necessarily creates disposable outputs.
4. Run only dependency-free nodes concurrently. Prefer useful parallelism over speculative fan-out.
5. Assign one writer per artifact at a time. Give concurrent writers disjoint paths, records, or external targets.
6. Add review, repair, or verification nodes only when risk, uncertainty, or acceptance criteria justify them. Do not duplicate reviewers by default.

Represent the plan compactly:

```text
P(plan) -> W1(output-a), W2(output-b) -> R(review) -> F(fix?) -> V(verify)
```

Skip `R`, `F`, or `V` when their value does not justify their cost. Run `F` only for accepted actionable findings.

## Set the envelope

Unless task risk or explicit instructions require a different envelope, begin with:

```yaml
max_nodes: 6
max_parallel_children: 3
max_waves: 3
retries_per_node: 1
review_cycles: 1
context_packet_tokens: 1200
agent_output_tokens: 800
default_effort: medium
```

- Use low effort for discovery, inventories, and deterministic checks.
- Use medium effort for normal planning, production, review, and synthesis.
- Use high effort only for a critical decision or failure mode that needs deeper reasoning.
- Use maximum or ultra effort only when explicitly required.
- Reduce the envelope for a small task. Expand it explicitly before exceeding a limit.

Treat token figures as approximate control targets, not permission to truncate required evidence.

## Dispatch minimal context

Use `fork_turns=none` by default. Send each child a self-contained packet with only:

```text
node_id and role
objective and completion condition
dependency outputs or direct artifact references
read scope and exclusive write scope
constraints and mutation authority
required evidence and compact return format
node-specific effort, context, and output limits
instruction: do not spawn subagents
```

Prefer paths, IDs, URLs, commits, and other stable references over copied source content. Pass dependency output only to consumers that need it. Do not forward the full conversation, unrelated project memory, hidden reasoning, or another node's raw transcript.

## Operate the graph

1. Dispatch the first ready wave within the parallel limit.
2. Record only state transitions: pending, running, completed, failed, or skipped.
3. Validate each result against its completion condition before unlocking dependents.
4. Retry once only when the failure is plausibly transient or the packet can be corrected without changing scope.
5. Route substantive defects to the designated fixer; do not patch them at the root.
6. Stop early when acceptance evidence is complete, remaining nodes cannot affect the outcome, the graph is blocked, or the envelope is exhausted.
7. If new work changes scope or authority, pause and obtain direction rather than growing the graph silently.

## Return the result

Report the outcome, changed or produced artifacts, verification evidence, unresolved risks, and any skipped or failed nodes. Keep node-by-node narration out of the final response unless it explains a material limitation.
