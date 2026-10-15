---
name: orchestrate
description: "Coordinate an explicitly requested team of agents working a Harness plan: assign fronts, track delivered outcomes, maintain team and front context. Use when the user asks for a team, parallel workers, or to continue an authorized orchestration."
---

# Orchestrate

Coordinate when the user requests a team or when continuing an authorized one. The coordinator owns the overall objective, responsibilities, dependencies, priorities and the acceptance of delivered outcomes and evidence; executors own technical investigation, implementation, integration, verification and fixes. Return concrete gaps to the responsible executor, and make a targeted check yourself only to resolve a contradiction or an integration gap, without redoing an executor's work or interfering with an active writer.

Use the plan's modules without mirroring them in the team: a front may handle several modules, and implementation and review fronts may share one. Give each executor a coherent outcome, the relevant constraints and its own entry files (front `context.md`, module, dependencies), not the team history. Executors delegate further only when their assignment says so.

A short collaboration runs on native messages and results alone. When shared coordination or continuation needs persistence, keep the team's configuration in `work/<work>/team.md`: logical names, roles, front references, relationships and the requested model, effort or other settings. Distinguish intended configuration from agents the host actually created; record native IDs when useful for continuation, knowing an ID does not prove an agent is running. Each persistent front keeps its responsibility, workspace and continuation in `fronts/<front>/context.md`, and progress lives there rather than in the plan or team file. One front writes to a workspace; a pair can alternate writes in one front, and independent writing fronts use separate checkouts. Read [file contracts](references/file-context.md) when creating this structure. `scripts/harness.py` in this skill, run by its absolute path, resolves or initializes the environment and writes Markdown atomically.

Dispatch only work the request covers, reuse workers for related follow-up, and wait for meaningful results. Reuse their verification and judge its relevance to the outcome; send back missing, contradictory or incomplete results. Honor explicit model, effort and cost choices, and avoid handing a worker the coordinator's more expensive configuration by default.

Execution records make the orchestration observable at little token cost; [execution records](references/records.md) is the contract. Each spawn prompt, kept in a file rather than quoted into context, names the environment path, the entry files, the run id, the owned attention point and flow ids, and the absolute path of that contract. Accept a delivery on its record and `python3 scripts/records.py record validate`, requiring every owned id to be reported with evidence or a stated residual; rerun suites only for a concrete contradiction. Append events with `scripts/records.py event`: `returned` with the usage the host reported for an in-host subagent, then `accepted`, `pr_opened` and `finished`. Runs of a host CLI that must be monitored start with `python3 scripts/run.py start` and are awaited with its blocking `wait`, which returns a short summary; `--retry` for rate limits or transient failures only when requested.

Keep the coordinator's own context small: a fresh coordinator session per phase on a short, complete continuation; the host's default compaction; no log tailing or polling; capped tool output; raw host output read by scripts, never whole; front and team files at most a screen, with events instead of progress entries. When the plan says `Map: yes`, build the change map with the map skill before review.

Hosts:
- Claude Code: subagents start without this conversation or auto memory, so spawn prompts carry the environment path and entry files. Named subagents can be resumed with follow-up messages; agent teams, when enabled, let teammates message each other.
- Codex: subagents are directed by the parent and return summaries; spawn prompts carry the environment path and entry files, and exchanges between agents are relayed through the coordinator.

Update context at useful changes of responsibility, direction or result. Finish when the objective is delivered and known gaps are resolved, and report remaining limitations. Delegation grants no permissions beyond the request.
