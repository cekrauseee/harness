# Host integration

Edit the host's actual instruction file, such as `~/.codex/AGENTS.md` or `~/.claude/CLAUDE.md`, when that installation or update is requested. Preserve unrelated instructions and replace an existing integration block. Keep user-wide preferences and permissions in the host, project contracts in the repository, execution procedures in Workflows and persistence mechanics in Continuity.

A host with both packages installed can use this routing block:

```text
Use continuity-recall only for prior project information missing from the current task context.

Use continuity-task for shared writes and contributions that need continuation or completion, including work across projects in one environment.

Use continuity-remember for confirmed durable guidance, reusable knowledge absent from canonical sources or scoped knowledge corrections. Use continuity-init for environment setup, explicit project membership or host-integration changes.

Use an applicable Workflows skill when its procedure is needed for the requested outcome. Select only the relevant skill.
```

Omit routes to unavailable packages or skills. The block selects a capability; its skill owns the procedure. Select the relevant project or known environment; membership does not require reading all member projects. Rules needed for every task belong in applicable host or project instructions, while contextual project knowledge stays in Continuity.

Verify the edited block and installed paths. Updating this template alone does not change existing host configuration or installed skills. Removing integration means deleting its block. No hooks or background cleanup are installed.
