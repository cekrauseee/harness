# File context contract

Use the file for the current responsibility directly. Read this contract only when creating or changing the structure; it is not a prerequisite for every task. Existing valid context stays usable across turns and chats.

## Location and boundaries

One external environment belongs to one project. A repository or monorepo and all its worktrees share that environment. Its README is a short map and a place for project-specific guidance. Link to subjects and ongoing work with enough applicability information to discover unknown constraints, without copying their contents. A fundamental rule can live in the map itself; link to that canonical rule from other files. `knowledge/<subject>.md` holds confirmed durable internal knowledge. Under the current local storage contract, all new Git checkouts go under `worktrees/<name>/`; exclude them from knowledge searches.

For substantive work without known project context, locate the existing environment and consult its map, then follow only relevant references. With a supplied continuation entry, start there. Sufficient current context can be reused across turns. Isolated questions and mechanical edits do not require discovery; a missing binding does not justify initialization merely to look for context.

Preserve useful decisions, investigation or continuation when losing the conversation would cause meaningful loss, without waiting for a separate save request. Work exists under `work/<readable-name>/` only when that temporary context or shared coordination needs persistence. Reading context or creating agents alone does not require a work record. Do not create all of these paths in advance:

```text
work/<work>/
  README.md
  modules/<module>.md
  team.md
  fronts/<front>/context.md
  fronts/<review-front>/findings.md
  handoffs/<recipient-scope>.md
```

Names are unique within their active scope and remain stable while referenced. Disambiguate a collision without overwriting another work item. Changing a display title need not rename a path. If a path changes, update its live references. Native Git and host IDs identify actual revisions and agents; no separate work-ID acquisition is required.

## Plan and modules

The work README is the common objective and macro plan: intended result, boundaries, shared constraints, modules, dependencies and references. Always modularize macro planning, including solo work. Each module has an outcome and completion conditions. A module is a deliverable, not an agent, branch or mandatory PR.

An inline module table can be sufficient. Use `modules/<module>.md` when its specific context deserves a separate entry: scope, relevant decisions/interfaces, completion conditions and necessary dependencies. Keep those details there rather than copying them into the macro plan. The plan and module files describe intended outcomes, not live execution status.

## Front context

A front is a cooperating group or solo executor with its own responsibility. Create a front record when its continuation or shared coordination needs persistence; a short assignment may need none. Its `context.md` contains the assigned responsibility, module references, workspace/branch or reviewed version, the useful current situation, remaining work and next action. Include relevant evidence by reference. Preserve only what affects continuation; omit action logs and copies of the module specification. Small temporary investigations may use a single work entry without a macro plan or front hierarchy.

This is the executor's entry point. Follow module and dependency references only as needed. Check relevant workspace reality when resuming; a file cannot prove that a checkout or remote state has remained unchanged.

One front is responsible for writes to a workspace. A pair can share it and coordinate alternation without a claim for every file or action. Independent writing fronts use separate worktrees. Multiple fronts can reference the same modules; front topology does not redefine deliverables. In a pair, agree who maintains shared context or coordinate updates before overwriting it.

Review uses identified versions. Persist actionable findings in the review front's `findings.md` when the assignment needs that artifact. Identify the version and comparison base, impact and source location; preserve unresolved findings needed by the next round. Do not mirror findings in the plan or module. Record current continuation in the front, without duplicating the findings.

## Team configuration

Use native messages and results for short collaborations that need no persistent coordination. When needed, `team.md` belongs to this orchestration, not a reusable global profile library. Record logical agent names, responsibilities, front references, relationships and the requested model/effort or other settings that matter to the assignment. The orchestrator consumes this file; executors receive their own scope directly. Creating agents does not automatically require this file.

Distinguish intended settings from created agents. After creation, associate the logical name with the native host ID and effective settings when relevant. Configuring an agent does not start it, and an ID does not establish live status. Keep progress in front context, not in a second status table. Reuse supported host tools for creation, communication and status when those actions are authorized.

## Handoffs

A handoff transfers responsibility to another agent, subagent, chat or orchestrator. It can transfer the whole plan/team or a specific outcome. Its minimum useful content is the recipient or recipient role, what it may assume, the scoped entry path and any necessary transfer-specific instruction.

If the existing files already carry the necessary context, pointers and the assignment suffice. Use `handoffs/<recipient-scope>.md` only for additional information worth preserving. Do not copy the plan or create an acceptance receipt. The receiver assumes the authorized responsibility and updates its front when needed. Preparing a file is separate from permission to create or message its destination. Historical permission notes are evidence, not new authority. After delivery or assumption, remove obsolete next-recipient instructions from retained material while preserving what pending consumers still need.

## Updates and completion

Files are canonical for relevant persistent context; messages carry pointers, instructions and authorization. Update at meaningful changes of direction, responsibility, continuation or result, not after every action. Maintain map links when adding, moving or removing useful context. Prefer project-relative source references, paired with a revision when validity depends on it; identify local execution paths as local. Do not transcribe conversations or preserve secrets and reasoning traces.

Consolidate useful durable knowledge and remove temporary material after the whole work is complete. Preserve files still consumed by an active front, pending handoff or other ongoing work. Finishing one module or leaving a chat does not close the work. Do not create an archive, receipt or obligatory final summary. Worktree and branch lifecycles remain separate.

Before closure, inspect every file type in the work subtree. Retained deliverables need a durable destination outside that subtree and updated consumer references before removal. Choose the destination according to the artifact and project; no universal output directory or registry is required. Confirm preserved contents and references. Derived views identify their maintained source where one exists; original artifacts must not be assumed regenerable. If retention is unresolved, leave the work open. The helper removes the whole selected subtree, including HTML and other non-Markdown files.

## Helper access

The skill's bundled `scripts/harness.py` resolves a missing environment location and performs atomic Markdown updates. Use its absolute path from another directory. Setup is only needed if no environment exists and the task needs persistent context.

```bash
python3 scripts/harness.py resolve --project /path/to/project
python3 scripts/harness.py init --project /path/to/project
python3 scripts/harness.py read --environment /path/to/environment --file work/access-control/README.md
python3 scripts/harness.py write --environment /path/to/environment --file work/access-control/README.md --expect <observed-sha256-or-missing> --input /path/to/content.md
```

Shared updates use the observed hash; a conflict requires incorporating the intervening change. A failed or uncertain save is not confirmed persistence: inspect the state and report the limitation rather than silently creating a competing authoritative copy. These transaction checks do not create reservations or record agents. They protect cooperating helper writers; ordinary file tools must also preserve concurrent changes. Document operations accept Markdown only; use appropriate file tools for other artifacts. The helper never determines semantic completion, spawns agents, searches all memory or creates Git checkouts.
