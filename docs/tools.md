# Tools

The common command is `harness`. Before shell `PATH` configuration, use `~/.harness/bin/harness`; before setup, use the plugin's `bin/harness`.

Global options precede the command:

```sh
harness --json --environment storefront --work checkout memory search --query retries
```

`--json` returns either `{"ok":true,"data":...}` or `{"ok":false,"error":{"code":...,"message":...,"hint":...}}`. Success exits 0; contract/operation failures exit 2; interruption exits 130. Human errors go to stderr. `--plain` disables presentation color; `NO_COLOR` is also respected.

## Command families

| Family | Operations |
| --- | --- |
| `setup`, `doctor` | Prepare storage/optional host instructions and hooks; inspect prerequisites. |
| `environment` | `ensure`, `list`, `show`, `archive`. |
| `work` | `create`, `list`, `show`, `archive`. |
| `resource` | `add`, `list`, `remove` scoped to an environment. Removing a binding does not delete its external resource. |
| `record` | `read`, `write`, `delete`, `list`, `search`. |
| `memory` | `capture`, `put`, `list`, `search`. Generic record tools provide reads and revision-aware deletion. |
| `config` | `show`, `write`, `limits`. |
| `workflow` | `template`, `create`, `read`, `write`, `validate`. |
| `run` | `start`, `list`, `status`, `wait`, `result`, `decide`, `stop`, `resume`, `recover`, `spawn`, `retry`. |
| `message` | `send`, `inbox`, `read`, `ack`. |

Use a family's `--help` for arguments. Content inputs accept `--text` or `--file`; `--file -` reads stdin. Decisions use `--reason` or `--reason-file`.

## Common operations

```sh
harness environment ensure storefront --title Storefront
harness --environment storefront resource add app --location /path/to/app --kind repository
harness --environment storefront work create checkout --title Checkout --purpose 'Improve checkout reliability.'

harness --environment storefront memory capture --title 'Retry observation' --text 'The request deadline needs a bound.' --source 'Endpoint test'
harness --environment storefront memory search --captures --query deadline
harness --environment storefront memory put checkout-deadline --file /path/to/knowledge.md
harness memory search --global --query conventions

harness record read environments/storefront/work/checkout/work.md
harness record write environments/storefront/work/checkout/work.md --file /path/to/update.md --revision PREVIOUS_HASH
harness record search --prefix environments/storefront/work/checkout --query acceptance
```

Keep authoring files outside product repositories when they are internal work artifacts. The file argument is an input to the tool; the tool owns the persisted Harness record.

`config show` returns `settings` and a `revision`. To replace settings, preserve unrelated fields in a local input copy and use `config write --file FILE --revision HASH`. A stale revision is rejected. Global settings contain operational limits, without model preferences or role mappings.

For direct tasks and helpers, `run start` and `run spawn` require `--provider`, `--model`, `--effort`, and `--reason`. `--read-only` independently restricts Harness context writes. Workflow nodes carry the same choices in their `selection` objects. `workflow template` returns an unassigned definition; `workflow create ID --file FILE` persists it only after all selections are complete. Existing runs retain their selections when definitions or global settings change.

`config limits --file FILE` changes defaults for new definitions/executions. It does not renew an existing run's budget. See [execution](execution.md) before changing workflow limits.

Managed participants inherit identity, environment, and work. The CLI checks those values and restricts record access and graph decisions to their assigned role. Do not copy credentials into prompts or output; do not unset managed context to expand scope.
