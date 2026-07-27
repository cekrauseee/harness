from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"


def run_script(relative: str, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / relative), *args],
        cwd=ROOT,
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )


class SkillPackagingTests(unittest.TestCase):
    def test_standard_skills_are_self_contained_and_complete(self) -> None:
        expected = {
            "harness-worktree": ("resolve_branch.py", "worktrees.md"),
            "harness-commit": ("validate_conventional.py", "conventional-commits.md"),
            "harness-pr": ("render_pr.py", "pull-requests.md"),
            "harness-review": ("validate_review.py", "review-severity.md"),
        }
        for name, (script, reference) in expected.items():
            with self.subTest(skill=name):
                skill = SKILLS / name
                content = (skill / "SKILL.md").read_text()
                self.assertIn(f"name: {name}", content)
                self.assertNotIn("TODO", content)
                self.assertTrue((skill / "scripts" / script).is_file())
                self.assertTrue((skill / "references" / reference).is_file())
                if name == "harness-worktree":
                    self.assertIn(
                        "Harness owns branch naming, base selection, creation",
                        content,
                    )
                    self.assertIn(
                        "The host owns only the physical checkout path",
                        content,
                    )
                    self.assertNotIn(
                        "The host owns the checkout path, storage layout, metadata, lifecycle",
                        content,
                    )


class WorktreeResolverTests(unittest.TestCase):
    def prepare(self, root: Path) -> None:
        subprocess.run(["git", "init", "-q", "-b", "trunk", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.com"], check=True)
        (root / "README.md").write_text("# Test\n")
        subprocess.run(["git", "-C", str(root), "add", "README.md"], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "test: seed repository"], check=True)

    def test_resolves_branch_semantics_without_path_or_harness_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.prepare(root)
            before = sorted(str(path.relative_to(root)) for path in root.rglob("*"))
            result = run_script(
                "skills/harness-worktree/scripts/resolve_branch.py",
                "--project",
                str(root),
                "--type",
                "docs",
                "--slug",
                "Artifact Guidelines",
                "--require-available",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(
                payload,
                {
                    "base": "trunk",
                    "branch": "docs/artifact-guidelines",
                    "branch_exists": False,
                    "slug": "artifact-guidelines",
                    "type": "docs",
                },
            )
            after = sorted(str(path.relative_to(root)) for path in root.rglob("*"))
            self.assertEqual(before, after, "resolution must not write Git or Harness state")
            self.assertNotIn("path", payload)
            self.assertNotIn("worktree_id", payload)
            self.assertNotIn("project_id", payload)

    def test_rejects_existing_branch_when_availability_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            repo.mkdir()
            self.prepare(repo)
            subprocess.run(
                ["git", "-C", str(repo), "branch", "fix/session-expiry"],
                check=True,
            )
            result = run_script(
                "skills/harness-worktree/scripts/resolve_branch.py",
                "--project",
                str(repo),
                "--type",
                "fix",
                "--slug",
                "session-expiry",
                "--require-available",
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("already exists", result.stderr)


class ConventionalCommitTests(unittest.TestCase):
    SCRIPT = "skills/harness-commit/scripts/validate_conventional.py"

    def test_accepts_breaking_commit_and_harness_branch(self) -> None:
        result = run_script(
            self.SCRIPT,
            "--message",
            "feat(api)!: replace authentication contract\n\n"
            "BREAKING CHANGE: clients must provide a refresh token.",
            "--branch",
            "feat/authentication-contract",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["ok"])

    def test_rejects_invalid_case_period_and_branch_prefix(self) -> None:
        result = run_script(
            self.SCRIPT,
            "--message",
            "Feat(api): Add authentication.",
            "--branch",
            "feature/authentication",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertGreaterEqual(len(payload["errors"]), 2)


class PullRequestRendererTests(unittest.TestCase):
    SCRIPT = "skills/harness-pr/scripts/render_pr.py"

    def test_renders_required_sections_as_json(self) -> None:
        result = run_script(
            self.SCRIPT,
            "--title",
            "docs(harness): define artifact routing",
            "--summary",
            "Define the canonical destination for final HTML artifacts.",
            "--change",
            "Route final files to docs/artifacts/.",
            "--verification",
            "Ran the standards unit tests.",
            "--risk",
            "Existing artifacts are not migrated.",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["title"], "docs(harness): define artifact routing")
        for section in ("Summary", "Changes", "Verification", "Risks"):
            self.assertIn(f"## {section}", payload["body"])
        self.assertNotIn("gh pr create", payload["body"])

    def test_rejects_non_conventional_title(self) -> None:
        result = run_script(
            self.SCRIPT,
            "--title",
            "Document artifact routing",
            "--summary",
            "Describe artifact routing.",
            "--change",
            "Add guidance.",
            "--verification",
            "Not run because this command only validates text.",
            "--risk",
            "None identified.",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)["ok"])


class ReviewValidatorTests(unittest.TestCase):
    SCRIPT = "skills/harness-review/scripts/validate_review.py"

    def test_accepts_evidence_backed_finding(self) -> None:
        payload = {
            "findings": [
                {
                    "priority": "P2",
                    "title": "Handle the empty-token path",
                    "file": "src/auth.py",
                    "start": 42,
                    "end": 43,
                    "evidence": "An empty token reaches decode_token without a guard.",
                    "impact": "The request raises instead of returning an authentication error.",
                    "direction": "Reject empty tokens before decoding.",
                }
            ]
        }
        result = run_script(self.SCRIPT, "--format", "json", stdin=json.dumps(payload))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["ok"])

    def test_rejects_unknown_priority_and_missing_evidence(self) -> None:
        payload = {
            "findings": [
                {
                    "priority": "P4",
                    "title": "Improve this",
                    "file": "src/auth.py",
                    "start": 1,
                    "impact": "Unclear behavior.",
                    "direction": "Change it.",
                }
            ]
        }
        result = run_script(self.SCRIPT, "--format", "json", stdin=json.dumps(payload))
        self.assertEqual(result.returncode, 1)
        errors = json.loads(result.stdout)["errors"]
        self.assertTrue(any("priority" in error for error in errors))
        self.assertTrue(any("evidence" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
