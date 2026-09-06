"""Current identity/ownership and Markdown guarantees; all state is temporary."""
from concurrent.futures import ThreadPoolExecutor
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock
import uuid

HELPER = Path(os.environ.get("HARNESS_TEST_HELPER", Path(__file__).resolve().parents[1] / "src" / "harness.py"))
SPEC = importlib.util.spec_from_file_location("kernel_under_test", HELPER)
harness = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(harness)


class KernelTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.home = self.base / "state"
        self.project = self.base / "work" / "project"
        self.project.mkdir(parents=True)

    def call(self, operation, **data):
        if "project_id" not in data and "project" not in data:
            data["project"] = str(self.project)
        return harness.execute(operation, data, self.home)

    def initialize(self):
        self.identity = self.call("init")
        self.snapshot = Path(self.identity["project_dir"]) / "project.json"
        return self.identity

    def claim(self, resource="src", **data):
        return self.call("claim", purpose="Implement the change", resource=[resource], **data)["contribution"]

    def input_file(self, content, name="input.md"):
        path = self.base / name
        path.write_text(content, encoding="utf-8")
        return str(path)

    def error(self, code, operation, **data):
        with self.assertRaises(harness.Error) as caught:
            self.call(operation, **data)
        self.assertEqual(caught.exception.code, code, str(caught.exception))
        return caught.exception

    def git(self, directory, *arguments):
        completed = subprocess.run(["git", "-C", str(directory), *arguments], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return completed.stdout.strip()

    def repository(self):
        self.git(self.project, "init", "-q")
        self.git(self.project, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "commit", "--allow-empty", "-qm", "Initial")

    def concurrent_cli(self, commands):
        barrier = threading.Barrier(len(commands))
        def run(arguments):
            barrier.wait()
            result = subprocess.run([sys.executable, str(HELPER), "--home", str(self.home), *arguments],
                                    text=True, capture_output=True, timeout=20)
            self.assertIn(result.returncode, (0, 1), result.stderr)
            return json.loads(result.stdout)
        with ThreadPoolExecutor(max_workers=len(commands)) as pool:
            return list(pool.map(run, commands))

    def test_unknown_reads_do_not_initialize(self):
        for operation in ("resolve", "status", "read"):
            self.error("project_unknown", operation, file="fact.md")
        self.assertFalse(self.home.exists())
        self.assertEqual(list(self.project.iterdir()), [])

    def test_init_and_non_git_closest_root_are_stable(self):
        identity = self.initialize()
        child = self.project / "nested"
        child.mkdir()
        self.assertEqual(self.call("resolve", project=str(child)), identity)
        self.assertEqual(self.call("init", project=str(child)), identity)
        self.assertEqual(list(self.project.iterdir()), [child])
        state = json.loads(self.snapshot.read_text())
        self.assertEqual(set(state), {"format", "id", "name", "roots", "contributions"})
        self.assertEqual(state["format"], 1)

    def test_concurrent_init_creates_one_identity(self):
        commands = [["init", "--project", str(self.project)]] * 2
        results = self.concurrent_cli(commands)
        self.assertEqual(results[0], results[1])
        folders = [p for p in (self.home / "projects").iterdir() if not p.name.startswith(".")]
        self.assertEqual(len(folders), 1)

    def test_storage_cannot_be_inside_project_or_project_inside_storage(self):
        nested_home = self.project / "state"
        with self.assertRaises(harness.Error) as caught:
            harness.execute("init", {"project": str(self.project)}, nested_home)
        self.assertEqual(caught.exception.code, "unsafe_path")
        self.assertFalse(nested_home.exists())
        self.home.mkdir()
        nested_project = self.home / "work"
        nested_project.mkdir()
        self.error("unsafe_path", "init", project=str(nested_project))
        self.assertFalse((self.home / ".runtime.lock").exists())

    def test_worktree_joins_and_clone_stays_separate(self):
        self.repository()
        first = self.initialize()
        worktree = self.base / "worktree"
        self.git(self.project, "worktree", "add", "-qb", "test-worktree", str(worktree))
        before = self.snapshot.read_bytes()
        resolved = self.call("resolve", project=str(worktree))
        self.assertEqual(resolved["project_id"], first["project_id"])
        self.assertNotEqual(resolved["workspace"]["workspace_id"], first["workspace"]["workspace_id"])
        self.assertEqual(self.snapshot.read_bytes(), before)
        self.assertEqual(self.call("init", project=str(worktree)), resolved)
        self.assertEqual(len(json.loads(self.snapshot.read_text())["roots"]), 2)
        clone = self.base / "clone"
        self.git(self.base, "clone", "-q", str(self.project), str(clone))
        cloned = self.call("init", project=str(clone))
        self.assertNotEqual(cloned["project_id"], first["project_id"])

    def test_worktree_claim_registers_stable_workspace(self):
        self.repository()
        first = self.initialize()
        worktree = self.base / "worktree"
        self.git(self.project, "worktree", "add", "-qb", "test-worktree", str(worktree))
        resolved = self.call("resolve", project=str(worktree))
        record = self.claim(project=str(worktree))
        self.assertEqual(record["workspace_id"], resolved["workspace"]["workspace_id"])
        state = json.loads(self.snapshot.read_text())
        self.assertEqual(len(state["roots"]), 2)
        self.assertEqual(self.call("resolve", project_id=first["project_id"])["workspace"], None)

    def test_cross_project_ancestor_collision(self):
        self.initialize()
        self.error("root_conflict", "init", project=str(self.project.parent))
        other = self.base / "other"
        other.mkdir()
        identity = self.call("init", project=str(other))
        self.error("root_conflict", "bind", project=str(self.project), project_id=identity["project_id"])
        self.error("root_conflict", "bind", project=str(self.project.parent), project_id=identity["project_id"])

    def test_topology_changes_require_explicit_rebind(self):
        first = self.initialize()
        self.repository()
        self.error("topology_changed", "resolve")
        self.error("topology_changed", "init")
        self.error("topology_changed", "bind", project_id=first["project_id"], project=str(self.project))
        rebound = self.call("bind", project_id=first["project_id"], project=str(self.project), replace=str(self.project))
        self.assertEqual(rebound["workspace"]["workspace_id"], first["workspace"]["workspace_id"])
        self.assertTrue(rebound["workspace"]["git_common_dir"])
        self.assertEqual(self.call("resolve"), rebound)
        self.claim()
        self.assertEqual(self.call("bind", project_id=first["project_id"], project=str(self.project),
                                   replace=str(self.project)), rebound)

    def test_move_rebind_preserves_workspace_and_blocks_active_owners(self):
        first = self.initialize()
        owner = self.claim()
        moved = self.project.with_name("moved")
        old = str(self.project)
        self.project.rename(moved)
        self.error("project_unknown", "resolve", project=str(moved))
        self.error("active_contribution", "bind", project=str(moved), project_id=first["project_id"], replace=old)
        self.call("release", project_id=first["project_id"], owner=owner["id"], expect=1, reason="Writer stopped")
        rebound = self.call("bind", project=str(moved), project_id=first["project_id"], replace=old)
        self.assertEqual(rebound["workspace"]["workspace_id"], first["workspace"]["workspace_id"])
        self.assertEqual(self.call("bind", project=str(moved), project_id=first["project_id"], replace=old), rebound)
        self.assertEqual(self.call("resolve", project=str(moved)), rebound)
        self.assertFalse(Path(old).exists())

    def test_reference_only_project_read_and_status(self):
        project_id = str(uuid.uuid4())
        folder = self.home / "projects" / project_id
        (folder / "knowledge").mkdir(parents=True)
        state = {"format": 1, "id": project_id, "name": "Reference", "roots": [], "contributions": {}}
        (folder / "project.json").write_text(json.dumps(state))
        (folder / "knowledge" / "notes.md").write_text("# Reference\n")
        self.assertIsNone(self.call("resolve", project_id=project_id)["workspace"])
        self.assertEqual(self.call("status", project_id=project_id)["contributions"], {})
        self.assertEqual(self.call("read", project_id=project_id, file="notes.md")["content"], "# Reference\n")
        self.error("invalid_input", "claim", project_id=project_id, purpose="Read", resource=["notes.md"])
        self.assertFalse((self.home / "projects" / project_id / ".runtime.lock").exists())

    def test_reusing_a_moved_root_path_gets_a_distinct_workspace(self):
        first = self.initialize()
        moved = self.project.with_name("moved")
        self.project.rename(moved)
        rebound = self.call("bind", project=str(moved), project_id=first["project_id"], replace=str(self.project))
        self.project.mkdir()
        recreated = self.call("bind", project=str(self.project), project_id=first["project_id"])
        self.assertNotEqual(recreated["workspace"]["workspace_id"], rebound["workspace"]["workspace_id"])
        self.assertEqual(self.call("resolve"), recreated)
        self.assertEqual(self.call("resolve", project=str(moved)), rebound)

    def test_corrupt_and_incomplete_state_are_not_empty_projects(self):
        self.initialize()
        self.snapshot.write_text("{")
        self.error("invalid_state", "status")
        self.error("invalid_state", "init")
        self.snapshot.unlink()
        self.error("project_unknown", "init")

    def test_previous_format_is_rejected(self):
        self.initialize()
        state = json.loads(self.snapshot.read_text())
        state["format"] = 0
        self.snapshot.write_text(json.dumps(state))
        self.error("invalid_state", "resolve")

    def test_duplicate_json_keys_and_nonstandard_constants_are_rejected(self):
        self.initialize()
        self.claim()
        original = self.snapshot.read_text()
        damaged = [original.rstrip()[:-1] + ', "contributions": {}}',
                   original.replace('"active": true', '"active": true, "active": false')]
        damaged.extend(original.rstrip()[:-1] + ', "extra": ' + constant + '}'
                       for constant in ("NaN", "Infinity", "-Infinity"))
        for content in damaged:
            with self.subTest(content=content):
                self.snapshot.write_text(content)
                self.error("invalid_state", "status")
                self.error("invalid_state", "claim", purpose="Other", resource=["docs"])

    def test_simultaneous_overlapping_claims_have_one_owner(self):
        self.initialize()
        commands = [["claim", "--project", str(self.project), "--purpose", purpose, "--resource", resource]
                    for purpose, resource in (("Parent", "src"), ("Child", "src/file.py"))]
        results = self.concurrent_cli(commands)
        successes = [r for r in results if "contribution" in r]
        failures = [r for r in results if "error" in r]
        self.assertEqual(len(successes), 1)
        self.assertEqual(failures[0]["error"]["code"], "resource_conflict")
        self.assertEqual(len(self.call("status")["contributions"]), 1)

    def test_simultaneous_disjoint_claims_preserve_both(self):
        self.initialize()
        commands = [["claim", "--project", str(self.project), "--purpose", name, "--resource", name]
                    for name in ("src", "docs")]
        results = self.concurrent_cli(commands)
        self.assertTrue(all("contribution" in r for r in results), results)
        self.assertEqual(len(self.call("status")["contributions"]), 2)

    def test_conflicting_extension_is_all_or_nothing(self):
        self.initialize()
        first = self.claim("src")
        second = self.claim("docs")
        before = self.snapshot.read_bytes()
        self.error("resource_conflict", "claim", owner=second["id"], expect=1, resource=["tests", "src/file.py"])
        self.assertEqual(self.snapshot.read_bytes(), before)
        conflict = self.error("resource_conflict", "claim", purpose="Third", resource=["src"])
        self.assertEqual(conflict.details["conflicts"][0]["owner"], first["id"])

    def test_owner_extension_uses_cas_and_preserves_provenance(self):
        self.initialize()
        owner = self.claim("src")
        extended = self.call("claim", owner=owner["id"], expect=1, resource=["docs"], purpose="Ignored new purpose")
        record = extended["contribution"]
        self.assertEqual(record["purpose"], owner["purpose"])
        self.assertEqual(record["version"], 2)
        self.assertEqual(record["workspace"], owner["workspace"])
        self.error("version_conflict", "claim", owner=owner["id"], expect=1, resource=["tests"])
        retry = self.call("claim", owner=owner["id"], expect=1, resource=["docs"])
        self.assertFalse(retry["changed"])
        self.assertEqual(retry["contribution"]["version"], 2)

    def test_symlink_and_parent_resource_overlap(self):
        self.initialize()
        (self.project / "real").mkdir()
        (self.project / "alias").symlink_to("real", target_is_directory=True)
        owner = self.claim("alias")
        self.assertEqual(owner["resources"], [str(self.project / "real")])
        self.error("resource_conflict", "claim", purpose="Other", resource=["real/file.py"])
        self.error("invalid_input", "claim", purpose="Glob", resource=["*.py"])

    def test_cross_project_absolute_and_symlink_claims_conflict(self):
        first = self.initialize()
        shared = self.base / "shared"
        shared.mkdir()
        owner = self.claim(str(shared))
        other = self.base / "other"
        other.mkdir()
        self.call("init", project=str(other))
        (other / "alias").symlink_to(shared, target_is_directory=True)
        for resource in (str(shared / "file.py"), "alias/file.py"):
            conflict = self.error("resource_conflict", "claim", project=str(other),
                                  purpose="Other project", resource=[resource])
            self.assertEqual(conflict.details["conflicts"][0]["project_id"], first["project_id"])
            self.assertEqual(conflict.details["conflicts"][0]["owner"], owner["id"])
        self.assertEqual(self.call("status", project=str(other))["contributions"], {})
        self.assertEqual(len(self.call("status")["contributions"]), 1)
        self.call("release", owner=owner["id"], expect=1, reason="Finished shared work")
        self.claim("alias/file.py", project=str(other))

    def test_existing_hardlink_resources_conflict(self):
        self.initialize()
        source = self.project / "file.md"
        source.write_text("Shared bytes")
        os.link(source, self.project / "hardlink.md")
        self.claim("file.md")
        self.error("resource_conflict", "claim", purpose="Other writer", resource=["hardlink.md"])

    def test_existing_case_aliases_respect_filesystem_identity(self):
        self.initialize()
        source = self.project / "File.md"
        source.write_text("Original")
        alias = self.project / "file.md"
        self.claim("File.md")
        if alias.exists() and source.samefile(alias):
            self.error("resource_conflict", "claim", purpose="Other writer", resource=["file.md"])
        else:
            alias.write_text("Separate file on a case-sensitive filesystem")
            self.claim("file.md")
            self.assertEqual(len(self.call("status")["contributions"]), 2)

    def test_existing_directory_aliases_cover_future_descendants(self):
        self.initialize()
        directory = self.project / "MixedCase"
        directory.mkdir()
        alias = self.project / "mixedcase"
        self.claim("MixedCase/future")
        if alias.exists() and directory.samefile(alias):
            self.error("resource_conflict", "claim", purpose="Other writer",
                       resource=["mixedcase/future/file.py"])
        else:
            alias.mkdir()
            self.claim("mixedcase/future/file.py")
            self.assertEqual(len(self.call("status")["contributions"]), 2)

    def test_handoff_release_is_one_atomic_cas_update(self):
        self.initialize()
        owner = self.claim()
        content = "# Done\nEvidence and next action.\n"
        input_path = self.input_file(content)
        released = self.call("handoff", owner=owner["id"], expect=1, input=input_path, release=True)
        record = released["contribution"]
        self.assertEqual(record["version"], 2)
        self.assertFalse(record["active"])
        self.assertEqual(record["handoff"], content)
        self.assertEqual(self.call("status")["reservations"], [])
        self.assertFalse(self.call("handoff", owner=owner["id"], expect=1, input=input_path, release=True)["changed"])
        self.error("owner_closed", "handoff", owner=owner["id"], expect=2, input=input_path)
        self.error("owner_closed", "claim", owner=owner["id"], expect=2, resource=["src"])
        names = {p.name for p in Path(self.identity["project_dir"]).iterdir()}
        self.assertEqual(names, {"project.json", "knowledge"})

    def test_continuing_handoff_keeps_claim_and_rejects_stale_updates(self):
        self.initialize()
        owner = self.claim()
        first = self.input_file("First", "first.md")
        second = self.input_file("Second", "second.md")
        record = self.call("handoff", owner=owner["id"], expect=1, input=first)["contribution"]
        self.assertTrue(record["active"])
        self.assertEqual(len(self.call("status")["reservations"]), 1)
        self.error("version_conflict", "handoff", owner=owner["id"], expect=1, input=second, release=True)
        self.error("version_conflict", "release", owner=owner["id"], expect=1, reason="Stale")
        self.assertEqual(self.call("status")["contributions"][owner["id"]], record)

    def test_blank_handoffs_cannot_erase_context_or_release_ownership(self):
        self.initialize()
        owner = self.claim()
        before = self.snapshot.read_bytes()
        for content in ("", " \n\t"):
            for release in (False, True):
                self.error("invalid_input", "handoff", owner=owner["id"], expect=1,
                           input=self.input_file(content), release=release)
                self.assertEqual(self.snapshot.read_bytes(), before)

    def test_disjoint_owner_handoffs_preserve_both(self):
        self.initialize()
        first, second = self.claim("src"), self.claim("docs")
        commands = [["handoff", "--project", str(self.project), "--owner", owner["id"], "--expect", "1",
                     "--input", self.input_file(owner["id"], owner["id"] + ".md")]
                    for owner in (first, second)]
        results = self.concurrent_cli(commands)
        self.assertTrue(all("contribution" in r for r in results), results)
        for record in self.call("status")["contributions"].values():
            self.assertEqual(record["handoff"], record["id"])
            self.assertEqual(record["version"], 2)

    def test_failed_snapshot_replace_keeps_claim_and_handoff_unchanged(self):
        self.initialize()
        owner = self.claim()
        before = self.snapshot.read_bytes()
        input_path = self.input_file("Finished")
        with mock.patch.object(harness.os, "replace", side_effect=OSError("injected failure")):
            self.error("write_failed", "handoff", owner=owner["id"], expect=1, input=input_path, release=True)
        self.assertEqual(self.snapshot.read_bytes(), before)
        self.assertEqual(len(self.call("status")["reservations"]), 1)
        self.assertFalse(list(self.snapshot.parent.glob(".harness-*")))

    def test_no_automatic_stale_release_and_explicit_reason_persists(self):
        self.initialize()
        owner = self.claim()
        state = json.loads(self.snapshot.read_text())
        state["contributions"][owner["id"]]["updated_at"] = "2000-01-01T00:00:00+00:00"
        self.snapshot.write_text(json.dumps(state))
        self.assertEqual(len(self.call("status")["reservations"]), 1)
        self.error("resource_conflict", "claim", purpose="New writer", resource=["src"])
        released = self.call("release", owner=owner["id"], expect=1, reason="Verified the writer stopped")
        self.assertEqual(released["contribution"]["release_reason"], "Verified the writer stopped")
        retry = self.call("release", owner=owner["id"], expect=1, reason="Retry")
        self.assertFalse(retry["changed"])
        self.assertEqual(retry["contribution"], released["contribution"])

    def test_drop_requires_inactive_owner_and_is_idempotent(self):
        self.initialize()
        owner = self.claim()
        self.error("active_contribution", "drop", owner=owner["id"], expect=1)
        self.call("release", owner=owner["id"], expect=1, reason="Consolidated")
        self.error("version_conflict", "drop", owner=owner["id"], expect=1)
        self.assertTrue(self.call("drop", owner=owner["id"], expect=2)["changed"])
        self.assertFalse(self.call("drop", owner=owner["id"], expect=2)["changed"])
        self.assertEqual(self.call("status")["contributions"], {})

    def test_lock_is_bounded_and_never_unlinked(self):
        self.initialize()
        lock = self.home / ".runtime.lock"
        inode = lock.stat().st_ino
        with lock.open("a+b") as stream, mock.patch.object(harness, "LOCK_TIMEOUT", 0.03):
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            self.error("lock_busy", "claim", purpose="Other", resource=["src"])
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        self.claim()
        self.assertEqual(lock.stat().st_ino, inode)

    def test_knowledge_hash_and_content_are_from_one_read(self):
        self.initialize()
        text = "# Note\r\nCafé\r\n"
        target = Path(self.identity["knowledge_dir"]) / "note.md"
        target.write_bytes(text.encode("utf-8"))
        original = Path.read_bytes
        def replace_after_read(path):
            content = original(path)
            if path == target:
                target.write_bytes(b"Changed after read")
            return content
        with mock.patch.object(Path, "read_bytes", replace_after_read):
            observed = self.call("read", file="note.md")
        self.assertEqual(observed["content"], text)
        self.assertEqual(observed["sha256"], hashlib.sha256(text.encode("utf-8")).hexdigest())
        self.assertFalse(observed["missing"])

    def test_markdown_cas_retry_and_delete(self):
        self.initialize()
        missing = self.call("read", file="nested/note.md")
        self.assertEqual((missing["missing"], missing["sha256"], missing["content"]), (True, "missing", None))
        first = self.input_file("Original", "first.md")
        second = self.input_file("Revised", "second.md")
        written = self.call("write", file="nested/note.md", input=first, expect="missing")
        self.assertTrue(written["changed"])
        self.assertFalse(self.call("write", file="nested/note.md", input=first, expect="missing")["changed"])
        self.error("document_conflict", "write", file="nested/note.md", input=second, expect="missing")
        updated = self.call("write", file="nested/note.md", input=second, expect=written["sha256"])
        self.error("document_conflict", "delete", file="nested/note.md", expect=written["sha256"])
        self.assertTrue(self.call("delete", file="nested/note.md", expect=updated["sha256"])["changed"])
        self.assertFalse(self.call("delete", file="nested/note.md", expect=updated["sha256"])["changed"])
        self.assertTrue(self.call("read", file="nested/note.md")["missing"])

    def test_knowledge_write_failure_preserves_old_bytes(self):
        self.initialize()
        first = self.call("write", file="note.md", input=self.input_file("Original"), expect="missing")
        with mock.patch.object(harness.os, "replace", side_effect=OSError("injected")):
            self.error("write_failed", "write", file="note.md", input=self.input_file("New"), expect=first["sha256"])
        self.assertEqual(self.call("read", file="note.md")["content"], "Original")

    def test_knowledge_escape_and_symlinks_are_rejected(self):
        self.initialize()
        directory = Path(self.identity["knowledge_dir"])
        target = self.base / "outside.md"
        target.write_text("Keep")
        (directory / "link.md").symlink_to(target)
        (directory / "outside").symlink_to(self.base, target_is_directory=True)
        (directory / "inside.md").write_text("Inside")
        (directory / "inside-link.md").symlink_to(directory / "inside.md")
        for name in ("../project.json", "../outside.md", "project.json", str(target), "link.md", "outside/outside.md", "inside-link.md"):
            for operation in ("read", "write", "delete"):
                self.error("unsafe_path", operation, file=name, input=self.input_file("Bad"), expect="0" * 64)
        self.assertEqual(target.read_text(), "Keep")
        self.assertEqual((directory / "inside.md").read_text(), "Inside")

    def test_knowledge_directory_link_is_rejected(self):
        self.initialize()
        directory = Path(self.identity["knowledge_dir"])
        directory.rmdir()
        directory.symlink_to(self.base, target_is_directory=True)
        self.error("unsafe_path", "read", file="note.md")
        self.error("unsafe_path", "write", file="note.md", input=self.input_file("Bad"), expect="missing")

    def test_simultaneous_document_writes_use_cas(self):
        self.initialize()
        commands = [["write", "--project", str(self.project), "--file", "note.md", "--expect", "missing",
                     "--input", self.input_file(text, text + ".md")] for text in ("First", "Second")]
        results = self.concurrent_cli(commands)
        self.assertEqual(sum("error" not in r for r in results), 1)
        self.assertEqual([r["error"]["code"] for r in results if "error" in r], ["document_conflict"])

    def test_cli_stdin_and_error_shape(self):
        self.initialize()
        completed = subprocess.run([sys.executable, str(HELPER), "--home", str(self.home), "write", "--project",
                                    str(self.project), "--file", "stdin.md", "--expect", "missing", "--input", "-"],
                                   input="# From stdin\n", capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["content"], "# From stdin\n")
        completed = subprocess.run([sys.executable, str(HELPER), "--home", str(self.home), "read", "--project",
                                    str(self.project), "--file", "../bad.md"], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(json.loads(completed.stdout)["error"]["code"], "unsafe_path")
        self.assertEqual(completed.stderr, "")


if __name__ == "__main__":
    unittest.main()
