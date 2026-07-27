from __future__ import annotations

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


class ProjectNativeHarnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.project = self.root / "plain-local-project"
        self.project.mkdir()
        self.env = dict(
            os.environ,
            HARNESS_HOME=str(self.root / "harness-home"),
            HARNESS_SKIP_HOOK_INSTALL="1",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def command(
        self,
        script: Path,
        *arguments: str,
        input_json: dict | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(script), *arguments],
            env=self.env,
            input=json.dumps(input_json) if input_json is not None else None,
            capture_output=True,
            text=True,
        )
        if check and result.returncode:
            self.fail(f"command failed ({result.returncode}): {result.stderr}\n{result.stdout}")
        return result

    def initialize(self, *arguments: str) -> dict:
        return json.loads(
            self.command(
                INIT,
                "init",
                "--project",
                str(self.project),
                "--json",
                *arguments,
            ).stdout
        )

    def test_non_git_project_uses_global_path_and_host_bindings(self) -> None:
        initialized = self.initialize(
            "--host", "codex", "--host-project-id", "local-workspace-17"
        )
        manifest = initialized["project"]
        self.assertEqual(2, manifest["schema_version"])
        self.assertTrue(
            any(
                item["type"] == "path"
                and Path(item["value"]) == self.project.resolve()
                for item in manifest["bindings"]
            )
        )
        self.assertTrue(
            any(
                item["type"] == "host"
                and item["host"] == "codex"
                and item["value"] == "local-workspace-17"
                for item in manifest["bindings"]
            )
        )
        nested = self.project / "deliverables" / "draft"
        nested.mkdir(parents=True)
        resolved = json.loads(
            self.command(
                INIT, "resolve", "--project", str(nested), "--json"
            ).stdout
        )
        self.assertEqual(manifest["id"], resolved["project_id"])
        self.assertEqual("path-binding", resolved["resolution"])
        by_host = json.loads(
            self.command(
                INIT,
                "resolve",
                "--project",
                str(self.root),
                "--host",
                "codex",
                "--host-project-id",
                "local-workspace-17",
                "--json",
            ).stdout
        )
        self.assertEqual(manifest["id"], by_host["project_id"])

    def test_hook_never_initializes_or_injects_context(self) -> None:
        output = json.loads(
            self.command(
                HOOK,
                "event",
                "session-start",
                "--json",
                input_json={"cwd": str(self.project), "prompt": "private prompt"},
            ).stdout
        )
        self.assertEqual({"continue": True}, output)
        self.assertFalse((self.root / "harness-home/projects").exists())
        self.initialize()
        output = json.loads(
            self.command(
                HOOK,
                "event",
                "user-prompt",
                "--json",
                input_json={"cwd": str(self.project), "prompt": "private prompt"},
            ).stdout
        )
        self.assertEqual({"continue": True}, output)

    def test_semantic_search_no_match_and_large_record_hydration(self) -> None:
        project_id = self.initialize()["project"]["id"]
        memory_id = str(uuid.uuid4())
        large = "Architectural constraint. " + ("x" * 20_000) + " unique-tail-marker"
        self.command(
            REMEMBER,
            "--project",
            str(self.project),
            "--json",
            "candidate",
            "--id",
            memory_id,
            "--topic",
            "delivery-policy",
            "--title",
            "Delivery approval boundary",
            "--summary",
            "Publishing requires explicit user approval.",
            "--read-when",
            "when publishing or sharing a deliverable",
            "--tag",
            "approval",
            "--artifact-ref",
            "docs/publishing.md",
            "--content",
            large,
        )
        self.command(
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
        search = json.loads(
            self.command(
                RECALL,
                "--project",
                str(self.project),
                "--json",
                "search",
                "--query",
                "publishing approval",
            ).stdout
        )
        self.assertEqual(project_id, search["project_id"])
        self.assertEqual(memory_id, search["entries"][0]["id"])
        self.assertNotIn("content", search["entries"][0])
        no_match = json.loads(
            self.command(
                RECALL,
                "--project",
                str(self.project),
                "--json",
                "search",
                "--query",
                "unrelated-zebra-quantum",
            ).stdout
        )
        self.assertEqual([], no_match["entries"])
        hydrated = json.loads(
            self.command(
                RECALL,
                "--project",
                str(self.project),
                "--json",
                "hydrate",
                "--id",
                memory_id,
                "--budget-tokens",
                "200",
            ).stdout
        )["entry"]
        self.assertTrue(hydrated["truncated"])
        self.assertLessEqual(hydrated["estimated_tokens"], 200)
        self.assertLessEqual(
            (
                len(json.dumps(hydrated, sort_keys=True, ensure_ascii=False))
                + 3
            )
            // 4,
            200,
        )
        self.assertEqual(["docs/publishing.md"], hydrated["artifact_refs"])

    def test_session_is_explicit_semantic_and_can_become_dormant(self) -> None:
        self.initialize()
        identifier = str(uuid.uuid4())
        started = json.loads(
            self.command(
                SESSION,
                "--project",
                str(self.project),
                "--json",
                "start",
                "--session-id",
                identifier,
                "--task",
                "Prepare the quarterly operating review",
                "--title",
                "Quarterly operating review",
                "--read-when",
                "when resuming the quarterly review",
                "--tag",
                "operations",
                "--artifact-ref",
                "reports/q3-review.docx",
            ).stdout
        )["result"]
        self.assertEqual(2, started["schema_version"])
        self.assertEqual("active", started["status"])
        dormant = json.loads(
            self.command(
                SESSION,
                "--project",
                str(self.project),
                "--json",
                "dormant",
                "--session-id",
                identifier,
                "--summary",
                "Source collection is complete.",
                "--next-step",
                "Draft the review.",
            ).stdout
        )["result"]
        self.assertEqual("dormant", dormant["status"])
        listed = json.loads(
            self.command(
                SESSION,
                "--project",
                str(self.project),
                "--json",
                "list",
                "--status",
                "dormant",
            ).stdout
        )["result"]["sessions"]
        self.assertEqual([identifier], [item["id"] for item in listed])


if __name__ == "__main__":
    unittest.main()
