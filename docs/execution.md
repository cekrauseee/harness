# Managed execution

Work can be continuous. Each execution has finite limits and may contain multiple attempts and resumptions. Harness invokes authenticated provider CLIs, keeps operational state in SQLite, and starts local supervisory processes only for that execution.

## Profiles

Profiles explicitly choose provider, model, reasoning effort, attempt duration, economical autonomous eligibility, and whether context mutation is allowed. Default examples are Codex Luna/Sol/Astra and Claude Haiku/Sonnet/Opus roles; inspect `profile list` and choose the models available to the account. They are configuration, not assertions of equal quality or price across providers. Effort labels are not comparable quantities across models.

Autonomous execution requires a profile marked `autonomous`; it receives at most five minutes and one attempt. A full workflow requires a recorded user authorization. The CLI cannot infer user consent from a peer's message. Managed participants cannot create a new root execution or edit profile/configuration defaults.

Provider permissions remain active. Codex uses a writable workspace sandbox plus the Harness data root; Claude preserves native policy with edit permissions and no interactive permission wait. Read-only profiles restrict Harness context mutations and instruct reconnaissance; they are not a separate OS sandbox for application code. Authentication or permission failures are visible results, not reasons to bypass the host.

## Define a workflow

Create a usable initial module graph through the tool:

```sh
harness --environment storefront --work checkout workflow create checkout-dev \
  --mode develop --module payments --resource app \
  --context environments/storefront/work/checkout/payments.md
```

`workflow read` returns the definition and revision. Edit a local input copy and apply it with `workflow write --file FILE --revision HASH`. Validate with `workflow validate --file FILE` before execution.

The JSON definition contains:

- `version: 1` and `mode: develop|review`.
- `limits`: `seconds`, `attempt_seconds`, `concurrency`, `max_attempts`, `max_rounds`.
- `modules`: unique IDs, registered local resources, optional module dependencies, entry coordinator, explicit coordinator/worker nodes with profiles and context references, and graph edges.
- `integration`: the profile, resource, and context of the final integration coordinator.

Each module has one coordinator and 1–16 configured workers. Edges enumerate `delegate`, `request_changes`, `result`, and `accept`. Correction loops are bounded. Module dependencies are acyclic; the worker/coordinator graph intentionally has loops. The initial release supports this specific workflow vocabulary rather than arbitrary embedded expressions.

```text
Macro modules
├── Module coordinator → delegate → Worker(s)
│   └── inspect ← result ────────────┘
│       ├── request_changes → Worker(s)
│       └── accept module
└── Integration coordinator
    ├── request_changes → Module coordinator
    └── accept execution
```

Tests are steps inside development and review. A review can use different module boundaries. The coordinator makes the cognitive judgment; the runtime validates the role, expected state revision, allowed transition, and remaining limits. Process success alone never produces acceptance.

## Start and decide

```sh
harness --environment storefront --work checkout run start \
  --workflow checkout-dev --file /path/to/brief.md \
  --authorization 'The user requested this development workflow.'

harness run status RUN_ID
harness run wait RUN_ID --seconds 30 --after REVISION
harness run result RUN_ID PARTICIPANT_ID
```

A coordinator uses `run decide RUN_ID --event delegate --to WORKER_ID --reason-file FILE --revision N`. Add explicit `--context RECORD` references to grant generated micro plans within the coordinator's accessible context. It yields its turn after delegation; the graph returns control after worker results. Use `request_changes`, `accept`, or `fail` as appropriate.

Workers return useful prose, not a Harness-mandated output schema. Provider JSON is a transport envelope; `run result` extracts the text. A direct task remains awaiting operator acceptance after successful exit.

The integration coordinator can use `request_changes --to MODULE_COORDINATOR_ID` to reopen an accepted module, then yield. The module receives the correction with its original brief; the graph returns to integration after renewed acceptance. This preserves the execution deadline, attempt allowance, profiles, and accumulated worker rounds. Final acceptance also requires successful helper results.

For a small economical reconnaissance task, without a full workflow:

```sh
harness --environment storefront run start --autonomous \
  --profile codex-scout --resource app --text 'Locate the checkout entry points and return the relevant paths.'
```

`run spawn RUN_ID --profile PROFILE --file FILE` adds one economical helper for a managed parent. Yield the current turn after delegation; the graph returns control to the parent when the result is available. Helpers share the run's deadline, concurrency, and attempt allowance, receive at most five minutes per attempt, and cannot delegate again. They are not another unrestricted workflow.

If a helper fails, its parent or the operator can request `run retry RUN_ID HELPER_ID --reason 'Why another attempt can succeed'`. This retries the same assignment and preserves its profile, context, history, and shared budget. Yield after requesting a retry. An ambiguous attempt requires recovery first; a failed helper is not silently treated as completed work.

## Limits and failure

Defaults are 60 minutes per execution, 20 minutes per attempt, concurrency 2, 12 total attempts, and three worker rounds. Profiles can impose a shorter attempt duration. Attempts and concurrent slots are reserved transactionally before process launch. The provider brief is released through stdin only after recording the process identity. Output is bounded to 4 MiB per attempt.

A supervisor schedules participants; a finite companion guard stops tracked process groups if the supervisor disappears or the execution deadline passes. A waiting run consumes no model tokens while awaiting an explicit decision, but its original deadline still applies. Guards do not resume models.

```sh
harness run stop RUN_ID --reason 'The user requested cancellation.'
harness run recover RUN_ID
harness run resume RUN_ID --reason 'The user requested continuation within the remaining allowance.'
```

Resuming preserves the original deadline, attempt count, profiles, and accumulated rounds. Exhausted limits require a separately authorized new execution, not an implicit reset. A human cancellation does not resume because a message arrives.

Recovery inspects process identity and stops verified owned groups, including descendants whose original leader has exited. Group members must remain in the recorded POSIX session; conflicting or unverifiable ownership remains ambiguous. An ambiguous launch is not replayed automatically. `--confirm-stopped` is an operator assertion used only after verifying the uncertain process has stopped. PID alone is not used as the identity check.

These controls cover processes managed by Harness, not an independent root agent opened elsewhere. Processes sharing an OS user are not a security isolation boundary; a malicious process that escapes its group or alters local state is outside this cooperative execution model. Simultaneous loss of all supervisory processes needs operator recovery. Exact token/currency limits are not promised where provider telemetry/control is unavailable; unknown usage is null, not zero.

## Messages and hooks

`message send` persists content before notification. `message inbox` lists headers without marking them read. `message read` records reading; `message ack` idempotently records acknowledgment after reading. None means the requested work is complete.

Session-start and post-tool hooks emit brief pending-message notices for managed participants. They inject no message body or new authority. No stop hook forces continuation. A terminated participant receives pending context when explicitly resumed or when the authorized graph schedules its next turn.

Local hook scripts must be installed and trusted in the host. The hooks do not provide arbitrary mid-generation interruption, and cloud-orchestrated Work does not support them. For troubleshooting, inspect `run status`, bounded results, and the private supervisor log in the data root.
