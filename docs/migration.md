# Migrating a legacy installation

Harness 0.6 reads schema 3 snapshots. It does not run the old per-skill scripts or treat old execution defaults as current policy. An existing legacy manifest requires an explicit migration before normal initialization can proceed.

Migration is a whole-home operation over `HARNESS_HOME`, normally `~/.harness`. A project selector does not narrow it. The importer supports the schema 1 and 2 manifests, session records and memory records used by Harness 0.5. Project IDs must be canonical UUIDs matching their directory names. Nonempty session and memory IDs are preserved when unique; duplicate or missing IDs receive deterministic mappings with source references. Every duplicate occurrence remains distinct.

## Skill names after the split

| Old entry | Replacement |
| --- | --- |
| `harness-init`, `harness-recall`, `harness-remember` | Retained names with the new standalone runtime. |
| `harness-session` | `harness-task`; outcomes and participants replace manual session closure. |
| `harness-audit` | `harness-maintain`. |
| `harness-orchestrate` | Removed; shared responsibility belongs to tasks and the host decides delegation. |
| Commit, PR, review, worktree, docs and artifact skills | The separate Workflows plugin's six `workflow-*` entries. |

Inspect and remove recognized old copies before installing replacements; check every host's visible skill list so old and new instructions do not compete. Preserve manually edited copies for explicit reconciliation. Installation of the new package does not remove old names automatically.

## Preview and apply

Use the runtime launcher from an installed new Harness skill. These examples use a repository checkout:

```bash
python3 skills/harness-init/scripts/harness.py migrate.preview
```

Preview is read-only. It returns the complete file inventory and SHA-256 fingerprint, project counts, inactive edited defaults, references needing reassessment, and exact managed files proposed for removal. It does not save a backup, lock, receipt or state file. Invalid source data produces a structured error instead of silently skipping a project.

Before applying, stop every old Harness agent, hook and script that can access this home. The new operating-system lock cannot coordinate with the old directory locks. The acknowledgement is required even when the old files appear idle. Review the preview and apply with its fingerprint:

```bash
python3 skills/harness-init/scripts/harness.py migrate.apply --data '{"fingerprint":"<preview fingerprint>","old_agents_stopped":true}'
```

Apply verifies the source again under the new runtime lock, copies all regular files byte for byte and retains empty directories in an external backup, verifies the copy, then writes canonical snapshots atomically. The backup lives beside the Harness home under `.<home-name>-migration-backups/migrate-<unique-id>/`. It includes `source/` and a `backup.json` transaction record. Do not place backup material in a target project repository or remove it before inspecting the result.

Each project receives `projects/<project-id>/state.json` with schema 3 and defaults version 7. Its import provenance includes the source fingerprint and backup directory. Every imported record includes its original source or a reference to its bytes. Legacy files remain in place except for the exact managed execution defaults described below. Files changing during backup or application cause an explicit error and retain recovery evidence; they are not silently merged.

Reapplying the same fingerprint returns the completed import without replacing subsequent schema 3 writes. Running a fresh preview after a completed import reports the projects as already migrated. Added or edited legacy files after migration require inspection; continuing to run the old scripts is unsupported.

## What the import means

- Each legacy session becomes a task, participant and checkpoint. Tasks and participants begin `blocked` with presence unknown. Original lifecycle status, summaries, pending next steps and artifact references remain available. A legacy `closed` value does not establish delivery, user acceptance, a commit or publication.
- Every legacy memory becomes `historical` and `stale`. Original confidence, candidate dispositions, pending promotion, session relationships and supersession fields remain in source provenance. These assertions have not been verified by migration. Reclassify useful knowledge explicitly through the new memory operations.
- Project Markdown becomes searchable historical reference content with its original and backup paths. Global query aliases are retained and relevant memory aliases are expanded. Local overrides and other global standards retain checksummed references. None of these files becomes a new host instruction or execution rule.
- Path and host bindings are retained after validation. Git remotes remain reference data; they do not establish identity. Imported workspace presence and Git topology remain unverified. Run `resolve` for the current checkout and inspect `maintain` before continuing work.
- Catalogs are derived data. A malformed legacy catalog is reported and backed up; authoritative session and memory files are still imported. Unknown files are preserved in the full backup, not interpreted as new runtime records.

Ambiguous or overlapping bindings across projects, malformed authoritative JSON, duplicate JSON keys, unsupported or future schemas, inconsistent project IDs, relative path bindings, non-UTF-8 Markdown, symlinks and special files require explicit repair or manual migration. The importer does not guess identity, merge duplicate records, traverse links or discard unknown data. It supports ordinary files and directories, not filesystem snapshots, extended attributes or special-file restoration.

## Execution defaults

After all canonical project snapshots are durable, apply removes only byte-identical known Harness defaults for `standards/commits.md`, `standards/branches.md`, `standards/worktrees.md`, `standards/pull-requests.md` and each project's `worktrees/policy.toml`. Their bytes remain in the external backup. Recognition is limited to the bundled immutable defaults-version-6 fingerprints; it is not based on filename alone.

Edited versions are retained and reported as inactive legacy data. `overrides/` files remain intact. The new runtime does not load either set as policy. Moving execution workflows to a separate package and installing the new host instruction block are separate installation steps; state migration does not edit host configuration or project instructions.

## Guarded restore

Stop the old agents again and supply the returned backup directory:

```bash
python3 skills/harness-init/scripts/harness.py migrate.restore --data '{"backup_dir":"<returned backup directory>","old_agents_stopped":true}'
```

Restore verifies every backed-up checksum before making changes. It restores the original files and removes snapshots introduced by this migration only when current files still match the recorded pre-migration or post-migration bytes. This also supports a partially interrupted apply or restore. Added files, changed schema 3 records, missing previously existing files or other conflicting edits block restoration. No force option discards newer work. Preserve that work and reconcile the files manually if the guard reports a conflict.

The backup remains after restore. Repeating an already completed restore is harmless. The transient `.runtime.lock` is excluded from the legacy inventory and may remain after any write operation.

## Legacy skills and hooks

Installation inspection and cleanup are separate from state migration. Pass explicit skill roots and hook configuration files; an empty scan does not search the machine:

```bash
python3 skills/harness-init/scripts/harness.py legacy.scan --data '{"skill_roots":["/absolute/path/to/skills"],"hook_files":["/absolute/path/to/hooks.json"]}'
```

The scan compares the entire file set of each known legacy skill name with the bundled fingerprints. Edited skills, extra personal files and unknown versions remain untouched. Hook recognition requires the exact known command shape, timeout and matching adapter bytes. A path marker alone is insufficient. Older variants or missing adapters are reported for manual inspection.

After reviewing the scan and authorizing changes to those installation paths, stop old agents and opt in explicitly:

```bash
python3 skills/harness-init/scripts/harness.py legacy.clean --data '{"skill_roots":["/absolute/path/to/skills"],"hook_files":["/absolute/path/to/hooks.json"],"fingerprint":"<scan fingerprint>","old_agents_stopped":true}'
```

Cleanup first backs up matching skill directories and original hook files, rechecks the scan, removes only recognized hook handlers, and atomically moves exact legacy skill directories into quarantine. Unrelated handlers within mixed groups and other configuration values remain. Skill quarantine requires the installation and backup to share a filesystem; other layouts need manual removal. The returned quarantine directory contains `cleanup.json`, file backups and the original skill directories. Cleanup recovery is manual from these copies; `migrate.restore` restores state migrations only. Host application settings that refer to separately installed plugins may still require removal through that host's installation controls.

The fingerprint assets in [the runtime source](../src/harness_runtime/legacy/fingerprints.json) record the immutable source revision used for recognition. No installed legacy code is executed to determine whether it is managed.
