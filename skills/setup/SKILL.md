---
name: setup
description: Prepare or repair the local Harness installation and its host integration.
---

# Setup

Harness is a local plugin with one shared CLI. Its executable is `bin/harness` at the plugin root, two directories above this skill. It needs Python 3.11+ and runs without pip dependencies. If the launcher cannot find Python, use an installed maintained interpreter through `HARNESS_PYTHON` or help install that prerequisite within the user's requested setup.

Run the plugin's `bin/harness setup --host codex` for Codex or local ChatGPT, or `--host claude` for Claude Code. Setup preserves unrelated host configuration, installs the owned global instruction block, disables native memory for that host, and prepares `~/.harness/bin/harness`. The Codex target also upserts the two Harness lifecycle hooks in `~/.codex/hooks.json`; the result identifies that file as `hook_file`. Claude uses its bundled hooks. No environment is created by setup.

Verify that `SessionStart` and `PostToolUse` appear in the native hook list after setup. Registration, native trust, and execution are distinct checks; do not infer any of them solely from a successful plugin install. For Codex, the user reviews the exact Harness commands through `/hooks` or desktop hook settings. Report an untrusted state precisely; do not edit trust records or bypass review. Rerun setup after upgrades to repair missing registrations without duplicating hooks or replacing unrelated ones.

Use `harness doctor` to inspect prerequisites. Provider login and native hook trust remain host-controlled; report a concrete missing prerequisite instead of claiming setup completed it. Existing authorization covers routine idempotent preparation; do not ask again for each directory or owned configuration update.

When upgrading an existing installation, refresh the owned global instructions through setup. Inspect `config show`; if it contains obsolete `profiles` or `defaults`, remove only those fields from an input copy and apply it with `config write --file FILE --revision HASH`. Preserve limits and unrelated settings. Model choices belong to individual assignments; do not recreate global role mappings. Adapt saved workflows only when needed for a new execution, using the [upgrade guidance](../../docs/installation.md#updates).

Ordinary record mutations prepare missing data automatically. Use this setup flow when installation, integration, or repair is the task. See [installation](../../docs/installation.md) for supported surfaces and marketplace commands.
