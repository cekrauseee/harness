# Evaluation

The verification uses temporary homes and projects. It does not migrate the user's state, edit actual host instructions, publish either package or use paid model APIs. Browser, development-server and visual QA were not part of this file-native refactor.

Verification recorded on 5 September 2026: the final suites pass **60 Harness tests and 35 Workflows tests**, on Python 3.9.6 and 3.12.14. All 11 skill validators and both Codex plugin validators pass. The four accepted independent-review findings have regression coverage and are resolved.

## Reproduce

```bash
python3 scripts/build_dist.py
python3 -m unittest discover -s tests -v
python3 scripts/verify_install.py --workflows ../workflows --output /tmp/harness-install-results.json
python3 scripts/benchmark.py --output /tmp/harness-benchmark.json
```

Run Workflows' unit suite from its own checkout. The runtime/distribution tests exercise installed skill copies with no import path to the development source. The additional skills CLI script installs through the actual Vercel installer in disposable homes, removes the source package, executes the installed helpers, and verifies reinstall/removal. Workflow helper semantics are covered by that repository's tests; the CLI matrix checks their installed imports with `--help`.

## Acceptance coverage

| Scenario | Executable evidence |
| --- | --- |
| Five chats, mixed delivery/blocking and consolidation | Runtime fixture and benchmark preserve all participants, pending work and active claims; whole-workspace reservation conflicts. |
| Concurrent writers and checkpoint updates | Separate spawned processes race for overlapping claims and distinct checkpoint writes. |
| Crash and retries | Atomic replacement failure, lost-response retry, changed-input rejection and guarded migration recovery. |
| Worktrees, clones, subdirectories and moved paths | Identity tests distinguish shared project from shared physical resources; remotes do not join clones. |
| Non-Git and interrupted work | Directory project and uncertain-presence tests retain checkpoints and claims. |
| Old or contradictory knowledge | Epistemic kinds, explicit supersession, source diagnostics and stale status remain visible. |
| Limited multilingual search | Alias-based Portuguese query, budget omissions, absent records and revision cursors. |
| Repeated maintenance | Read-only diagnostics leave canonical bytes unchanged. |
| Migration and old installations | Checksum preview, complete backup, source drift, duplicates, edited defaults, mixed hooks and exact legacy skill recognition. |
| Host integration | Reinstall/removal, exact preservation, duplicate/edited block rejection, missing runtime and concurrent instruction-file change. |
| Real installation | 22 selective cases: 11 skills × symlink/copy, reinstall, source removal and uninstall. |

The first independent review found migrated-Git identity and nested non-Git enrollment defects. The same review identified unresolved post-delivery follow-ups and released-predecessor aggregation. All four fixes and regression checks are part of the delivered validation, rather than relying only on the initial passing tests.

## Context and latency

`scripts/benchmark.py` measures operation calls, input/output JSON characters, subprocess wall-clock latency, snapshot bytes and skill metadata/body characters. Character counts are not tokenizer measurements. It includes five participants, three delivered, one blocked, one active and ten knowledge records. A compact consolidation contains the last outcome per participant and all claims; full history requires an explicit query.

The initial measured run used Python 3.9.6, Node v26.4.0 and skills CLI 1.5.23 on macOS. The CLI matrix completed in about 13 seconds. Runtime measurements and final rerun results are recorded in [verification.json](verification.json). These are single-machine observations, not throughput or large-history guarantees.

## Model behavior and limits

A separate forward test gave GPT-5.6 Luna at medium effort only installed skills and a temporary shared project, asked it to add an independent document and prepare an editor handoff, then inspected its actual writes and checkpoints. It also asked how to route a generic checkpoint question without executing it. Luna used six runtime invocations during execution and one read-only verification after resumption. A second test gave GPT-6 Astra at xhigh effort only the installed host rule as the continuity trigger; it used nine runtime invocations. Both preserved the other writer's claim, saved usable checkpoints and identified the pending work. These different entry contexts are not a performance comparison. The observed results are recorded with the final verification data. [Behavioral cases](../tests/behavior-cases.json) also define negative PR-mention and plain-explanation triggers and explicit review/artifact requests; only cases actually executed are reported as measured. This is one bounded behavioral sample, not a guarantee across all models or hosts.

Skill wording follows [OpenAI's Astra guidance](https://developers.openai.com/api/docs/guides/latest-model) on instruction sensitivity and proportionate clarification/testing, while keeping persistent contracts model-neutral. Progressive discovery follows [Build skills](https://learn.chatgpt.com/docs/build-skills) and the [Agent Skills specification](https://agentskills.io/specification). Packaging was checked against the [official skills CLI](https://github.com/vercel-labs/skills), including independent copy installation.

Not measured: broad repeated Astra/Luna behavioral reliability, other smaller models, actual model-token costs, Windows writes, network filesystems, automatic cross-machine sync, public indexing, remote updates of unpublished versions or real user-state migration. Claims are cooperative; code cannot stop an agent that ignores the host rule. Review actual files before consolidation even when the recorded contributions appear complete.
