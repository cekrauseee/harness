# Execution records

Orchestrations produce, as a by-product of the work, the data a reviewer needs: attention points and flows declared in the plan, run records written by the agents that did the work, events that make a running orchestration observable, and a change map consolidated from them. Facts come from scripts; judgment is written once, by the agent that holds the context. Coordinators read summaries and validator output, not raw logs.

The JSON formats are versioned and defined by the schemas beside this contract: [record](../schema/record.v1.json), [event](../schema/event.v1.json) and [map](../schema/map.v1.json).

## When records exist

Observability follows the structure of the work; there is no separate switch.

| Situation | Records |
| --- | --- |
| Solo work, no front | None |
| A front exists | Events in `fronts/<front>/events.jsonl` |
| A run under a front changes code | A run record in `fronts/<front>/runs/<run>.record.json` |
| A test or review run under a front | A run record whose `tests` and `attention` carry its results |

A record describes committed work, `base...head`. An orchestration that wants records gives its writing fronts commit authority on their own branches; a run without it delivers without a record and says so.

## Plan

A plan that coordinates several fronts or carries risks worth proving declares them with stable ids. Use these sections in `work/<work>/README.md`, or in a module file for module-local points:

```markdown
## Attention points

| Id | Category | Severity | Scenario | Handling | Proof | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| ap-login-resend-race | concurrency | critical | A login verifies the password while a resend rotates it. | Recheck the credential generation when issuing the session. | test | access |

## Flows

| Id | Actor | Trigger | Outcome | Modules |
| --- | --- | --- | --- | --- |
| fl-first-login | employee | Opens the access email link. | Sets a password and reaches the app. | access, session |

Map: yes. 30+ files across three layers and one critical attention point.
```

- Ids are lowercase, `ap-` or `fl-` followed by hyphenated words, unique within the work. Category is one of concurrency, security, data integrity, delivery, rollout or performance; severity is critical, high, medium or low; proof is test, qa or review; owner is the module that must prove it.
- Each module lists the ids it owns. Executors may add ids to the plan, never silently drop one. Owned ids are the floor of test plans and reviews, not the ceiling: findings outside the list become new `ap-` ids.
- The map decision is `Map: yes` when the change is expected to touch more than about ten files, cross two or more layers or modules, or carries any critical attention point; otherwise `Map: no`. Recheck it when the work closes.

Helpers find ids by scanning the plan for tokens; only the map consolidator reads the table rows, by their header names, to show category, severity and scenario.

## Run record

The agent that did the work writes the record at delivery, from context it already holds, and validates it before returning. Its chat return stays under about 1 KB and points to the record path.

| Field | Written by | Meaning |
| --- | --- | --- |
| `format`, `work`, `front`, `run`, `kind`, `iteration` | launcher draft or agent | Identity. `run` is unique in the front; each iteration gets its own run id, such as `impl-2`. `kind` is implement, test or review. |
| `host`, `model`, `session` | launcher draft or agent | Optional provenance. |
| `base`, `head`, `changed` | helper | `head` and `changed` are filled from Git when omitted and checked when present. |
| `summary`, `modules`, `owned` | agent | What was delivered and the ids assigned to the run. |
| `cards` | agent | Components of the change: `id`, `layer`, `title`, `summary`, `files`, optional `group`. Use plan module or flow ids where they fit. |
| `files` | agent | Role of each changed path, one or two sentences. |
| `notes` | agent | `{path, symbol, text}` for significant symbols only. Hunks overlapping a resolved symbol show its note; other hunks show their commit message, so commits must stay cohesive. |
| `edges` | agent | Optional relations between cards that imports cannot show. |
| `attention` | agent | Per owned `ap-` id: `status` (handled, partial, open), `handling`, `evidence` (`{path, symbol, note}`), `tests` (`{path, title}` with the exact title), `qa`, `residual`. |
| `flows` | agent | Per flow the run makes visible: ordered steps with `actor`, `do`, `expect`, optional `url` (an app path or local URL), `commands`, `cards`, `code`, `test`. |
| `tests` | agent | Tests the run added or relied on: `{path, title, ids}`. Test runs use this as the source of coverage data. |
| `followups` | agent | Work noticed and left out. |

Every owned id needs an entry in `attention` or `flows`. A symbol is a top-level declaration name, or `Outer.inner` for a declaration nested in it; Python, JavaScript/TypeScript, Go, Rust, Ruby, shell and Markdown headings have their own declaration patterns; other languages use a generic one. Anchors survive later edits and rebases better than hunk indexes; unresolved ones are reported, not guessed.

Records are immutable: rewriting the same bytes is a no-op, different content for an existing run fails. A correction is a new run id. Validation checks the schema, that card, file and note paths changed in `base...head`, that evidence and test paths exist at head, that test titles appear in their files at head, that `ap-` and `fl-` ids appear in the plan, that owned ids have entries, and that symbols resolve.

```bash
python3 scripts/records.py record validate --environment <env> --input <draft.json> --repo <checkout>
python3 scripts/records.py record write --environment <env> --input <draft.json> --repo <checkout>
python3 scripts/records.py symbol --repo <checkout> --rev HEAD --path src/app.py --symbol Session.issue
```

The launcher pre-fills a draft at `runs/<run>.draft.json` with the identity, `base` and, after the run, `head` and `changed`; `--head HEAD` replaces an outdated head and recomputes `changed`. `record write` validates the same way and writes `work/<work>/fronts/<front>/runs/<run>.record.json`. Errors list each problem with its JSON location; fix the draft and run again until it passes.

## Events

`fronts/<front>/events.jsonl` is append-only, one JSON object per line. The helper fills `format`, `ts`, `work` and `front`, validates the line and appends it atomically under a cooperative lock.

```bash
python3 scripts/records.py event --environment <env> --work <work> --front <front> --data '{"kind": "accepted", "run": "impl-1", "actor": "coordinator"}'
```

| Kind | Written by | Use |
| --- | --- | --- |
| `spawn`, `resume` | launcher | A host run started or resumed. |
| `delivered`, `failed`, `rate_limited` | launcher | A host run ended, failed, or hit a rate limit; carries `tokens`, `duration_ms` and `session`. |
| `returned` | coordinator | An in-host subagent returned; carries the usage the host reported. |
| `accepted` | coordinator | The run's delivery and record were accepted. The map consolidates only accepted runs. |
| `pr_opened` | coordinator | A pull request exists; carries `pr`. |
| `finished` | coordinator | The front's responsibility is done. |

Optional fields: `run`, `actor`, `host`, `model`, `effort`, `session`, `iteration`, `ref`, `tokens` (`input` including cached, `cached`, `output`, or `total` when only a total is reported), `duration_ms`, `pr` and a `note` of at most 140 characters. Events replace progress diaries: a front's `context.md` stays continuation only.

## Launcher

`scripts/run.py`, bundled with the orchestrate skill, runs one Codex or Claude CLI session on a coordinator's explicit command. It never queues or dispatches work by itself.

```bash
python3 scripts/run.py start --environment <env> --work <work> --front <front> --run impl-1 --host codex --cwd <checkout> --prompt <prompt.md> [--model M] [--effort E] [--owned ap-x,fl-y] [--retry N] [-- host options]
python3 scripts/run.py wait --environment <env> --work <work> --front <front> --run impl-1 [--timeout seconds]
python3 scripts/run.py resume --environment <env> --work <work> --front <front> --run impl-2 --from impl-1 --prompt <feedback.md>
```

`start` writes the record draft, then a detached supervisor runs the host CLI in the checkout with stdin closed, keeps its output under `runs/raw/`, parses the session, usage, exit and errors, and appends `spawn`, `delivered`, `failed` or `rate_limited` events. `wait` blocks until the run ends and returns a short JSON summary: status, attempts, session, tokens, duration, record or draft path, and the start of the final message. `resume` continues the session of an earlier run as the next iteration, under a new run id. `--retry` retries rate limits and transient failures with doubling delays, resuming the session once the host created one; without it, nothing is retried. Model, effort and permission or sandbox options come from the coordinator's command, never from the launcher; options after `--` must suit both a start and a resume of the host when retrying.

## Map

`work/<work>/map/` holds the change map of the work: `map.json` (format `harness-map-v1`), generated, and `supplement.json`, written by the agent that fills gaps. The consolidator combines Git facts for `base...head`, the latest accepted records of every front (later acceptances override earlier ones by id, path or path and symbol), the plan's attention and flow tables, and the supplement, which overrides everything else. It resolves symbols at head, derives edges from relative imports in Python and JavaScript/TypeScript, attaches notes and commits to hunks, validates the result against the schema and prints a gap list:

| Gap | Level | Filled by |
| --- | --- | --- |
| `unassigned_file` | error | A card in the supplement that lists the file. |
| `unreported_id` | error | An attention or flow entry in the supplement, or a new run. |
| `unevidenced_id` | error | Evidence or tests for a handled or partial attention point. |
| `unresolved_anchor` | error | A corrected symbol in the supplement. |
| `invalid_reference` | error | Correcting the path, test title or card id it names. |
| `ungrouped_card` | error | A group for every card, required above 40 cards. |
| `isolated_card` | warning | An authored edge, when the card has files without an import extractor. |

```bash
python3 scripts/changemap.py build --environment <env> --work <work> --repo <checkout> --base <base> --head <head>
python3 scripts/changemap.py view --environment <env> --work <work> --viewer <harness checkout>/apps/viewer
```

The supplement uses the `supplement` definition of the map schema; a supplement note with `replaces` takes the place of a record note whose symbol no longer resolves. `view` starts a local viewer instance on the map folder, or prints its command when the viewer is unknown or not installed. Filling gaps costs tokens in proportion to the gaps, not to the diff. A published map stays valid without the viewer; viewing it requires the local viewer application.

## Raw host output and retention

Launcher output from a host CLI (JSON lines or JSON) can contain model reasoning. It is evidence, stored only under `fronts/<front>/runs/raw/`, read by scripts, never read whole into an agent's context or quoted into context files. When the work closes, `map/` is a retained deliverable that needs a durable destination; `runs/raw/` is not retained. Records and events are retained only through the map built from them.
