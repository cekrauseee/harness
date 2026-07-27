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
INIT = ROOT / "skills/harness-init/scripts/init.py"
HOOK = ROOT / "skills/harness-init/scripts/hook_adapter.py"
RECALL = ROOT / "skills/harness-recall/scripts/recall.py"
REMEMBER = ROOT / "skills/harness-remember/scripts/remember.py"
SESSION = ROOT / "skills/harness-session/scripts/session.py"


def timestamp(days: int = 0) -> str:
    return (
        dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=days)
    ).replace(microsecond=0).isoformat()


class CoreRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.env = dict(
            os.environ,
            CODEX_HOME=str(self.root / "codex"),
            HARNESS_HOME=str(self.root / "harness"),
            HARNESS_SKIP_HOOK_INSTALL="1",
        )
        self.initialized = self.run_json(
            INIT, "init", "--project", str(self.project), "--json"
        )
        self.project_id = self.initialized["project"]["id"]
        self.base = Path(self.initialized["project_dir"])

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def command(
        self,
        script: Path,
        *arguments: str,
        env: dict[str, str] | None = None,
        input_json: dict | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(script), *arguments],
            env=env or self.env,
            input=json.dumps(input_json) if input_json is not None else None,
            capture_output=True,
            text=True,
        )

    def run_json(self, script: Path, *arguments: str, **kwargs: object) -> dict:
        result = self.command(script, *arguments, **kwargs)
        self.assertEqual(0, result.returncode, result.stderr)
        return json.loads(result.stdout)

    def write_json(self, path: Path, value: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def test_missing_git_is_silent_for_optional_probes(self) -> None:
        project = self.root / "without-git"
        project.mkdir()
        env = dict(self.env, PATH="")
        initialized = self.command(
            INIT, "init", "--project", str(project), "--json", env=env
        )
        self.assertEqual(0, initialized.returncode, initialized.stderr)
        hook = self.command(
            HOOK,
            "event",
            "session-start",
            "--json",
            env=env,
            input_json={"cwd": str(self.root / "unregistered")},
        )
        self.assertEqual({"continue": True}, json.loads(hook.stdout))
        unregistered = self.root / "unregistered"
        unregistered.mkdir(exist_ok=True)
        for script, arguments in (
            (RECALL, ("--query", "anything", "--budget-tokens", "100")),
            (REMEMBER, ("list", "--status", "active")),
            (SESSION, ("list", "--status", "active")),
        ):
            result = self.command(
                script,
                "--project",
                str(unregistered),
                "--json",
                *arguments,
                env=env,
            )
            self.assertEqual(2, result.returncode, (script, result.stderr))
            self.assertNotIn("Traceback", result.stderr)

    def test_ambiguous_host_is_rejected_and_hook_ignores_it(self) -> None:
        other = self.root / "other"
        other.mkdir()
        second = self.run_json(INIT, "init", "--project", str(other), "--json")
        binding = {
            "host": "codex",
            "type": "host",
            "value": "shared-host-project",
        }
        for manifest_path in (
            self.base / "manifest.json",
            Path(second["project_dir"]) / "manifest.json",
        ):
            manifest = json.loads(manifest_path.read_text())
            manifest["bindings"].append(binding)
            self.write_json(manifest_path, manifest)
        for script, command in (
            (RECALL, ("search", "--query", "anything")),
            (REMEMBER, ("list", "--status", "active")),
            (SESSION, ("list", "--status", "active")),
        ):
            result = self.command(
                script,
                "--project",
                str(self.root),
                "--host",
                "codex",
                "--host-project-id",
                "shared-host-project",
                "--json",
                *command,
            )
            self.assertEqual(2, result.returncode, (script, result.stderr))
            self.assertIn("Ambiguous Harness host binding", result.stderr)
        old_files = []
        for base in (self.base, Path(second["project_dir"])):
            path = base / "workspace/old.txt"
            path.write_text("keep", encoding="utf-8")
            old = dt.datetime.now().timestamp() - 30 * 86400
            os.utime(path, (old, old))
            old_files.append(path)
        hook = self.run_json(
            HOOK,
            "event",
            "session-start",
            "--json",
            input_json={
                "cwd": str(self.root),
                "host": "codex",
                "host_project_id": "shared-host-project",
            },
        )
        self.assertEqual({"continue": True}, hook)
        self.assertTrue(all(path.exists() for path in old_files))
        unbound = self.root / "unbound"
        unbound.mkdir()
        conflict = self.command(
            INIT,
            "init",
            "--project",
            str(unbound),
            "--host",
            "codex",
            "--host-project-id",
            "shared-host-project",
            "--json",
        )
        self.assertEqual(2, conflict.returncode)
        link_conflict = self.command(
            INIT,
            "link",
            "--project",
            str(unbound),
            "--project-id",
            self.project_id,
            "--host",
            "codex",
            "--host-project-id",
            "shared-host-project",
            "--json",
        )
        self.assertEqual(2, link_conflict.returncode)

    def test_session_ids_cannot_overwrite_other_statuses(self) -> None:
        identifier = str(uuid.uuid4())
        closed = self.base / f"sessions/closed/{identifier}.json"
        self.write_json(closed, {
            "id": identifier,
            "status": "closed",
            "task": "completed work",
        })
        start = self.command(
            SESSION,
            "--project",
            str(self.project),
            "--json",
            "start",
            "--session-id",
            identifier,
            "--task",
            "new work",
        )
        self.assertEqual(2, start.returncode)
        self.assertEqual("completed work", json.loads(closed.read_text())["task"])

        active_id = str(uuid.uuid4())
        self.run_json(
            SESSION,
            "--project",
            str(self.project),
            "--json",
            "start",
            "--session-id",
            active_id,
            "--task",
            "active work",
        )
        collision = self.base / f"sessions/closed/{active_id}.json"
        self.write_json(collision, {
            "id": active_id,
            "status": "closed",
            "task": "older closed work",
        })
        transition = self.command(
            SESSION,
            "--project",
            str(self.project),
            "--json",
            "close",
            "--session-id",
            active_id,
        )
        self.assertEqual(2, transition.returncode)
        self.assertTrue((self.base / f"sessions/active/{active_id}.json").exists())
        self.assertEqual(
            "older closed work", json.loads(collision.read_text())["task"]
        )

    def test_parser_literals_phrase_scoring_catalog_and_recency(self) -> None:
        for literal in ("search", "hydrate"):
            legacy = self.command(
                RECALL,
                "--project",
                str(self.project),
                "--query",
                literal,
                "--budget-tokens",
                "200",
                "--json",
            )
            self.assertEqual(0, legacy.returncode, legacy.stderr)
        literal_path = self.root / "search"
        literal_path.mkdir()
        self.run_json(INIT, "init", "--project", str(literal_path), "--json")
        path_result = self.command(
            RECALL,
            "--project",
            str(literal_path),
            "--query",
            "nothing",
            "--budget-tokens",
            "200",
            "--json",
        )
        self.assertEqual(0, path_result.returncode, path_result.stderr)

        records = [
            (
                "OAuth migration",
                "Auth rollout plan",
                timestamp(-100),
            ),
            (
                "Authentication migration",
                "Auth rollout plan",
                timestamp(),
            ),
        ]
        ids = []
        for title, summary, updated in records:
            identifier = str(uuid.uuid4())
            ids.append(identifier)
            self.write_json(
                self.base / f"sessions/closed/{identifier}.json",
                {
                    "artifact_refs": [],
                    "id": identifier,
                    "read_when": "when planning auth",
                    "schema_version": 2,
                    "status": "closed",
                    "summary": summary,
                    "tags": ["auth"],
                    "task": summary,
                    "title": title,
                    "updated_at": updated,
                },
            )
        result = self.run_json(
            RECALL,
            "--project",
            str(self.project),
            "--json",
            "search",
            "--query",
            "auth",
            "--limit",
            "10",
            "--budget-tokens",
            "1000",
        )
        by_id = {entry["id"]: entry for entry in result["entries"]}
        self.assertLess(by_id[ids[0]]["score"], 24)
        self.assertGreater(by_id[ids[1]]["score"], by_id[ids[0]]["score"])

        memory_id = str(uuid.uuid4())
        self.run_json(
            REMEMBER,
            "--project",
            str(self.project),
            "--json",
            "candidate",
            "--id",
            memory_id,
            "--topic",
            "private-detail",
            "--title",
            "Unrelated card",
            "--summary",
            "No hidden keyword here.",
            "--content",
            "content-only-needle",
        )
        self.run_json(
            REMEMBER,
            "--project",
            str(self.project),
            "--json",
            "consolidate",
            "--candidate-id",
            memory_id,
            "--classification",
            "topic",
        )
        hidden = self.run_json(
            RECALL,
            "--project",
            str(self.project),
            "--json",
            "search",
            "--query",
            "content-only-needle",
            "--budget-tokens",
            "500",
        )
        self.assertEqual([], hidden["entries"])
        catalog = [
            json.loads(line)
            for line in (self.base / "memory/catalog.jsonl").read_text().splitlines()
        ]
        self.assertTrue(any(row["kind"] == "session" for row in catalog))
        self.assertTrue(all("content" not in row for row in catalog))

    def test_supersede_is_recoverable_and_retry_is_idempotent(self) -> None:
        old_id = str(uuid.uuid4())
        new_id = str(uuid.uuid4())
        for identifier, content in (
            (old_id, "old policy"),
            (new_id, "new policy"),
        ):
            self.run_json(
                REMEMBER,
                "--project",
                str(self.project),
                "--json",
                "candidate",
                "--id",
                identifier,
                "--topic",
                "policy",
                "--content",
                content,
            )
            if identifier == old_id:
                self.run_json(
                    REMEMBER,
                    "--project",
                    str(self.project),
                    "--json",
                    "consolidate",
                    "--candidate-id",
                    identifier,
                    "--classification",
                    "topic",
                )
        candidate = json.loads(
            (self.base / f"memory/candidates/{new_id}.json").read_text()
        )
        simulated_replacement = {
            "artifact_refs": [],
            "confidence": "medium",
            "content": candidate["content"],
            "created_at": timestamp(),
            "id": new_id,
            "last_verified_at": timestamp(),
            "read_when": candidate["read_when"],
            "review_after": timestamp(90),
            "schema_version": 2,
            "source_session": "",
            "status": "active",
            "summary": candidate["summary"],
            "supersedes": old_id,
            "tags": [],
            "title": candidate["title"],
            "topic": "policy",
            "updated_at": timestamp(),
        }
        self.write_json(
            self.base / f"memory/topics/policy/{new_id}.json",
            simulated_replacement,
        )
        first = self.run_json(
            REMEMBER,
            "--project",
            str(self.project),
            "--json",
            "consolidate",
            "--candidate-id",
            new_id,
            "--classification",
            "topic",
            "--supersedes",
            old_id,
        )
        self.assertEqual(old_id, first["result"]["memory"]["supersedes"])
        self.assertFalse(
            (self.base / f"memory/topics/policy/{old_id}.json").exists()
        )
        self.assertTrue(
            (self.base / f"memory/topics/policy/{new_id}.json").exists()
        )
        archived = json.loads(
            (self.base / f"memory/archive/memory-{old_id}.json").read_text()
        )
        self.assertEqual(new_id, archived["superseded_by"])
        retry = self.run_json(
            REMEMBER,
            "--project",
            str(self.project),
            "--json",
            "consolidate",
            "--candidate-id",
            new_id,
            "--classification",
            "topic",
            "--supersedes",
            old_id,
        )
        self.assertTrue(retry["result"]["idempotent"])


if __name__ == "__main__":
    unittest.main()
