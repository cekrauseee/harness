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

Setup creates the data root, shared launcher, and operational database; it adds or updates an owned global instruction block and disables native memory for the selected host. It preserves unrelated configuration and does not create an environment, install provider CLIs, log into accounts, or bypass native hook trust.

The `codex` target serves local Codex and ChatGPT runtime configuration. The `claude` target also clears automatic commit/PR attribution. Explicit `--host-home DIRECTORY` selects an alternate host installation for testing or managed setup. Data operations can prepare their own missing storage without requiring a manual initialization request.

`HARNESS_ROOT` selects another data root. `HARNESS_PYTHON` selects an interpreter. Use `harness doctor` to inspect local prerequisites without creating an environment.

## Updates

Refresh the marketplace and reinstall the current plugin through the host:

```sh
codex plugin marketplace upgrade marketplace
codex plugin add harness@marketplace
```

For Claude Code, use `claude plugin marketplace update marketplace` followed by `claude plugin update harness@marketplace`. Restart the session and rerun setup to refresh the launcher to the installed version. Harness data stays in its own root. Stop managed runs before removing a plugin version they are executing.

## Sources

The installation surface follows the official [plugin packaging guide](https://developers.openai.com/plugins/build/plugins), [Codex developer commands](https://learn.chatgpt.com/docs/developer-commands), and [Claude marketplace documentation](https://code.claude.com/docs/en/plugin-marketplaces). Hook support is described in [ChatGPT and Codex plugins](https://learn.chatgpt.com/docs/plugins) and the [Codex hook reference](https://learn.chatgpt.com/docs/hooks).
