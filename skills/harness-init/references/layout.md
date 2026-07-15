# Global layout

Harness state is local to the user and independent of the agent host.

```text
${HARNESS_HOME:-~/.harness}/
  adapters/
  charter.md
  managed.json
  standards/
  overrides/
  projects/
    <uuid>/
      manifest.json
      index.md
      project.md
      decisions.md
      memory/
        candidates/
        topics/
        archive/
        catalog.jsonl
      sessions/
        active/
        closed/
      references/
        product/
        technical/
        operations/
        investigations/
      workspace/
        policy.json
        policy.local.json (optional)
      worktrees/
        policy.toml
```

The repository contains no Harness-owned file. Its local Git configuration contains the only pointer:

```text
harness.project-id=<uuid>
```

`manifest.json` records known repository paths and remote URLs for deterministic hook resolution. A remote match may relink a clone only when it identifies exactly one Harness project.

Harness refreshes managed defaults when their packaged version changes. User overrides stay separate under `overrides/` and `workspace/policy.local.json`.
