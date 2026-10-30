# Architecture

Harness separates cognitive guidance, persistent human context, and mechanical execution. The public CLI is the stable boundary agents use; internal modules can evolve without spreading storage knowledge into every skill.

| Module | Ownership |
| --- | --- |
| `cli`, `presentation` | Argument and result contracts, concise human output, structured agent output. |
| `config`, `setup` | Operational settings, idempotent storage preparation, owned host integration. |
| `selection` | Validate and expose an agent's explicit model choice without choosing or ranking models. |
| `files`, `context`, `memory` | Scoped resources and Markdown, optimistic revisions, textual retrieval. |
| `database`, `access` | Operational transactions and managed participant identity/scope checks. |
| `workflows`, `runs` | Graph definitions, explicit decisions, run/participant lifecycle, shared limits. |
| `processes`, `providers` | Local supervision, process-group cleanup, CLI transport adapters. |
| `messages`, `hooks` | Durable communication, receipts, lifecycle notification. |

The runtime uses Python 3.11+ and its standard library. `bin/harness` locates an interpreter and executes the installed plugin directly. There is no runtime package installation, network server, ORM, or provider SDK.

Markdown is canonical for human records. Locks protect compare-and-replace updates; atomic filesystem replacement prevents partial documents. SQLite transactions protect operational reservations and decisions. Database transactions do not make external process creation atomic; launch intent, process identity, stdin release, and recovery handle that boundary explicitly.

Skills are grouped conceptually into context, engineering, and coordination. Each lives in a standard discoverable folder. References contain substantial conditional procedures; shared CLI documentation avoids duplicated scripts and schema descriptions. Global instructions establish the environment and general behavior rather than loading every process.

Future changes should preserve observable tool contracts or version them intentionally. Add a provider adapter when its CLI can meet the declared process and permission contracts. Add workflow events only when their authority, state transitions, and recovery semantics are defined. Add retrieval complexity when actual memory usage demonstrates a need. Do not add a generic storage or workflow abstraction speculatively.
