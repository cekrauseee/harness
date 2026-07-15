from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INIT_DOCS = ROOT / "skills" / "harness-docs-init" / "scripts" / "init_docs.py"
CHECK_DOCS = ROOT / "skills" / "harness-docs-audit" / "scripts" / "check_docs.py"
CREATE_ARTIFACT = ROOT / "skills" / "harness-artifact" / "scripts" / "create_artifact.py"
CHECK_ARTIFACTS = ROOT / "skills" / "harness-artifact" / "scripts" / "check_artifacts.py"


def run(*args: str | Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(arg) for arg in args],
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class DocumentationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name) / "project"
        self.project.mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def initialize(self) -> None:
        run(sys.executable, INIT_DOCS, self.project)

    def test_initializes_complete_layout_without_overwriting_content(self) -> None:
        readme = self.project / "README.md"
        readme.write_text("# Existing\n", encoding="utf-8")

        first = run(sys.executable, INIT_DOCS, self.project)
        second = run(sys.executable, INIT_DOCS, self.project)

        self.assertEqual(readme.read_text(encoding="utf-8"), "# Existing\n")
        self.assertTrue((self.project / "docs" / "modules").is_dir())
        self.assertTrue((self.project / "docs" / "artifacts" / "index.md").is_file())
        self.assertIn("Files created: 5", first.stdout)
        self.assertIn("Files created: 0", second.stdout)

    def test_docs_checker_reports_broken_links_and_unindexed_modules(self) -> None:
        self.initialize()
        module = self.project / "docs" / "modules" / "billing.md"
        module.write_text("# Billing\n\n[Missing](missing.md)\n", encoding="utf-8")

        result = run(
            sys.executable,
            CHECK_DOCS,
            self.project,
            "--strict",
            "--format",
            "json",
            check=False,
        )
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("broken link: docs/modules/billing.md -> missing.md", payload["issues"])
        self.assertIn("unindexed module: docs/modules/billing.md", payload["warnings"])

    def test_creates_indexes_and_validates_self_contained_artifact(self) -> None:
        self.initialize()

        created = run(
            sys.executable,
            CREATE_ARTIFACT,
            self.project,
            "request-flow",
            "--title",
            "Request Flow",
            "--summary",
            "Shows how a request moves through the system.",
        )
        artifact = self.project / "docs" / "artifacts" / "request-flow.html"
        html = artifact.read_text(encoding="utf-8")

        self.assertEqual(Path(created.stdout.strip()).resolve(), artifact.resolve())
        self.assertIn('<html lang="en">', html)
        self.assertIn('<main id="main-content">', html)
        self.assertNotIn("https://", html)
        self.assertIn("(request-flow.html)", (artifact.parent / "index.md").read_text(encoding="utf-8"))
        run(sys.executable, CHECK_ARTIFACTS, self.project)
        run(sys.executable, CHECK_DOCS, self.project, "--strict")

    def test_artifact_checker_rejects_external_dependencies_and_missing_index_entry(self) -> None:
        self.initialize()
        artifact = self.project / "docs" / "artifacts" / "unsafe.html"
        artifact.write_text(
            """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Unsafe</title><script src="https://example.com/app.js"></script></head>
<body><main><h1>Unsafe</h1></main></body></html>
""",
            encoding="utf-8",
        )

        result = run(sys.executable, CHECK_ARTIFACTS, self.project, "--format", "json", check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "external dependency: docs/artifacts/unsafe.html -> https://example.com/app.js",
            payload["issues"],
        )
        self.assertIn("unindexed artifact: docs/artifacts/unsafe.html", payload["issues"])

    def test_artifact_checker_rejects_local_css_and_network_runtime_dependencies(self) -> None:
        self.initialize()
        artifact = self.project / "docs" / "artifacts" / "runtime.html"
        artifact.write_text(
            """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width"><title>Runtime</title>
<link rel="stylesheet" href="local.css"><style>@import "theme.css"; .x{background:url(icon.svg)}</style>
<script src="local.js"></script><script>fetch('/api')</script></head>
<body><main><h1>Runtime</h1></main></body></html>""",
            encoding="utf-8",
        )
        result = run(sys.executable, CHECK_ARTIFACTS, self.project, "--format", "json", check=False)
        issues = json.loads(result.stdout)["issues"]
        self.assertTrue(any("local.css" in issue for issue in issues))
        self.assertTrue(any("theme.css" in issue for issue in issues))
        self.assertTrue(any("icon.svg" in issue for issue in issues))
        self.assertTrue(any("local.js" in issue for issue in issues))
        self.assertTrue(any("network API" in issue for issue in issues))

    def test_artifact_creation_requires_lowercase_kebab_case(self) -> None:
        self.initialize()
        result = run(
            sys.executable,
            CREATE_ARTIFACT,
            self.project,
            "Request_Flow",
            "--title",
            "Request Flow",
            "--summary",
            "Shows the request flow.",
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("lowercase kebab-case", result.stderr)


if __name__ == "__main__":
    unittest.main()
