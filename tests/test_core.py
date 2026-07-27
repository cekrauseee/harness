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
        self.assertIn('creation = "host-native"', worktree_policy)
        self.assertIn("host_managed_path = true", worktree_policy)
        self.assertNotIn("directory_template", worktree_policy)
        self.assertNotIn('root = "project-container"', worktree_policy)
        self.assertTrue((self.root / "harness-home/charter.md").is_file())
        again = json.loads(self.command(INIT, "init", "--repo", str(self.repo), "--json").stdout)
        self.assertFalse(again["created"])
        self.assertEqual(project_id, again["project"]["id"])

    def test_memory_classification_catalog_and_budgeted_recall(self) -> None:
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
            "--budget-tokens", "40", "--json",
        ).stdout)
        self.assertLessEqual(recall["estimated_tokens"], 40)
        self.assertEqual(candidate_id, Path(recall["entries"][0]["source"]).stem)
        self.assertEqual(project_id, recall["project_id"])
        memory = json.loads((base / f"memory/topics/authentication/{candidate_id}.json").read_text())
        for field in ("last_verified_at", "read_when", "review_after"):
            self.assertTrue(memory[field])
        audit = json.loads(self.command(AUDIT, "--repo", str(self.repo), "--json").stdout)
        self.assertEqual(0, audit["errors"])
        hook_recall = json.loads(self.command(
            HOOK, "event", "user-prompt", "--json",
            input_json={"cwd": str(self.repo), "session_id": str(uuid.uuid4()), "prompt": "autenticacao movel"},
        ).stdout)
        self.assertIn("legacy refresh endpoint", hook_recall["hookSpecificOutput"]["additionalContext"])

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

    def test_session_stop_checkpoints_but_does_not_close(self) -> None:
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
        self.assertEqual("Mapped refresh paths.", json.loads(active.read_text())["summary"])
        self.assertEqual(1, len(list((base / "memory/candidates").glob("*.json"))))
        self.command(SESSION, "--repo", str(self.repo), "--json", "close", "--session-id", session_id)
        self.assertFalse(active.exists())

    def test_hook_auto_init_and_fail_open(self) -> None:
        result = self.command(
            HOOK, "event", "session-start", "--json", "--budget-tokens", "120",
            input_json={"cwd": str(self.repo), "session_id": str(uuid.uuid4()), "prompt": "Inspect docs"},
        )
        payload = json.loads(result.stdout)
        self.assertTrue(payload["continue"])
        self.assertIn("hookSpecificOutput", payload)
        configured = subprocess.run(
            ["git", "-C", str(self.repo), "config", "--local", "--get", "harness.project-id"],
            text=True, capture_output=True, check=True,
        ).stdout.strip()
        self.assertEqual(str(uuid.UUID(configured)), configured)
        base = self.root / "harness-home/projects" / configured
        session_file = next((base / "sessions/active").glob("*.json"))
        self.assertNotIn("Inspect docs", session_file.read_text())
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
        session = json.loads((base / f"sessions/active/{session_id}.json").read_text())
        self.assertNotIn("raw private response", json.dumps(session))
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
        self.assertTrue(hooks["skipped"])
        self.assertIn("plugin-bundled", hooks["reason"])
        self.assertFalse((self.root / "codex-home/hooks.json").exists())

    def test_audit_clean_container(self) -> None:
        self.initialize()
        result = self.command(AUDIT, "--repo", str(self.repo), "--json")
        payload = json.loads(result.stdout)
        self.assertEqual(0, payload["errors"])


if __name__ == "__main__":
    unittest.main()
