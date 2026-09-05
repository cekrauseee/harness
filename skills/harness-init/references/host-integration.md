# Host integration

Skill discovery provides capabilities; the host instruction block supplies the lifecycle trigger. Harness does not assume every model will follow it. Scripts guarantee persistence and coordination when invoked, while the host must load the rule and the agent must register semantic outcomes. No hooks, daemon or paid API are needed.

## Install deliberately

Install the skills first. Select the instruction file actually read by the host: for example `~/.codex/AGENTS.md` for Codex or `~/.claude/CLAUDE.md` for Claude Code. Other hosts may use another file. Use an absolute installed runtime path, not the development checkout or a temporary skills-use directory. The CLI fills `runtime` from its own entrypoint unless one is provided.

```bash
python3 /installed/harness-init/scripts/harness.py integration.preview --data '{"file":"/path/to/host/AGENTS.md"}'
```

Review the returned block and `expected_sha256`. Only when modification of that instruction file is authorized:

```bash
python3 /installed/harness-init/scripts/harness.py integration.install --data '{"file":"/path/to/host/AGENTS.md","expected_sha256":"<preview-value>"}'
python3 /installed/harness-init/scripts/harness.py integration.status --data '{"file":"/path/to/host/AGENTS.md"}'
```

Status reports the stored runtime path, whether it exists and whether it matches the selected runtime. Reinstalling the same block is a no-op. A changed file requires a new preview. Modified, duplicate or malformed blocks are reported instead of overwritten. Unrelated instructions and file permissions are preserved.

To remove the integration, inspect status and supply its current `sha256` as `expected_sha256` to `integration.remove`. Only the intact managed block is removed. Remove the block before uninstalling its runtime, or reinstall it to another retained skill's runtime. Every Harness skill carries the same command interface.

## Lifecycle

The block routes substantive entry/resume to a compact coordination report, shared writes to atomic scope registration, and meaningful outcomes/blockers/delivery to checkpoints. Knowledge recall is selective. Generic questions create no administrative session. Delivery releases the participant's scope and preserves pending acceptance or publication; the user need not close sessions.

When consolidating work, reserve the workspace through a `.` claim and inspect real files. Claims coordinate participating agents only. They cannot prevent an editor or agent outside the protocol from changing files. Presence age never proves a writer has stopped.

No automatic global instruction changes happen during skill installation, initialization or updates. Without invocations, no background maintenance occurs.
