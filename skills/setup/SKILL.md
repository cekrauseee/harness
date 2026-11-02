---
name: setup
description: Prepare or repair the local Harness installation and its host integration.
---

# Setup

Harness is a local plugin with one shared CLI. Its executable is `bin/harness` at the plugin root, two directories above this skill. It needs Python 3.11+ and runs without pip dependencies. If the launcher cannot find Python, use an installed maintained interpreter through `HARNESS_PYTHON` or help install that prerequisite within the user's requested setup.

Run the plugin's `bin/harness setup --host HOST` with the target documented for the current host in [installation](../../docs/installation.md). Setup preserves unrelated host configuration, removes legacy Harness blocks from global instruction files, disables native memory for that host, and prepares `~/.harness/bin/harness`. Context comes from the session-start hook; setup does not create global instruction files. If removing a legacy block leaves only whitespace, setup removes that file. Host integration either registers the lifecycle hooks and returns `hook_file`, or uses the plugin's bundled hooks. No environment is created by setup.

Verify that `SessionStart` and `PostToolUse` appear in the native hook list after setup. Registration, native trust, and execution are distinct checks; do not infer any of them solely from a successful plugin install. The user reviews the exact Harness commands through the host's hook settings. Report an untrusted state precisely; do not edit trust records or bypass review. Rerun setup after upgrades to repair missing registrations and remove legacy instruction blocks without duplicating hooks or replacing unrelated ones.

Use `harness doctor` to inspect prerequisites. Provider login and native hook trust remain host-controlled; report a concrete missing prerequisite instead of claiming setup completed it. Existing authorization covers routine idempotent preparation; do not ask again for each directory or owned configuration update.

When upgrading an existing installation, refresh the launcher and migrate legacy instruction blocks through setup. Inspect `config show`; if it contains obsolete `profiles` or `defaults`, remove only those fields from an input copy and apply it with `config write --file FILE --revision HASH`. Preserve limits and unrelated settings. Model choices belong to individual assignments; do not recreate global role mappings. Adapt saved workflows only when needed for a new execution, using the [upgrade guidance](../../docs/installation.md#updates).

Ordinary record mutations prepare missing data automatically. Use this setup flow when installation, integration, or repair is the task. See [installation](../../docs/installation.md) for supported surfaces and marketplace commands.
