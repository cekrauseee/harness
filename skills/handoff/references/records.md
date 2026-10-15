# Execution records

Orchestrations produce, as a by-product of the work, the data a reviewer needs: attention points and flows declared in the plan, run records written by the agents that did the work, events that make a running orchestration observable, and a change map consolidated from them. Facts come from scripts; judgment is written once, by the agent that holds the context. Coordinators read summaries and validator output, not raw logs.

The JSON formats are versioned and defined by JSON Schemas in `schema/`: `record.v1.json`, `event.v1.json` and `map.v1.json`. They sit at the repository root and in every skill whose scripts validate them. The bundled scripts return JSON like the environment helper and, like it, accept `--project <path>` wherever an example shows `--environment <env>`, and `--home` before the command.

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

Helpers find ids by scanning the plan for tokens; only the map consolidator reads the table rows, by their header names, to show category, severity, scenario, handling, actor, trigger and outcome. Those cells are shown as written, so they follow [display copy](#display-copy).

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
| `edges` | agent | Optional relations between cards that imports cannot show: `from` (the caller), `to`, optional `label`. |
| `attention` | agent | Per owned `ap-` id: `status` (handled, partial, open), `title`, `handling`, `evidence` (`{path, symbol, note}`), `tests` (`{path, title}` with the exact title), `qa`, `residual`, optional `cards`. Without `cards`, the map takes the cards that own the evidence and test files. |
| `flows` | agent | Per flow the run makes visible: `id`, `title`, optional `actor`, `cards` and `test`, and ordered `steps` with `actor`, `do`, `expect`, optional `title`, `url` (an app path or local URL), `commands`, `cards`, `code` (`{path, symbol, note}`) and `test`. |
| `tests` | agent | Tests the run added or relied on: `{path, title, ids}`. Test runs use this as the source of coverage data. |
| `followups` | agent | Work noticed and left out. |

Every owned id needs an entry in `attention` or `flows`. A symbol is a top-level declaration name, or `Outer.inner` for a declaration nested in it; Python, JavaScript/TypeScript, Go, Rust, Ruby, shell and Markdown headings have their own declaration patterns; other languages use a generic one. Anchors survive later edits and rebases better than hunk indexes; unresolved ones are reported, not guessed.

Records are immutable: rewriting the same bytes is a no-op, different content for an existing run fails. A correction is a new run id. Validation checks the schema, that card, file and note paths changed in `base...head`, that evidence and test paths exist at head, that test titles appear in their files at head, that `ap-` and `fl-` ids appear in the plan, that owned ids have entries, and that symbols resolve.

```bash
python3 scripts/records.py record validate --environment <env> --input <draft.json> --repo <checkout> [--base <rev>] [--head <rev>]
python3 scripts/records.py record write --environment <env> --input <draft.json> --repo <checkout> [--base <rev>] [--head <rev>]
python3 scripts/records.py symbol --repo <checkout> --rev HEAD --path src/app.py --symbol Session.issue
```

The launcher pre-fills a draft at `runs/<run>.draft.json` with the identity, `base` and, after the run, `head` and `changed`. `--base` and `--head` set those revisions; `--head HEAD` replaces an outdated head and recomputes `changed`. `record write` validates the same way and writes `work/<work>/fronts/<front>/runs/<run>.record.json`. Errors list each problem with its JSON location; fix the draft and run again until it passes.

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

## Display copy

The viewer shows every text field of a map exactly as written: titles of cards, layers, groups, attention points, flows and steps; summaries, file roles and notes; scenario, handling, residual and checks; step actions and expectations; edge labels, follow-ups and the map title and subtitle. Nothing is reformatted, so whoever writes a field writes it ready for a reviewer who has not seen the work. This applies to records, the supplement and the plan cells the map shows.

- English, plain and specific. Name the behavior or component, not the task that produced it: no run ids, module numbers, agent or model names.
- Titles are short noun phrases in sentence case, without a final period: `Sign-in API`, `Session store`, `Invite token reuse`. Acronyms and names keep their real form (`API`, `UI`, `SQL`, `GitHub`); a title is never an identifier with a capital letter (`Api`, `Ui`, `Session_store`).
- Prose fields are complete sentences that end with a period, one idea each. A summary says what the component does now; a file role says why the file exists; a note says why a symbol is shaped as it is, not what its code already shows.
- A scenario is the concrete failure (`A session is issued while the credential rotates.`); handling is how the change prevents it; residual is what can still happen. Checks and step actions are instructions in the imperative; an expectation is what the person observes.
- Edge labels are verb phrases read from the caller: `reads the generation`, `posts the sign-in form`.
- Plain text only: no Markdown, backticks, HTML or emoji. Code belongs in code references and symbols, paths in `files`.
- Fit the surface: card titles about 30 characters and summaries about 80 (two lines on a card), layer and group titles about 24, edge labels about 32. Longer text is cut on the canvas.
- One term per concept across the records of a work; attention points and flows keep the plan's wording.

The consolidator never derives display text from identifiers. A layer, group, attention point, flow or map without a written title shows its id and is reported as an `untitled` gap.

## Launcher

`scripts/run.py`, bundled with the orchestrate skill, runs one Codex or Claude CLI session on a coordinator's explicit command. It never queues or dispatches work by itself.

```bash
python3 scripts/run.py start --environment <env> --work <work> --front <front> --run impl-1 --host codex --cwd <checkout> --prompt <prompt.md> [--kind implement|test|review] [--iteration N] [--actor NAME] [--model M] [--effort E] [--owned ap-x,fl-y] [--retry N] [--retry-delay SECONDS] [-- host options]
python3 scripts/run.py wait --environment <env> --work <work> --front <front> --run impl-1 [--timeout seconds]
python3 scripts/run.py resume --environment <env> --work <work> --front <front> --run impl-2 --from impl-1 --prompt <feedback.md>
```

`start` writes the record draft, then a detached supervisor runs the host CLI in the checkout with stdin closed, keeps its output under `runs/raw/`, parses the session, usage, exit and errors, and appends `spawn`, `delivered`, `failed` or `rate_limited` events. `wait` blocks until the run ends and returns a short JSON summary: status, attempts, session, tokens, duration, record or draft path, and the start of the final message. `resume` continues the session of an earlier run as the next iteration, under a new run id. `--retry` retries rate limits and transient failures with doubling delays, starting at `--retry-delay` (60 seconds by default) and resuming the session once the host created one; without it, nothing is retried. `--kind` (implement by default) and `--iteration` (1 by default; `resume` counts on from the earlier run) go into the draft and the events, `--actor`, the logical agent name, into the events. The `supervise` command is the launcher's own detached process, not for direct use. Model, effort and permission or sandbox options come from the coordinator's command, never from the launcher; options after `--` must suit both a start and a resume of the host when retrying.

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
| `untitled` | error | A title written as [display copy](#display-copy): layers and groups in the supplement, attention points and flows in a record or the supplement, the map in the supplement or the plan heading. |
| `isolated_card` | warning | An authored edge, when the card has files without an import extractor. |

```bash
python3 scripts/changemap.py build --environment <env> --work <work> --repo <checkout> --base <base> --head <head> [--exclude <glob> ...] [--max-lines N]
python3 scripts/changemap.py view --environment <env> --work <work> --viewer <harness checkout>/apps/viewer
```

Every changed file keeps its facts, but its code is omitted from the map when its path or name matches an excluded pattern (lockfiles such as `pnpm-lock.yaml`, `package-lock.json`, `yarn.lock`, `Cargo.lock`, `poetry.lock`, `uv.lock` and `go.sum`, plus `*.min.js` and `*.map`, and any `--exclude` pattern), when it is binary, or when an added file or a diff has more than `--max-lines` lines (3000 by default).

The supplement uses the `supplement` definition of the map schema; a supplement note with `replaces` takes the place of a record note whose symbol no longer resolves. `view` starts a local viewer instance on the map folder, or prints its command when the viewer is unknown or not installed. Filling gaps costs tokens in proportion to the gaps, not to the diff. A published map stays valid without the viewer; viewing it requires the local viewer application.

### Map fields

Every list is present and may be empty; viewers hide empty sections. Text fields follow [display copy](#display-copy).

| Field | Meaning |
| --- | --- |
| `format`, `title`, `subtitle`, `work` | The format id, the map's title and optional summary, and the work it maps. |
| `source` | `repository` (its name, never a local path), the `base` and `head` SHAs, the `baseRef` and `headRef` they were given as, and `headDate`, the committer date of head. |
| `layers`, `groups` | Layers ordered from the user-facing side inward, and the modules that group cards; each with `id` and `title`. |
| `cards` | Cards as records write them, plus `attention` and `flows`: the ids that name the card. |
| `edges` | From caller to dependency, with `kind` `import` (derived from relative imports at head) or `authored` (declared in a record or the supplement) and an optional `label`. |
| `files` | Every path changed in `base...head`: `status` (added, modified, deleted, renamed, copied or type-changed), `added` and `deleted` line counts (null for binary files), `previous` for renames and copies, `role`, and the `cards` that list it. |
| `notes` | Record and supplement notes resolved to their `start` and `end` lines at head. |
| `commits` | `subject` and `body` of each commit in `base..head`, by SHA. |
| `attention` | Every id from the plan, records and supplement: `status` (handled, partial, open, or unreported when no accepted run reported it), `title`, the plan's `category`, `severity`, `scenario`, `handling`, `proof` and `owner`, `residual`, `evidence` resolved to line ranges, `tests` with the line of their title, `qa` and `cards`. |
| `flows` | Every flow: `title`, the plan's `actor`, `trigger` and `outcome`, `cards`, `test`, and `steps` whose code references are resolved to line ranges. |
| `tests` | Tests reported by runs, with the line of their title and the `ap-` and `fl-` ids they prove. |
| `followups` | Follow-ups from records, with the `front` and `run` that reported them, and from the supplement. |
| `runs` | The accepted runs the map was built from: `front`, `run`, `kind`, `iteration`, `host`, `model`, `accepted` time, `record` path and `tokens`. |
| `code` | One entry per changed file: `lines` of an added file at head with the `commits` that introduced them; `hunks` of any other file (`header`, `context`, old and new start and line counts, unified diff `lines`, indexes into `notes` overlapping its new side, introducing `commits`); or `omitted` as `binary`, `excluded` or `too-large`. |

## Raw host output and retention

Launcher output from a host CLI (JSON lines or JSON) can contain model reasoning. It is evidence, stored only under `fronts/<front>/runs/raw/`, read by scripts, never read whole into an agent's context or quoted into context files. When the work closes, `map/` is a retained deliverable that needs a durable destination; `runs/raw/` is not retained. Records and events are retained only through the map built from them.
