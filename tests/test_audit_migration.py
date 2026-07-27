from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "skills/harness-audit/scripts/audit.py"
RECALL = ROOT / "skills/harness-recall/scripts/recall.py"


def timestamp(days: int = 0) -> str:
    return (
        dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=days)
    ).replace(microsecond=0).isoformat()


class AuditMigrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.harness_home = self.root / "harness-home"
        self.project_path = self.root / "non-git-project"
        self.project_path.mkdir(parents=True)
        self.env = dict(os.environ, HARNESS_HOME=str(self.harness_home))
        self.project_id = str(uuid.uuid4())
        self.base = self.harness_home / "projects" / self.project_id
        self.session_id = str(uuid.uuid4())
        self.memory_id = str(uuid.uuid4())
        self.make_legacy_project()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_json(self, path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def make_legacy_project(self) -> None:
        for relative in (
            "memory/candidates", "memory/topics/architecture", "memory/archive",
            "sessions/active", "sessions/closed", "references/product",
            "references/technical", "references/operations",
            "references/investigations", "workspace", "worktrees",
        ):
            (self.base / relative).mkdir(parents=True, exist_ok=True)
        for name in ("index.md", "project.md", "decisions.md"):
            (self.base / name).write_text(f"# {name}\n", encoding="utf-8")
        (self.base / "memory/catalog.jsonl").write_text("", encoding="utf-8")
        self.write_json(self.base / "workspace/policy.json", {"max_age_days": 7})
        (self.base / "worktrees/policy.toml").write_text(
            'creation_protocol = "harness"\n', encoding="utf-8",
        )
        self.write_json(self.base / "manifest.json", {
            "created_at": timestamp(-30),
            "display_name": "non-git-project",
            "id": self.project_id,
            "remote_urls": [],
            "repository_paths": [str(self.project_path)],
            "schema_version": 1,
            "updated_at": timestamp(-30),
        })
        empty = {
            "created_at": timestamp(-40),
            "id": self.session_id,
            "status": "active",
            "task": "",
            "updated_at": timestamp(-40),
        }
        self.write_json(
            self.base / f"sessions/active/{self.session_id}.json", empty,
        )
        closed = dict(
            empty,
            status="closed",
            summary="A prior occurrence was completed.",
            updated_at=timestamp(-20),
        )
        self.write_json(
            self.base / f"sessions/closed/{self.session_id}.json", closed,
        )
        recent_id = str(uuid.uuid4())
        self.write_json(self.base / f"sessions/active/{recent_id}.json", {
            "created_at": timestamp(),
            "id": recent_id,
            "status": "active",
            "summary": "",
            "task": "Prepare the delivery brief",
            "updated_at": timestamp(),
        })
        self.write_json(
            self.base / f"memory/topics/architecture/{self.memory_id}.json",
            {
                "confidence": "high",
                "content": "Architecture detail. " * 400,
                "created_at": timestamp(-10),
                "id": self.memory_id,
                "last_verified_at": timestamp(-10),
                "read_when": "when changing project architecture",
                "review_after": timestamp(30),
                "source_session": "",
                "status": "active",
                "supersedes": "",
                "tags": ["architecture"],
                "topic": "architecture",
                "updated_at": timestamp(-10),
            },
        )

    def command(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(AUDIT), *args],
            env=self.env,
            text=True,
            capture_output=True,
        )
        if check and result.returncode:
            self.fail(
                f"command failed ({result.returncode}): "
                f"{result.stderr}\n{result.stdout}"
            )
        return result

    def recall(self, *args: str) -> dict:
        result = subprocess.run(
            [sys.executable, str(RECALL), *args],
            env=self.env,
            text=True,
            capture_output=True,
        )
        if result.returncode:
            self.fail(
                f"recall failed ({result.returncode}): "
                f"{result.stderr}\n{result.stdout}"
            )
        return json.loads(result.stdout)

    def test_dry_run_is_read_only_and_reports_migration_and_efficiency_risks(self) -> None:
        before_manifest = (self.base / "manifest.json").read_bytes()
        before_session = (
            self.base / f"sessions/active/{self.session_id}.json"
        ).read_bytes()
        nested = self.project_path / "documents"
        nested.mkdir()
        result = self.command(
            "--path", str(nested), "--migrate", "--dry-run", "--json",
            check=False,
        )
        payload = json.loads(result.stdout)
        self.assertGreater(payload["migration"]["projects"][0]["changes"], 0)
        self.assertIsNone(payload["migration"]["backup_dir"])
        codes = {
            item["code"] for item in payload["projects"][0]["findings"]
        }
        self.assertIn("empty-active-session", codes)
        self.assertIn("legacy-schema", codes)
        self.assertIn("oversized-memory-content", codes)
        self.assertIn("unrecallable-memory", codes)
        self.assertIn("recall-budget-overhead", codes)
        self.assertEqual(before_manifest, (self.base / "manifest.json").read_bytes())
        self.assertEqual(
            before_session,
            (self.base / f"sessions/active/{self.session_id}.json").read_bytes(),
        )
        self.assertFalse((self.harness_home / "backups").exists())

    def test_migration_is_backed_up_preserving_and_idempotent(self) -> None:
        first = json.loads(self.command(
            "--project-id", self.project_id, "--migrate", "--json",
        ).stdout)
        backup = Path(first["migration"]["backup_dir"])
        self.assertTrue(
            (backup / f"projects/{self.project_id}/manifest.json").is_file(),
        )
        self.assertTrue(
            (
                backup
                / f"projects/{self.project_id}/sessions/active/{self.session_id}.json"
            ).is_file(),
        )

        manifest = json.loads((self.base / "manifest.json").read_text())
        self.assertEqual(2, manifest["schema_version"])
        path_binding = next(
            item for item in manifest["bindings"] if item["type"] == "path"
        )
        self.assertEqual(str(self.project_path.resolve()), path_binding["value"])
        self.assertTrue(path_binding["primary"])
        self.assertEqual(
            [str(self.project_path.resolve())], manifest["repository_paths"],
        )

        self.assertFalse(
            (self.base / f"sessions/active/{self.session_id}.json").exists(),
        )
        dormant = [
            json.loads(path.read_text())
            for path in (self.base / "sessions/dormant").glob("*.json")
        ]
        live = next(item for item in dormant if item["id"] == self.session_id)
        self.assertEqual("dormant", live["status"])
        self.assertTrue(live["title"].startswith("Unlabeled session"))
        self.assertEqual([], live["artifact_refs"])
        closed = [
            json.loads(path.read_text())
            for path in (self.base / "sessions/closed").glob("*.json")
        ]
        duplicate = next(
            item for item in closed if item.get("legacy_id") == self.session_id
        )
        self.assertNotEqual(self.session_id, duplicate["id"])
        self.assertFalse(
            (self.base / f"sessions/closed/{self.session_id}.json").exists(),
        )

        memory_path = (
            self.base / f"memory/topics/architecture/{self.memory_id}.json"
        )
        memory = json.loads(memory_path.read_text())
        self.assertEqual(2, memory["schema_version"])
        self.assertEqual("architecture", memory["title"])
        self.assertTrue(memory["summary"])
        self.assertLessEqual(len(memory["summary"]), 320)
        self.assertGreater(len(memory["content"]), len(memory["summary"]))
        catalog = [
            json.loads(line)
            for line in (self.base / "memory/catalog.jsonl").read_text().splitlines()
        ]
        self.assertEqual(2, catalog[0]["schema_version"])
        self.assertEqual("memory", catalog[0]["kind"])
        self.assertEqual(memory["summary"], catalog[0]["summary"])

        second = json.loads(self.command(
            "--project-id", self.project_id, "--migrate", "--json",
        ).stdout)
        self.assertIsNone(second["migration"]["backup_dir"])
        self.assertEqual(
            0, second["migration"]["projects"][0]["changes"],
        )
        self.assertEqual(0, second["errors"])

    def test_audit_detects_invalid_bindings_duplicates_and_active_excess(self) -> None:
        self.command("--project-id", self.project_id, "--migrate", "--json")
        manifest_path = self.base / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["bindings"].append({"type": "path", "value": "relative"})
        self.write_json(manifest_path, manifest)

        for number in range(2):
            identifier = str(uuid.uuid4())
            self.write_json(
                self.base / f"sessions/active/{identifier}.json",
                {
                    "artifact_refs": [],
                    "created_at": timestamp(),
                    "id": identifier,
                    "read_when": "when preparing delivery",
                    "schema_version": 2,
                    "status": "active",
                    "summary": "Current delivery details.",
                    "tags": [],
                    "task": "Prepare delivery",
                    "title": "Delivery",
                    "updated_at": timestamp(),
                },
            )
        result = self.command(
            "--project-id", self.project_id,
            "--max-active-sessions", "1", "--json",
            check=False,
        )
        self.assertEqual(1, result.returncode)
        payload = json.loads(result.stdout)
        codes = {
            item["code"] for item in payload["projects"][0]["findings"]
        }
        self.assertIn("invalid-project-binding", codes)
        self.assertIn("duplicate-semantic-title", codes)
        self.assertIn("excess-active-sessions", codes)
        self.assertIn("oversized-memory-content", codes)

    def test_relay_shaped_state_preserves_every_record_and_canonicalizes_ids(self) -> None:
        manifest_path = self.base / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["bindings"] = [
            {"type": "host", "host": "Codex", "value": "relay-project"},
        ]
        manifest["remote_urls"] = ["https://example.test/relay.git"]
        self.write_json(manifest_path, manifest)

        duplicate_id = str(uuid.uuid4())
        common = {
            "artifact_refs": [],
            "created_at": timestamp(),
            "id": duplicate_id,
            "read_when": "when continuing Relay delivery",
            "status": "active",
            "summary": "",
            "tags": [],
            "updated_at": timestamp(),
        }
        self.write_json(
            self.base / f"sessions/active/{duplicate_id}.json",
            dict(common, task="Primary Relay handoff"),
        )
        self.write_json(
            self.base / "sessions/active/legacy-duplicate-file.json",
            dict(common, task="Secondary Relay handoff"),
        )
        self.write_json(
            self.base / "sessions/active/legacy-session.json",
            {
                "artifact_refs": "outputs/relay-plan.md",
                "created_at": timestamp(),
                "id": "relay-thread",
                "read_when": "when resuming Relay",
                "status": "active",
                "summary": "Relay work remains active.",
                "tags": "relay",
                "task": "Continue Relay",
                "updated_at": timestamp(),
            },
        )
        relay_memory = self.base / "memory/topics/relay/legacy-memory.json"
        self.write_json(relay_memory, {
            "artifact_refs": "docs/relay.md",
            "confidence": "high",
            "content": "Relay uses a durable delivery protocol.",
            "created_at": timestamp(-2),
            "id": "relay-memory",
            "last_verified_at": timestamp(-2),
            "read_when": "when changing Relay delivery",
            "review_after": timestamp(30),
            "source_session": "relay-thread",
            "status": "active",
            "summary": "Relay delivery protocol.",
            "tags": "relay",
            "title": "Relay delivery",
            "topic": "relay",
            "updated_at": timestamp(-2),
        })

        before_session_count = sum(
            len(list((self.base / "sessions" / status).glob("*.json")))
            for status in ("active", "dormant", "closed")
        )
        before_memory_count = len(list(self.base.glob("memory/**/*.json")))
        before = json.loads(self.command(
            "--project-id", self.project_id, "--json", check=False,
        ).stdout)
        before_codes = {
            item["code"] for item in before["projects"][0]["findings"]
        }
        self.assertIn("non-hydratable-record-id", before_codes)
        self.assertIn("record-path-id-mismatch", before_codes)

        migrated = json.loads(self.command(
            "--project-id", self.project_id, "--migrate", "--json",
        ).stdout)
        self.assertEqual(0, migrated["errors"])
        after_session_count = sum(
            len(list((self.base / "sessions" / status).glob("*.json")))
            for status in ("active", "dormant", "closed")
        )
        after_memory_count = len(list(self.base.glob("memory/**/*.json")))
        self.assertEqual(before_session_count, after_session_count)
        self.assertEqual(before_memory_count, after_memory_count)

        all_sessions = [
            json.loads(path.read_text())
            for status in ("active", "dormant", "closed")
            for path in (self.base / "sessions" / status).glob("*.json")
        ]
        ids = [item["id"] for item in all_sessions]
        self.assertEqual(len(ids), len(set(ids)))
        for status in ("active", "dormant", "closed"):
            for path in (self.base / "sessions" / status).glob("*.json"):
                item = json.loads(path.read_text())
                self.assertEqual(str(uuid.UUID(item["id"])), path.stem)
        converted_session = next(
            item for item in all_sessions if item.get("legacy_id") == "relay-thread"
        )
        self.assertEqual(["relay"], converted_session["tags"])
        self.assertEqual(
            ["outputs/relay-plan.md"], converted_session["artifact_refs"],
        )
        hydrated_session = self.recall(
            "--project-id", self.project_id, "--json", "hydrate",
            "--id", converted_session["id"],
        )
        self.assertIn("Continue Relay", hydrated_session["entry"]["content"])

        converted_memory_path = next(
            path
            for path in (self.base / "memory/topics/relay").glob("*.json")
            if json.loads(path.read_text()).get("legacy_id") == "relay-memory"
        )
        converted_memory = json.loads(converted_memory_path.read_text())
        self.assertEqual(str(uuid.UUID(converted_memory["id"])), converted_memory_path.stem)
        self.assertEqual(["relay"], converted_memory["tags"])
        self.assertEqual(["docs/relay.md"], converted_memory["artifact_refs"])
        hydrated_memory = self.recall(
            "--project-id", self.project_id, "--json", "hydrate",
            "--id", converted_memory["id"],
        )
        self.assertIn(
            "durable delivery protocol", hydrated_memory["entry"]["content"],
        )

        updated_manifest = json.loads(manifest_path.read_text())
        self.assertEqual(
            ["path", "git", "host"],
            [binding["type"] for binding in updated_manifest["bindings"]],
        )
        host = next(
            binding for binding in updated_manifest["bindings"]
            if binding["type"] == "host"
        )
        self.assertEqual("codex", host["host"])
        second = json.loads(self.command(
            "--project-id", self.project_id, "--migrate", "--json",
        ).stdout)
        self.assertEqual(0, second["migration"]["projects"][0]["changes"])
        self.assertIsNone(second["migration"]["backup_dir"])
        self.assertEqual(0, second["errors"])
        self.assertNotIn(
            "catalog-drift",
            {
                item["code"] for item in second["projects"][0]["findings"]
            },
        )


if __name__ == "__main__":
    unittest.main()
