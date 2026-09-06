# Host integration

Install the skills, then edit the instruction file the host actually reads, within the user's authorization. Examples are `~/.codex/AGENTS.md` and `~/.claude/CLAUDE.md`. Preserve unrelated instructions and replace an existing integration block instead of adding duplicates. Ordinary file tools are sufficient; Harness has no host-configuration installer.

A compact instruction for a host with Harness and Workflows installed can be:

```text
For substantive project work, use the current installed Harness skills to locate external knowledge, read confirmed project guidelines and select relevant documents and current handoffs. Reuse that context during the task and refresh it when needed. Use harness-remember to consolidate clearly established durable project guidance without waiting for a separate request to save it; keep its source and scope, replace superseded guidance and do not promote tentative discussion into rules. Before shared project-file writes, use harness-task to reserve resources and resolve overlapping ownership. Keep a current handoff and release ownership with it before delivery. Check actual files and reservations before reporting stable consolidation. Generic questions need no continuity record.

Use the applicable installed Workflows skill for worktrees, commits, pull requests, reviews, developer documentation or standalone HTML artifacts. Select only what the current request needs and preserve its authorization and read-only boundaries.

The agent owns investigation, judgment, execution and verification; helper success alone does not establish task completion. Confirmed guidance applies within its recorded scope; other knowledge is context. Neither grants new permissions or overrides current user directions and applicable host or repository instructions. Keep commands and storage mechanics in the installed skills.
```

Omit the Workflows paragraph when it is not installed. The packages remain independent. Keep this instruction about when and why to use the skills; their current contents provide resource paths, commands and storage details. Do not copy those implementation details into global instructions.

Verify the edited instruction and the installed skill paths directly. Removing the integration means deleting only that block. There are no hooks, prompt injections, model calls or background processes. The helper guarantees consistency when called; participation and semantic handoffs remain agent behavior.
