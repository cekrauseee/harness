# Installation

## Supported surfaces

| Surface | Support |
| --- | --- |
| Codex CLI | Local marketplace, skills, CLI, and trusted lifecycle hooks. |
| Local ChatGPT desktop / Codex desktop | The same local marketplace and executable environment; availability follows the selected local host. |
| Claude Code | Compatibility manifest, skills, CLI, and native lifecycle hooks. |
| Cloud-orchestrated ChatGPT Work | Local CLI and plugin hooks are not deployed or supported by this package. |
| Windows | Not supported by the POSIX process supervisor in this version. |

GitHub distribution does not automatically publish a plugin to the universal public directory. Native authentication, hook trust, and managed host policy remain in effect.

## Marketplace commands

Codex CLI and the local ChatGPT desktop installation share marketplace configuration:

```sh
codex plugin marketplace add cekrauseee/marketplace
codex plugin add harness@marketplace
```

Open a new Codex session. For ChatGPT desktop, restart the app if needed and open Plugins → marketplace → Harness. Run the plugin's setup action. There is no separate `chatgpt plugin install` command advertised by this package.

Claude Code:

```sh
claude plugin marketplace add cekrauseee/marketplace
claude plugin install harness@marketplace
```

Restart the session after installation. Review the hook definitions when the host asks for trust; installation alone does not grant it.

## Runtime and setup

Use Python 3.11 or newer. The launcher checks `HARNESS_PYTHON`, installed maintained Python executables, and the optional local desktop runtime location. If none is available, it exits with a concrete prerequisite message before modifying data. Install Python using your platform's normal package manager or [python.org](https://www.python.org/downloads/), then retry. No pip installation is needed for the plugin.

The setup skill resolves the installed plugin root and runs one of:

```sh
<plugin-root>/bin/harness setup --host codex
<plugin-root>/bin/harness setup --host claude
```

Setup creates the data root, shared launcher, and operational database, and disables native memory for the selected host. Harness instructions are injected by `SessionStart`; managed participant prompts receive them directly. Setup does not create or populate global instruction files. For Codex and local ChatGPT, it also registers `SessionStart` and `PostToolUse` in `~/.codex/hooks.json`. These hooks call the shared launcher, so their command remains stable across plugin updates. Setup preserves unrelated hooks and configuration. It does not create an environment, install provider CLIs, log into accounts, or bypass native hook trust.

During migration, setup removes the legacy Harness block from the selected host's global instruction file (`~/.codex/AGENTS.md` or `~/.claude/CLAUDE.md`). Content outside the owned markers is preserved. A file containing only that block and whitespace is removed; an absent file stays absent. Malformed blocks are reported without modifying the instruction file. Personalization belongs in Harness context and skills.

After Codex setup, open `/hooks` in the CLI or the desktop hook settings and review the two Harness commands. Registration and approval are separate: a discovered hook can remain untrusted and will not run until approved. Claude Code uses the hooks bundled in its compatibility manifest. Harness deliberately uses one hook source per host to avoid duplicate execution.

The `codex` target serves local Codex and ChatGPT runtime configuration. The `claude` target also clears automatic commit/PR attribution. Explicit `--host-home DIRECTORY` selects an alternate host installation for testing or managed setup. Data operations can prepare their own missing storage without requiring a manual initialization request.

`HARNESS_ROOT` selects another data root. `HARNESS_PYTHON` selects an interpreter. Use `harness doctor` to inspect local prerequisites without creating an environment.

## Updates

Version 0.0.4 prefers native agent coordination when the host can honor the assignment. Managed execution remains available for cross-host work and missing capabilities. Setup removes legacy Harness blocks from global instruction files; session hooks and managed prompts supply the context. Rerun setup for each installed host after upgrading, then start a new session to load the updated guidance.

Version 0.0.3 makes Codex hook registration an explicit setup operation. Rerun setup from the updated plugin to repair existing installations where bundled hooks were not discovered. The tool returns `hook_file` with the native file it updated. Existing unrelated hooks retain their positions and settings; malformed hook files are reported without being replaced.

Refresh the marketplace and reinstall the current plugin through the host:

```sh
codex plugin marketplace upgrade marketplace
codex plugin add harness@marketplace
```

For Claude Code, use `claude plugin marketplace update marketplace` followed by `claude plugin update harness@marketplace`. Restart the session and rerun setup to refresh the launcher and remove legacy global instruction blocks. The installed plugin supplies context through its hook or managed prompt. Harness data stays in its own root. Stop managed runs before removing a plugin version they are executing.

Version 0.0.2 replaces named model profiles with explicit choices for each assignment. During an upgrade from 0.0.1, use `config show` and `config write --file FILE --revision HASH` to remove the obsolete `profiles` and `defaults` fields while preserving operational limits and unrelated settings. They remain readable but are never used to select models. No database conversion is required; existing executions retain their frozen choices.

Saved workflows using `profile` must be updated with a `selection` containing `provider`, `model`, `effort`, and `reason` for every node and integration coordinator before a new launch. New workflows start with `workflow template`; complete the choices and persist the definition with `workflow create ID --file FILE`. Direct `run start` and `run spawn` use the equivalent flags. See [execution](execution.md).

## Sources

The installation surface follows the official [plugin packaging guide](https://developers.openai.com/plugins/build/plugins), [Codex developer commands](https://learn.chatgpt.com/docs/developer-commands), and [Claude marketplace documentation](https://code.claude.com/docs/en/plugin-marketplaces). Hook support is described in [ChatGPT and Codex plugins](https://learn.chatgpt.com/docs/plugins) and the [Codex hook reference](https://learn.chatgpt.com/docs/hooks).
