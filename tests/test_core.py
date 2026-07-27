from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
import uuid


ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "skills/harness-init/scripts/init.py"
HOOK = ROOT / "skills/harness-init/scripts/hook_adapter.py"
INSTALL_HOOKS = ROOT / "skills/harness-init/scripts/install_hooks.py"
REMEMBER = ROOT / "skills/harness-remember/scripts/remember.py"
RECALL = ROOT / "skills/harness-recall/scripts/recall.py"
SESSION = ROOT / "skills/harness-session/scripts/session.py"
AUDIT = ROOT / "skills/harness-audit/scripts/audit.py"


class CoreHarnessTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.env = dict(
            os.environ,
            CODEX_HOME=str(self.root / "codex-home"),
            HARNESS_HOME=str(self.root / "harness-home"),
            HARNESS_SKIP_HOOK_INSTALL="1",
            HOME=str(self.root / "user-home"),
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def command(self, script: Path, *args: str, input_json: dict | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(script), *args], env=self.env, text=True,
            input=json.dumps(input_json) if input_json is not None else None,
            capture_output=True,
        )
        if check and result.returncode:
            self.fail(f"command failed ({result.returncode}): {result.stderr}\n{result.stdout}")
        return result

    def initialize(self) -> tuple[str, Path]:
        result = self.command(INIT, "init", "--repo", str(self.repo), "--json")
        payload = json.loads(result.stdout)
        return payload["project"]["id"], Path(payload["project_dir"])

    def test_init_is_idempotent_global_and_repo_clean(self) -> None:
        project_id, base = self.initialize()
        self.assertEqual(str(uuid.UUID(project_id)), project_id)
        self.assertEqual("", subprocess.run(["git", "-C", str(self.repo), "status", "--porcelain"], text=True, capture_output=True, check=True).stdout)
        for path in (
            "index.md", "project.md", "decisions.md", "manifest.json", "memory/catalog.jsonl",
            "references/product", "references/technical", "references/operations",
            "references/investigations", "worktrees/policy.toml", "workspace/policy.json",
        ):
            self.assertTrue((base / path).exists(), path)
        worktree_policy = (base / "worktrees/policy.toml").read_text(encoding="utf-8")
        self.assertIn('creation_protocol = "harness"', worktree_policy)
        self.assertIn('lifecycle = "harness"', worktree_policy)
        self.assertIn('path_provider = "host"', worktree_policy)
        self.assertIn('storage_provider = "host"', worktree_policy)
        self.assertNotIn('creation = "host-native"', worktree_policy)
        self.assertNotIn("directory_template", worktree_policy)
        self.assertNotIn('root = "project-container"', worktree_policy)
        self.assertTrue((self.root / "harness-home/charter.md").is_file())
        again = json.loads(self.command(INIT, "init", "--repo", str(self.repo), "--json").stdout)
        self.assertFalse(again["created"])
        self.assertEqual(project_id, again["project"]["id"])

    def test_memory_classification_catalog_and_two_stage_recall(self) -> None:
        project_id, base = self.initialize()
        candidate_id = str(uuid.uuid4())
        self.command(
            REMEMBER, "--repo", str(self.repo), "--json", "candidate",
            "--id", candidate_id, "--topic", "Authentication",
            "--content", "Mobile clients use the legacy refresh endpoint.",
        )
        self.assertTrue((base / f"memory/candidates/{candidate_id}.json").is_file())
        self.command(
            REMEMBER, "--repo", str(self.repo), "--json", "consolidate",
            "--candidate-id", candidate_id, "--classification", "topic",
        )
        self.assertTrue((base / f"memory/topics/authentication/{candidate_id}.json").is_file())
        catalog = (base / "memory/catalog.jsonl").read_text(encoding="utf-8")
        self.assertIn(candidate_id, catalog)
        recall = json.loads(self.command(
            RECALL, "--repo", str(self.repo), "--query", "autenticacao movel legacy refresh endpoint",
            "--budget-tokens", "200", "--json",
        ).stdout)
        self.assertLessEqual(recall["estimated_tokens"], 200)
        self.assertEqual(candidate_id, recall["entries"][0]["id"])
        self.assertNotIn("content", recall["entries"][0])
        self.assertEqual(project_id, recall["project_id"])
        hydrated = json.loads(self.command(
            RECALL, "--repo", str(self.repo), "--json", "hydrate",
            "--id", candidate_id, "--budget-tokens", "200",
        ).stdout)
        self.assertIn("legacy refresh endpoint", hydrated["entry"]["content"])
        memory = json.loads((base / f"memory/topics/authentication/{candidate_id}.json").read_text())
        for field in ("last_verified_at", "read_when", "review_after"):
            self.assertTrue(memory[field])
        audit = json.loads(self.command(AUDIT, "--repo", str(self.repo), "--json").stdout)
        self.assertEqual(0, audit["errors"])
        hook_recall = json.loads(self.command(
            HOOK, "event", "user-prompt", "--json",
            input_json={"cwd": str(self.repo), "session_id": str(uuid.uuid4()), "prompt": "autenticacao movel"},
        ).stdout)
        self.assertEqual({"continue": True}, hook_recall)

    def test_discard_removes_candidate_content(self) -> None:
        _, base = self.initialize()
        candidate_id = str(uuid.uuid4())
        secret = "temporary-sensitive-observation"
        self.command(
            REMEMBER, "--repo", str(self.repo), "--json", "candidate",
            "--id", candidate_id, "--topic", "temporary", "--content", secret,
        )
        self.command(
            REMEMBER, "--repo", str(self.repo), "--json", "consolidate",
            "--candidate-id", candidate_id, "--classification", "discard",
        )
        archived = (base / f"memory/archive/candidate-{candidate_id}.json").read_text()
        self.assertNotIn(secret, archived)
        self.assertNotIn("content", json.loads(archived))

    def test_hooks_do_not_checkpoint_or_capture_candidates(self) -> None:
        _, base = self.initialize()
        session_id = str(uuid.uuid4())
        self.command(
            SESSION, "--repo", str(self.repo), "--json", "start",
            "--session-id", session_id, "--task", "Document authentication",
        )
        hook = self.command(
            HOOK, "event", "stop", "--json", "--summary", "Mapped refresh paths.", "--capture-candidate",
            input_json={"cwd": str(self.repo), "session_id": session_id},
        )
        self.assertTrue(json.loads(hook.stdout)["continue"])
        active = base / f"sessions/active/{session_id}.json"
        self.assertTrue(active.is_file())
        self.assertFalse((base / f"sessions/closed/{session_id}.json").exists())
        self.assertEqual("", json.loads(active.read_text())["summary"])
        self.assertEqual(0, len(list((base / "memory/candidates").glob("*.json"))))
        self.command(SESSION, "--repo", str(self.repo), "--json", "close", "--session-id", session_id)
        self.assertFalse(active.exists())

    def test_hook_does_not_auto_init_and_fails_open_silently(self) -> None:
        result = self.command(
            HOOK, "event", "session-start", "--json", "--budget-tokens", "120",
            input_json={"cwd": str(self.repo), "session_id": str(uuid.uuid4()), "prompt": "Inspect docs"},
        )
        payload = json.loads(result.stdout)
        self.assertTrue(payload["continue"])
        self.assertEqual({"continue": True}, payload)
        configured = subprocess.run(
            ["git", "-C", str(self.repo), "config", "--local", "--get", "harness.project-id"],
            text=True, capture_output=True, check=False,
        ).stdout.strip()
        self.assertEqual("", configured)
        self.assertFalse((self.root / "harness-home/projects").exists())
        outside = self.command(HOOK, "event", "session-start", "--json", input_json={"cwd": str(self.root)})
        outside_payload = json.loads(outside.stdout)
        self.assertTrue(outside_payload["continue"])
        self.assertNotIn("systemMessage", outside_payload)

        prompt = self.command(
            HOOK, "event", "user-prompt", "--json", "--budget-tokens", "120",
            input_json={"cwd": str(self.repo), "session_id": str(uuid.uuid4()), "prompt": "Inspect docs"},
        )
        self.assertTrue(json.loads(prompt.stdout)["continue"])

    def test_hooks_recover_stale_lock_clean_workspace_and_do_not_store_raw_messages(self) -> None:
        _, base = self.initialize()
        old_file = base / "workspace/old.txt"
        old_file.write_text("expired")
        old = time.time() - 9 * 86400
        os.utime(old_file, (old, old))
        stale_lock = base / ".lock"
        stale_lock.mkdir()
        (stale_lock / "owner").write_text("dead")
        os.utime(stale_lock, (time.time() - 301, time.time() - 301))
        session_id = str(uuid.uuid4())
        started = self.command(
            HOOK, "event", "session-start", "--json",
            input_json={"cwd": str(self.repo), "session_id": session_id},
        )
        self.assertTrue(json.loads(started.stdout)["continue"])
        self.assertFalse(old_file.exists())
        stopped = self.command(
            HOOK, "event", "stop", "--json",
            input_json={"cwd": str(self.repo), "session_id": session_id, "last_assistant_message": "raw private response"},
        )
        self.assertTrue(json.loads(stopped.stdout)["continue"])
        self.assertFalse((base / f"sessions/active/{session_id}.json").exists())
        self.assertEqual([], list((base / "memory/candidates").glob("*.json")))

    def test_hook_installation_is_idempotent_and_preserves_existing_hooks(self) -> None:
        codex = self.root / "codex-home/hooks.json"
        codex.parent.mkdir(parents=True)
        codex.write_text(json.dumps({"hooks": {"Stop": [
            {"hooks": [{"type": "command", "command": "true"}]},
            {"hooks": [
                {"type": "command", "command": "python3 /old/harness-init/scripts/hook_adapter.py event stop"},
                {"type": "command", "command": "keep-me"},
            ]},
        ]}}))
        first = json.loads(self.command(INSTALL_HOOKS, "--json").stdout)
        self.assertTrue(any(item["changed"] for item in first["results"]))
        second = json.loads(self.command(INSTALL_HOOKS, "--json").stdout)
        self.assertFalse(any(item["changed"] for item in second["results"]))
        configured = json.loads(codex.read_text())
        self.assertEqual("true", configured["hooks"]["Stop"][0]["hooks"][0]["command"])
        self.assertIn("keep-me", json.dumps(configured))
        self.assertIn("harness-init/scripts/hook_adapter.py", json.dumps(configured))
        claude = json.loads((self.root / "user-home/.claude/settings.json").read_text())
        self.assertIn("harness-init/scripts/hook_adapter.py", json.dumps(claude))

    def test_full_plugin_init_does_not_duplicate_bundled_hooks(self) -> None:
        env = dict(self.env)
        env.pop("HARNESS_SKIP_HOOK_INSTALL")
        env["PLUGIN_ROOT"] = str(ROOT)
        result = subprocess.run(
            [sys.executable, str(INIT), "init", "--repo", str(self.repo), "--json"],
            env=env, text=True, capture_output=True, check=True,
        )
        hooks = json.loads(result.stdout)["hooks"]
        self.assertFalse(hooks["installed"])
        self.assertIn("explicit", hooks["reason"])
        self.assertFalse((self.root / "codex-home/hooks.json").exists())
        self.assertEqual(
            {"hooks": {}},
            json.loads((ROOT / "hooks/hooks.json").read_text()),
        )

    def test_audit_clean_container(self) -> None:
        self.initialize()
        result = self.command(AUDIT, "--repo", str(self.repo), "--json")
        payload = json.loads(result.stdout)
        self.assertEqual(0, payload["errors"])


if __name__ == "__main__":
    unittest.main()
