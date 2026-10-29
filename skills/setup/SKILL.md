---
name: setup
description: Prepare or repair the local Harness installation and its host integration.
---

# Setup

Harness is a local plugin with one shared CLI. Its executable is `bin/harness` at the plugin root, two directories above this skill. It needs Python 3.11+ and runs without pip dependencies. If the launcher cannot find Python, use an installed maintained interpreter through `HARNESS_PYTHON` or help install that prerequisite within the user's requested setup.

Run the plugin's `bin/harness setup --host codex` for Codex or local ChatGPT, or `--host claude` for Claude Code. Setup preserves unrelated host configuration, installs the owned global instruction block, disables native memory for that host, and prepares `~/.harness/bin/harness`. No environment is created by setup.

Use `harness doctor` to inspect prerequisites. Provider login and native hook trust remain host-controlled; report a concrete missing prerequisite instead of claiming setup completed it. Existing authorization covers routine idempotent preparation; do not ask again for each directory or owned configuration update.

Ordinary record mutations prepare missing data automatically. Use this setup flow when installation, integration, or repair is the task. See [installation](../../docs/installation.md) for supported surfaces and marketplace commands.
