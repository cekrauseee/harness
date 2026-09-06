# Host integration

Install the skills, then edit the instruction file the host actually reads, within the user's authorization. Examples are `~/.codex/AGENTS.md` and `~/.claude/CLAUDE.md`. Preserve unrelated instructions and replace an existing integration block instead of adding duplicates. Ordinary file tools are sufficient; Harness has no host-configuration installer.

A compact instruction for a host with Harness and Workflows installed can be:

```text
For substantive project work, use the current installed Harness skills to recall confirmed guidelines and relevant knowledge and handoffs. Reuse that context and refresh it when needed. Use harness-remember to preserve clearly established durable guidance with its source and scope, without waiting for a separate save request. Use harness-task to reserve shared project files before writing and resolve overlapping ownership.

Before the final response, consolidate useful knowledge, release your reservations, remove completed or superseded execution records within the current work and verify the resulting state. Keep a current handoff only for genuine pending work; preserve unrelated records and other writers' ownership. Complete this as part of delivery without a session-closure or cleanup request. Generic questions need no record, and read-only requests remain read-only.

Use the applicable installed Workflows skill for worktrees, commits, pull requests, reviews, developer documentation or standalone HTML artifacts. Select only what the current request needs and preserve its authorization and read-only boundaries.

The agent owns investigation, judgment, execution and verification; helper success alone does not establish completion. Confirmed guidance applies within its scope; tentative discussion and other knowledge are context. These do not grant new permissions or override current user directions and applicable host or repository instructions. Keep commands and storage mechanics in the installed skills.
```

Omit the Workflows paragraph when it is not installed. The packages remain independent. Keep this instruction about when and why to use the skills; their current contents provide resource paths, commands and storage details. Do not copy those implementation details into global instructions.

Verify the edited instruction and the installed skill paths directly. Removing the integration means deleting only that block. There are no hooks, prompt injections, model calls or background processes. Delivery cleanup is an agent obligation before the final response, not a process triggered by closing a chat. A forced interruption can stop that sequence; on resumption, the agent reconciles the current files and remaining records rather than assuming cleanup succeeded.
