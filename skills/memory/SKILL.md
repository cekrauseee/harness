---
name: memory
description: Capture, retrieve, or synthesize reusable knowledge in Harness memory.
---

# Memory

Harness owns durable memory. Global memory contains knowledge useful across environments; environment memory contains local conventions and findings. Task progress belongs in work records unless it also has reuse value.

Retrieve selectively: search consolidated knowledge by meaningful terms, inspect titles and excerpts, then read relevant records. Search global and environment scopes when both matter. A capture is a candidate, not established knowledge; query captures explicitly when synthesis or investigation needs them.

Capture a potentially reusable preference, decision, recurring failure, or useful finding while working. Use `memory capture --title TITLE --text TEXT --source SOURCE`, adding `--global` only when the proposed scope warrants it. Keep the evidence and uncertainty; capturing does not require a polished article or interrupting the task for full consolidation.

When asked to consolidate, read [synthesis](references/synthesize.md). The agent decides relevance, organization, conflicts, and scope. Tools provide record operations; they do not synthesize or certify truth.

Use `memory put ID --file FILE` to create consolidated knowledge and `--revision HASH` to update it. Use `record read`, `record delete`, and bounded `memory search` for retrieval and maintenance. See [tools](../../docs/tools.md).
