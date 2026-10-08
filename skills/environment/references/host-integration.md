# Host integration

Change a host's global instructions only within the user's request, preserving unrelated sections, existing authority, tool restrictions and explicit choices. Installing Harness never rewrites `AGENTS.md`, `CLAUDE.md` or host settings by itself.

## Layout

One shared instruction file, owned by the user, serves every host on the machine. Codex reads it directly: it has no import syntax and loads `~/.codex/AGENTS.md` (or `AGENTS.override.md`) with the project chain under a 32 KiB combined cap, so `~/.codex/AGENTS.md` is a symlink to the shared file. Claude Code imports it from a thin `~/.claude/CLAUDE.md` containing `@/path/to/shared/AGENTS.md`; user-scope imports load without approval in terminal and desktop sessions, while Cowork sessions skip external imports.

The file holds, in order: the user's principles and practical choices (language of replies and of environment files, branch and commit conventions, environment home, testing and QA policy, delegation and cost policy); the Harness block below, between its version markers so a later update can be diffed; and one short section per host containing only lines the model acts on. Keep the whole file under 200 lines. Choices the hosts expose as settings go in the settings checklist, not in prose.

## Harness block

Insert verbatim; adapt wording only where it conflicts with the user's own rules.

```markdown
<!-- harness-block v2.0 -->
## Harness: project context and workflows

- Each project has one external environment under `$HARNESS_HOME` (default `~/.harness`), shared by all its worktrees: `knowledge/<subject>.md` for durable decisions, `work/<work>/` for plans and continuation, a README that maps both. Resolve it with the helper bundled in any installed Harness skill (`scripts/harness.py resolve --project <root>`), or match the project root recorded in `environments/*/environment.json`.
- Before substantive work in a project whose context you do not know, read that README map and follow only the relevant links. With a supplied continuation entry, start there. Isolated questions and mechanical edits with enough context need no lookup. Never initialize storage just to look for context.
- Use the installed Harness skill whose stated responsibility covers the requested outcome or a necessary operation, without the user naming it. Read it unless its text is already in context. A suboperation covered by the active skill needs no second skill; when a suboperation ends, continue the broader objective. If a needed skill is missing, say so and continue.
- Preserve decisions, useful investigation and continuation in the environment when losing this conversation would cost later work, without a separate request. Reading context creates no record. Team and front files exist only when coordination or continuation needs them. Keep one canonical source; report failed or uncertain saves instead of creating a competing copy.
- Close a work item only when its whole objective is done and no front or handoff still needs it, after preserving retained outputs. Never store secrets, transcripts or reasoning traces in context files.
<!-- /harness-block -->
```

## Host sections

```markdown
## Claude Code

- Auto memory holds notes about working with the user only (`user`, `feedback`). Project facts, decisions and references go to the Harness environment. Promote a durable lesson to this file or to `knowledge/`, then delete the duplicate.
- Worktrees created by the app or by `EnterWorktree` are accepted as they are. Fronts that Harness creates use `git worktree add` under the environment.
- Subagents receive no auto memory and no conversation history (forks excepted): give each one the environment path and its entry files in the prompt.
- Harness skills are `/harness:<name>`. For work a Harness skill covers, prefer it over bundled skills such as `/code-review` or `/simplify` unless the user invokes those.

## Codex

- Memories are off. The Harness environment is the memory.
- Codex-managed worktrees (root set in Settings) are accepted as they are. Fronts that Harness creates use `git worktree add` under the environment.
- Subagents are directed by the parent: relay deliberation contributions through the coordinator and give each subagent the environment path and its entry files in the spawn prompt.
```

## Settings checklist

| Host | Setting | Purpose |
| --- | --- | --- |
| Codex | `[features] memories = false`; `[memories] generate_memories = false`, `use_memories = false` | The environment is the memory |
| Codex | `git-branch-prefix` (desktop settings) | Branches follow the user's convention instead of a host prefix |
| Codex | `localeOverride` | Interface and reply language |
| Codex | Worktree root (Settings, Worktrees) | Where managed worktrees live |
| Claude Code | `includeGitInstructions: false` and `attribution` | The user's commit and PR conventions replace built-in guidance and trailers |
| Claude Code | `autoMemoryEnabled` | On with the remit above; off if auto memory accumulates project facts or stays empty |
| Claude Code | `worktree.baseRef` | Base for worktrees Claude creates |
| Claude Code | Project instructions mode (`claude-md-or-agents-md`) | Repositories can keep a single `AGENTS.md` |
| Claude Code | `skillListingBudgetFraction` or name-only `skillOverrides` | Keeps Harness descriptions in the skill listing when many plugins are installed |

## Behavior and limits

Skill selection by responsibility is a behavioral instruction; no instruction or setting guarantees every invocation. Evaluate availability, loading or valid reuse, application and composition in the actual host, and judge discovery, preservation and composition rather than catalog coverage: a small fix that loads no skill can be correct. Do not add lifecycle hooks, automatic memory injection, transcript collection or a mandatory invocation announcement to compensate.

Use each host's real capabilities for agents, IDs, worktrees and permissions; invent no parameters and substitute no models silently. Persist concrete team settings in the work's temporary `team.md` only when coordination or continuation needs them. When replacing earlier skills or plugins, identify active consumers before removing discovery entries or helper paths, preserve legacy knowledge and continuations separately, and validate the new inventory in a fresh session of each host.
