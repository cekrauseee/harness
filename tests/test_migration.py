"""Migration tests never use the real Harness home or installed skills."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from harness_runtime import core, migration


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.home = self.root / "harness"
        self.project = self.root / "project"
        self.project.mkdir()
        self.project_id = str(uuid.uuid4())
        self.session_id = str(uuid.uuid4())
        self.memory_id = str(uuid.uuid4())
        self.base = self.home / "projects" / self.project_id
        self.manifest = {"schema_version": 2, "id": self.project_id, "display_name": "Migration fixture",
                         "created_at": "2025-01-01T00:00:00+00:00", "bindings": [{"type": "path", "value": str(self.project)}]}
        self.write(self.base / "manifest.json", self.manifest)
        self.write(self.base / "sessions/closed" / (self.session_id + ".json"),
                   {"schema_version": 2, "id": self.session_id, "task": "Ship the draft", "status": "closed",
                    "summary": "Draft prepared; approval pending.", "next_step": "Ask the owner for approval",
                    "artifact_refs": ["docs/draft.md"], "created_at": "2025-01-02T00:00:00+00:00"})
        self.write(self.base / "memory/topics/architecture" / (self.memory_id + ".json"),
                   {"schema_version": 2, "id": self.memory_id, "title": "Authentication", "content": "Historical design explanation.",
                    "confidence": "high", "status": "active", "topic": "authentication", "source_session": self.session_id})
        self.write(self.home / "managed.json", {"defaults_version": 6})
        self.write(self.home / "standards/query-aliases.json", {"autenticacao": ["authentication", "auth"]})
        for relative, known in migration.KNOWN["defaults"].items():
            relative = relative.replace("projects/*", "projects/" + self.project_id)
            self.write_text(self.home / relative, known["content"])
        self.write_text(self.base / "project.md", "# Context\n\nDo not confuse a draft with approved delivery.\n")
        self.write_text(self.home / "overrides/standards/branches.md", "# Local preference\nPreserve this historical override.\n")
        self.write_text(self.base / "unrecognized.bin", b"\x00\xfflegacy bytes\r\n")
        (self.base / "empty-legacy-directory").mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def write(self, path, data):
        self.write_text(path, json.dumps(data, sort_keys=True) + "\n")

    def write_text(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text if isinstance(text, bytes) else text.encode())

    def call(self, operation, **data):
        return migration.execute(operation, data, home=self.home)

    def apply(self, preview=None):
        preview = preview or self.call("migrate.preview")
        return self.call("migrate.apply", fingerprint=preview["fingerprint"], old_agents_stopped=True)

    def assert_error(self, code, operation, **data):
        with self.assertRaises(core.HarnessError) as caught:
            self.call(operation, **data)
        self.assertEqual(code, caught.exception.code)

    def test_preview_is_read_only_and_missing_home_is_not_created(self):
        before = migration._inventory(self.home)
        result = self.call("migrate.preview")
        self.assertEqual("entire_home", result["scope"])
        self.assertEqual(before, migration._inventory(self.home))
        self.assertFalse(migration._backup_root(self.home).exists())
        missing = self.root / "nonexistent-home"
        migration.execute("migrate.preview", {}, home=missing)
        self.assertFalse(missing.exists())

    def test_apply_preserves_source_bytes_and_semantic_uncertainty(self):
        before = migration._inventory(self.home)
        preview = self.call("migrate.preview")
        result = self.apply(preview)
        backup = Path(result["backup_dir"])
        self.assertNotIn(self.home, backup.parents)
        self.assertEqual(before, migration._inventory(backup / "source"))
        state = core.read_state(core.state_path(self.home, self.project_id))
        self.assertEqual(3, state["schema_version"])
        self.assertEqual(7, state["defaults_version"])
        self.assertEqual(self.project_id, state["project"]["id"])
        self.assertEqual("blocked", state["sessions"][self.session_id]["status"])
        self.assertTrue(state["sessions"][self.session_id]["presence_unknown"])
        self.assertEqual("closed", state["sessions"][self.session_id]["legacy_status"])
        checkpoint = next(iter(state["checkpoints"].values()))
        self.assertEqual("Ask the owner for approval", checkpoint["next_action"])
        self.assertEqual(["docs/draft.md"], checkpoint["evidence"])
        memory = state["memories"][self.memory_id]
        self.assertEqual("historical", memory["kind"])
        self.assertEqual("stale", memory["status"])
        self.assertIn("autenticacao", memory["aliases"])
        self.assertEqual("high", memory["legacy_source"]["original"]["confidence"])
        self.assertTrue(Path(memory["legacy_source"]["backup_path"]).is_file())
        self.assertTrue(any("confuse a draft" in item["content"] for item in state["memories"].values()))
        self.assertFalse(state["legacy"]["policy_active"])
        for source in state["legacy"]["reference_sources"]:
            self.assertTrue(Path(source["backup_path"]).exists())
        for relative in result["removed_defaults"]:
            self.assertFalse((self.home / relative).exists())
            self.assertTrue((backup / "source" / relative).exists())
        self.assertTrue((self.home / "overrides/standards/branches.md").is_file())
        self.assertEqual((backup / "source" / "projects" / self.project_id / "unrecognized.bin").read_bytes(), b"\x00\xfflegacy bytes\r\n")

    def test_explicit_no_backup_keeps_receipt_and_repeatable_preview(self):
        preview = self.call("migrate.preview")
        with mock.patch.object(migration, "_create_backup", side_effect=AssertionError("Backup forbidden")):
            result = self.call("migrate.apply", fingerprint=preview["fingerprint"], old_agents_stopped=True, backup=False)
        self.assertIsNone(result["backup_dir"])
        self.assertFalse(migration._backup_root(self.home).exists())
        receipt = Path(result["migration_receipt"])
        self.assertEqual(["receipt.json"], [p.name for p in receipt.parent.iterdir()])
        self.assertFalse(json.loads(receipt.read_text())["backup_created"])
        state = core.read_state(core.state_path(self.home, self.project_id))
        self.assertIsNone(state["legacy"]["backup_dir"])
        self.assertNotIn("backup_path", json.dumps(state))
        self.assertEqual(self.project_id, state["project"]["id"])
        self.assertTrue(self.call("migrate.apply", fingerprint=preview["fingerprint"], old_agents_stopped=True, backup=False)["idempotent"])
        self.assertEqual("already_migrated", self.call("migrate.preview")["projects"][0]["status"])
        core.execute("task.start", {"project": str(self.project), "objective": "New work", "resources": [], "request_id": "new"}, home=self.home)
        current = core.state_path(self.home, self.project_id).read_bytes()
        self.call("migrate.apply", fingerprint=preview["fingerprint"], old_agents_stopped=True, backup=False)
        self.assertEqual(current, core.state_path(self.home, self.project_id).read_bytes())
        self.write_text(self.base / "project.md", "Concurrent legacy edit")
        self.assert_error("source_changed", "migrate.preview")

    def test_backup_option_requires_explicit_boolean(self):
        preview = self.call("migrate.preview")
        for value in ("false", None, 0):
            self.assert_error("invalid_input", "migrate.apply", fingerprint=preview["fingerprint"], old_agents_stopped=True, backup=value)
        self.assertFalse(core.state_path(self.home, self.project_id).exists())

    def test_acknowledgement_required(self):
        preview = self.call("migrate.preview")
        self.assert_error("old_agents_running", "migrate.apply", fingerprint=preview["fingerprint"])
        self.assertFalse(core.state_path(self.home, self.project_id).exists())

    def test_source_drift_refuses_apply_without_backup_or_state(self):
        preview = self.call("migrate.preview")
        self.write_text(self.base / "project.md", "Changed after preview\n")
        self.assert_error("source_changed", "migrate.apply", fingerprint=preview["fingerprint"], old_agents_stopped=True)
        self.assertFalse(core.state_path(self.home, self.project_id).exists())
        self.assertFalse(migration._backup_root(self.home).exists())

    def test_apply_is_idempotent_and_does_not_overwrite_new_v3_work(self):
        preview = self.call("migrate.preview")
        result = self.apply(preview)
        path = core.state_path(self.home, self.project_id)
        core.execute("task.start", {"project": str(self.project), "objective": "A new v3 change",
                     "resources": [], "request_id": "post-migration-work"}, home=self.home)
        before = path.read_bytes()
        repeated = self.apply(preview)
        self.assertTrue(repeated["idempotent"])
        self.assertEqual(result["backup_dir"], repeated["backup_dir"])
        self.assertEqual(before, path.read_bytes())
        fresh = self.apply()
        self.assertTrue(fresh["idempotent"])
        self.assertIsNone(fresh["backup_dir"])

    def test_old_writer_after_migration_is_detected(self):
        preview = self.call("migrate.preview")
        self.apply(preview)
        self.write_text(self.base / "legacy-late-note.md", "Old agent returned")
        self.assert_error("source_changed", "migrate.apply", fingerprint=preview["fingerprint"], old_agents_stopped=True)
        self.assert_error("source_changed", "migrate.preview")

    def test_full_restore_is_byte_preserving_and_idempotent(self):
        before = migration._inventory(self.home)
        result = self.apply()
        restored = self.call("migrate.restore", backup_dir=result["backup_dir"], old_agents_stopped=True)
        self.assertTrue(restored["restored"])
        self.assertEqual(before, migration._inventory(self.home, ignore_lock=True))
        self.assertFalse(core.state_path(self.home, self.project_id).exists())
        repeated = self.call("migrate.restore", backup_dir=result["backup_dir"], old_agents_stopped=True)
        self.assertTrue(repeated["idempotent"])

    def test_restore_refuses_new_v3_writes(self):
        result = self.apply()
        path = core.state_path(self.home, self.project_id)
        state = core.read_state(path)
        state["revision"] += 1
        core.atomic_json(path, state)
        content = path.read_bytes()
        self.assert_error("restore_conflict", "migrate.restore", backup_dir=result["backup_dir"], old_agents_stopped=True)
        self.assertEqual(content, path.read_bytes())

    def test_restore_refuses_new_files_and_tampered_backup(self):
        result = self.apply()
        self.write_text(self.home / "later.md", "Do not discard")
        self.assert_error("restore_conflict", "migrate.restore", backup_dir=result["backup_dir"], old_agents_stopped=True)
        self.assertEqual("Do not discard", (self.home / "later.md").read_text())
        self.write_text(Path(result["backup_dir"]) / "source/managed.json", "tampered")
        self.assert_error("backup_changed", "migrate.restore", backup_dir=result["backup_dir"], old_agents_stopped=True)

    def test_restore_recovers_an_interrupted_apply(self):
        before = migration._inventory(self.home)
        real_write = migration._write_bytes
        def fail_after_state(path, content, mode=0o600):
            real_write(path, content, mode)
            raise OSError("simulated crash")
        with mock.patch.object(migration, "_write_bytes", side_effect=fail_after_state):
            with self.assertRaisesRegex(OSError, "simulated crash"):
                self.apply()
        backups = list(migration._backup_root(self.home).glob("migrate-*/backup.json"))
        self.assertEqual(1, len(backups))
        self.call("migrate.restore", backup_dir=str(backups[0].parent), old_agents_stopped=True)
        self.assertEqual(before, migration._inventory(self.home, ignore_lock=True))

    def test_duplicate_sessions_and_memories_preserve_every_occurrence(self):
        source = self.base / "sessions/closed" / (self.session_id + ".json")
        original = json.loads(source.read_text())
        self.write(self.base / "sessions/active/legacy-duplicate.json", dict(original, status="active", summary="Still pending"))
        old_memory = json.loads((self.base / "memory/topics/architecture" / (self.memory_id + ".json")).read_text())
        self.write(self.base / "memory/archive/prior.json", dict(old_memory, status="archived", content="Earlier distinct content"))
        before_ids = None
        result = self.apply()
        state = core.read_state(core.state_path(self.home, self.project_id))
        self.assertEqual(2, len(state["sessions"]))
        self.assertIn(self.session_id, state["sessions"])
        self.assertEqual({"active", "closed"}, {item["legacy_status"] for item in state["sessions"].values()})
        self.assertEqual({"Historical design explanation.", "Earlier distinct content"}, {item["content"] for item in state["memories"].values() if item.get("legacy_source", {}).get("original")})
        before_ids = set(state["sessions"])
        self.call("migrate.restore", backup_dir=result["backup_dir"], old_agents_stopped=True)
        self.apply()
        state = core.read_state(core.state_path(self.home, self.project_id))
        self.assertEqual(before_ids, set(state["sessions"]))

    def test_malformed_record_and_duplicate_json_keys_are_rejected_read_only(self):
        path = self.base / "sessions/active/broken.json"
        for raw in ("{broken", '{"id":"one","id":"two"}', '{"id":"one","confidence":NaN}'):
            self.write_text(path, raw)
            before = migration._inventory(self.home)
            self.assert_error("invalid_legacy_json", "migrate.preview")
            self.assertEqual(before, migration._inventory(self.home))
            self.assertFalse(migration._backup_root(self.home).exists())

    def test_future_schema_is_rejected(self):
        for version in (3, 900, "2"):
            self.write(self.base / "manifest.json", dict(self.manifest, schema_version=version))
            self.assert_error("unsupported_legacy_schema", "migrate.preview")

    def test_ambiguous_path_and_host_bindings_are_rejected(self):
        other_id = str(uuid.uuid4())
        other = self.home / "projects" / other_id / "manifest.json"
        self.write(other, dict(self.manifest, id=other_id))
        self.assert_error("ambiguous_legacy_binding", "migrate.preview")
        primary = dict(self.manifest, bindings=[{"type": "host", "host": "Codex", "value": "shared"}])
        self.write(self.base / "manifest.json", primary)
        self.write(other, dict(primary, id=other_id))
        self.assert_error("ambiguous_legacy_binding", "migrate.preview")

    def test_relative_bindings_are_not_silently_reinterpreted(self):
        self.write(self.base / "manifest.json", dict(self.manifest, bindings=[{"type": "path", "value": "relative/project"}]))
        self.assert_error("invalid_legacy_bindings", "migrate.preview")

    def test_manual_defaults_are_preserved_and_diagnosed(self):
        custom = "# Branches\nExplicitly edited local guidance\n"
        self.write_text(self.home / "standards/branches.md", custom)
        result = self.apply()
        self.assertEqual(custom, (self.home / "standards/branches.md").read_text())
        self.assertTrue(any(f["code"] == "edited_legacy_default" for f in result["findings"]))
        self.assertNotIn("standards/branches.md", result["removed_defaults"])

    def test_symlinks_are_rejected_without_following_them(self):
        outside = self.root / "outside.txt"
        outside.write_text("preserve")
        (self.base / "link").symlink_to(outside)
        self.assert_error("unsafe_source", "migrate.preview")
        self.assertEqual("preserve", outside.read_text())

    def test_legacy_catalog_does_not_replace_authoritative_records(self):
        self.write_text(self.base / "memory/catalog.jsonl", "malformed derived catalog\n")
        result = self.apply()
        self.assertTrue(any(f["code"] == "invalid_legacy_catalog" for f in result["findings"]))
        self.assertTrue((Path(result["backup_dir"]) / "source" / "projects" / self.project_id / "memory/catalog.jsonl").is_file())

    def test_imported_state_is_usable_by_core_read_operations(self):
        self.apply()
        selection = {"project": str(self.project)}
        resolved = core.execute("resolve", selection, home=self.home)
        self.assertEqual(self.project_id, resolved["project_id"])
        recalled = core.execute("recall", dict(selection, query="autenticacao"), home=self.home)
        self.assertIn(self.memory_id, {entry["id"] for entry in recalled["entries"]})
        inspected = core.execute("task.list", selection, home=self.home)
        self.assertEqual("blocked", inspected["tasks"][0]["status"])
        core.execute("consolidate", selection, home=self.home)
        core.execute("maintain", selection, home=self.home)


class LegacyInstallationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.home = self.root / "harness"
        self.skills = self.root / "installed-skills"
        self.skill = self.skills / "harness-init"
        self.fixture_known = copy.deepcopy(migration.KNOWN)
        # Standalone fixtures with test-local fingerprints: no dependency on a Git checkout.
        self.contents = {"SKILL.md": b"---\nname: harness-init\n---\nLegacy fixture\n", "scripts/hook_adapter.py": b"# known fixture adapter\n"}
        for relative, content in self.contents.items():
            path = self.skill / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        self.fixture_known["skills"] = {"harness-init": {key: hashlib.sha256(value).hexdigest() for key, value in self.contents.items()}}
        self.fixture_known["hook_adapter_sha256"] = hashlib.sha256(self.contents["scripts/hook_adapter.py"]).hexdigest()
        self.patch = mock.patch.object(migration, "KNOWN", self.fixture_known)
        self.patch.start()
        self.hooks = self.root / "hooks.json"
        self.handler = {"type": "command", "command": f"python3 {self.skill}/scripts/hook_adapter.py event session-start", "timeout": 15}
        self.unrelated = {"type": "command", "command": "echo unrelated", "timeout": 8}
        self.config = {"other": {"preserve": True}, "hooks": {"SessionStart": [{"matcher": "*", "hooks": [self.handler, self.unrelated]}], "Stop": [{"hooks": [self.unrelated]}]}}
        self.hooks.write_text(json.dumps(self.config))

    def tearDown(self):
        self.patch.stop()
        self.temporary.cleanup()

    def scan(self):
        return migration.execute("legacy.scan", {"skill_roots": [str(self.skills)], "hook_files": [str(self.hooks)]}, home=self.home)

    def clean(self, plan):
        return migration.execute("legacy.clean", {"skill_roots": [str(self.skills)], "hook_files": [str(self.hooks)], "fingerprint": plan["fingerprint"], "old_agents_stopped": True}, home=self.home)

    def test_scan_is_read_only_and_cleanup_preserves_mixed_groups(self):
        before = self.hooks.read_bytes()
        result = self.scan()
        self.assertFalse(self.home.exists())
        self.assertEqual(before, self.hooks.read_bytes())
        self.assertTrue(result["skills"][0]["exact_known_legacy"])
        cleaned = self.clean(result)
        self.assertFalse(self.skill.exists())
        config = json.loads(self.hooks.read_text())
        self.assertEqual([self.unrelated], config["hooks"]["SessionStart"][0]["hooks"])
        self.assertEqual(self.config["hooks"]["Stop"], config["hooks"]["Stop"])
        self.assertEqual({"preserve": True}, config["other"])
        self.assertEqual(before, (Path(cleaned["quarantine_dir"]) / "hooks-0.json").read_bytes())
        self.assertTrue((Path(cleaned["quarantine_dir"]) / "skill-0-harness-init-original/scripts/hook_adapter.py").is_file())

    def test_manual_skill_and_unknown_hook_remain(self):
        with (self.skill / "SKILL.md").open("ab") as handle:
            handle.write(b"Manually edited\n")
        with (self.skill / "scripts/hook_adapter.py").open("ab") as handle:
            handle.write(b"# customized\n")
        before = self.hooks.read_bytes()
        result = self.scan()
        self.assertFalse(result["skills"][0]["exact_known_legacy"])
        self.assertEqual(0, result["hook_files"][0]["remove_handlers"])
        self.clean(result)
        self.assertTrue(self.skill.exists())
        self.assertEqual(before, self.hooks.read_bytes())

    def test_additional_manual_file_prevents_directory_cleanup(self):
        (self.skill / "personal-notes.md").write_text("Manual file")
        result = self.scan()
        self.assertFalse(result["skills"][0]["exact_known_legacy"])
        self.clean(result)
        self.assertEqual("Manual file", (self.skill / "personal-notes.md").read_text())

    def test_additional_empty_directory_is_not_assumed_managed(self):
        (self.skill / "personal-empty-directory").mkdir()
        result = self.scan()
        self.assertFalse(result["skills"][0]["exact_known_legacy"])

    def test_hook_marker_alone_is_not_proof_of_ownership(self):
        self.config["hooks"]["SessionStart"][0]["hooks"][0] = {"type": "command", "command": "echo harness-init/scripts/hook_adapter.py", "timeout": 15}
        self.hooks.write_text(json.dumps(self.config))
        result = self.scan()
        self.assertEqual(0, result["hook_files"][0]["remove_handlers"])

    def test_hook_or_skill_drift_refuses_cleanup(self):
        result = self.scan()
        (self.skill / "new.txt").write_text("Added after preview")
        with self.assertRaises(core.HarnessError) as caught:
            self.clean(result)
        self.assertEqual("source_changed", caught.exception.code)
        self.assertTrue(self.skill.exists())
        self.assertEqual(self.config, json.loads(self.hooks.read_text()))


if __name__ == "__main__":
    unittest.main()
