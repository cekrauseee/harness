# Harness

A local cognitive environment for agents: readable context, deliberate memory, and explicit workflows.

```text
Global instructions → Focused skills → One local CLI
                                      ├── Markdown: context and knowledge
                                      └── SQLite: execution and communication
```

Harness keeps durable knowledge outside application repositories. Environments group resources; work records preserve continuity without requiring a plan or lifecycle. Memory separates permissive capture from agent-led synthesis. Development and review workflows use configured module graphs, agent-selected models, bounded context, and finite execution limits.

## Install

For **Codex CLI and local ChatGPT desktop**, add the marketplace and install the plugin:

```sh
codex plugin marketplace add cekrauseee/marketplace
codex plugin add harness@marketplace
```

Start a new session. In ChatGPT desktop, restart the app if the marketplace does not appear, open Plugins, and select Harness from `marketplace`. Use its setup skill to prepare the host integration; the agent runs the tool. Review native hook trust when the host requests it.

For **Claude Code**:

```sh
claude plugin marketplace add cekrauseee/marketplace
claude plugin install harness@marketplace
```

Requires macOS or Linux and Python 3.11+. The plugin has no Python package dependencies. Provider CLIs are optional until a workflow uses them and require their own authentication. This is a local marketplace plugin, not a claim of listing in the universal public directory. Cloud-orchestrated ChatGPT Work cannot run these local hooks.

See [installation](docs/installation.md) for setup, supported surfaces, updates, and prerequisites.

## Use

The installed entry point is `~/.harness/bin/harness`. Add that directory to your shell's `PATH` if you want the short `harness` command. The examples below use that short name.

```sh
harness environment ensure storefront --title Storefront
harness --environment storefront resource add app --kind repository --location /path/to/storefront
harness --environment storefront work create checkout --title Checkout --purpose 'Improve checkout reliability.'
harness --environment storefront memory capture --title 'Checkout timeout' --text 'Investigate bounded retries.' --source 'Endpoint investigation'
```

Use `--json` before a command for compact agent-readable output. Tools prepare missing data when required; they do not invent environments from working directories.

| Area | Capabilities |
| --- | --- |
| Context | Environments, scoped resources, small or continuous work, revision-aware Markdown records. |
| Memory | Global/environment capture, selective textual retrieval, agent-led consolidation. |
| Execution | Explicit development/review graphs, model choices per assignment, shared limits, cancellation, recovery. |
| Communication | Persistent messages, lifecycle notifications, explicit reading and acknowledgment. |
| Guidance | Setup, context, planning, implementation, review, testing, Git, documentation, cleanup, orchestration, deliberation, handoff. |

## Documentation

- [Tools](docs/tools.md): command contracts and examples.
- [Records](docs/records.md): layout, scope, formatting, and concurrent updates.
- [Execution](docs/execution.md): graph configuration, decisions, budgets, messages, and recovery.
- [Architecture](docs/architecture.md): module responsibilities and extension points.
- [Writing guidance](docs/writing.md): concise, model-independent skill design.
- [Contributing](CONTRIBUTING.md): local development and validation.
