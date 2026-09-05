from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import json
import multiprocessing
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from harness_runtime import core


def race_worker(home, operation, data, ready, results):
    ready.wait(10)
    try:
        result = core.execute(operation, data, Path(home))
        results.put(("ok", result))
    except core.HarnessError as exc:
        results.put((exc.code, exc.details))
    except Exception as exc:
        results.put(("unexpected", repr(exc)))


class RuntimeTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.home = self.root / "harness"
        self.project = self.root / "project"
        self.project.mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def run_op(self, operation, **data):
        data.setdefault("project", str(self.project))
        if operation in core._WRITES and operation != "init":
            data.setdefault("request_id", str(uuid.uuid4()))
        return core.execute(operation, data, self.home)

    def initialize(self):
        self.initialized = self.run_op("init", title="Test project")
        return self.initialized

    def snapshot(self):
        return core.read_state(core.state_path(self.home, self.initialized["project_id"]))

    def rewrite(self, state):
        core.atomic_json(core.state_path(self.home, state["project"]["id"]), state)

    def start(self, resource="notes/a.md", **data):
        return self.run_op("task.start", objective="Improve source notes", resources=[resource], **data)

    def checkpoint(self, session_id, **data):
        data.setdefault("summary", "Updated the selected notes.")
        data.setdefault("evidence", ["notes/a.md"])
        data.setdefault("next_action", "Review source accuracy.")
        data.setdefault("status", "active")
        return self.run_op("task.checkpoint", session_id=session_id, **data)

    def remember(self, **data):
        payload = {"title": "Authentication endpoint", "summary": "The endpoint needs source verification.",
                   "content": "Mobile authentication currently uses a legacy endpoint.", "kind": "hypothesis",
                   "sources": ["notes/auth.md"], "scope": "project", "aliases": ["autenticação", "móvel"]}
        payload.update(data)
        return self.run_op("remember", **payload)

    def assert_error(self, code, operation, **data):
        with self.assertRaises(core.HarnessError) as caught:
            self.run_op(operation, **data)
        self.assertEqual(code, caught.exception.code, str(caught.exception))
        return caught.exception

    def race(self, operations):
        context = multiprocessing.get_context("spawn")
        ready = context.Event()
        results = context.Queue()
        processes = []
        for operation, data in operations:
            data.setdefault("project", str(self.project))
            data.setdefault("request_id", str(uuid.uuid4()))
            process = context.Process(target=race_worker, args=(str(self.home), operation, data, ready, results))
            process.start()
            processes.append(process)
        ready.set()
        output = [results.get(timeout=20) for _ in processes]
        for process in processes:
            process.join(timeout=20)
            self.assertEqual(0, process.exitcode)
        return output

    def test_reads_never_initialize(self):
        for operation, data in (("resolve", {}), ("task.list", {}), ("consolidate", {}),
                                ("recall", {"query": "source"}), ("maintain", {})):
            self.assert_error("not_initialized", operation, **data)
            self.assertFalse(self.home.exists())
        self.assertEqual([], list(self.project.iterdir()))

    def test_init_idempotent_and_non_git_ancestor_resolution(self):
        first = self.initialize()
        second = self.run_op("init")
        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        self.assertEqual(first["revision"], second["revision"])
        nested = self.project / "drafts/chapter"
        nested.mkdir(parents=True)
        resolved = self.run_op("resolve", project=str(nested))
        self.assertEqual(first["project_id"], resolved["project_id"])
        self.assertEqual(first["workspace"]["id"], resolved["workspace"]["id"])
        self.assertEqual(str(self.project), resolved["workspace"]["path"])
        self.assertEqual(["drafts"], [path.name for path in self.project.iterdir()])
        self.assertEqual(3, self.snapshot()["schema_version"])
        self.assertEqual(7, self.snapshot()["defaults_version"])

    def test_home_inside_scoped_project_is_rejected_before_creating_files(self):
        home = self.project / ".harness"
        with self.assertRaises(core.HarnessError) as caught:
            core.execute("init", {"project": str(self.project)}, home)
        self.assertEqual("state_inside_project", caught.exception.code)
        self.assertFalse(home.exists())

    def test_explicit_uuid_cannot_silently_bind_unrelated_directory(self):
        initialized = self.initialize()
        other = self.root / "other"
        other.mkdir()
        self.assert_error("explicit_binding_required", "init", project=str(other), project_id=initialized["project_id"])
        bound = self.run_op("project.bind", project=str(other), project_id=initialized["project_id"], evidence=["Author confirmed same research project."])
        self.assertEqual(initialized["project_id"], self.run_op("resolve", project=str(other))["project_id"])
        self.assertNotEqual(initialized["workspace"]["id"], bound["workspace"]["id"])

    def test_move_preserves_identity_workspace_and_claims(self):
        initialized = self.initialize()
        started = self.start()
        moved = self.root / "relocated"
        self.project.rename(moved)
        result = self.run_op("project.move", project=str(moved), from_path=str(self.project),
                             project_id=initialized["project_id"], evidence=["The project directory was renamed."])
        self.assertEqual(initialized["workspace"]["id"], result["workspace"]["id"])
        report = self.run_op("consolidate", project=str(moved))
        self.assertEqual(str(moved / "notes/a.md"), report["claims"][0]["path"])
        self.assertEqual(started["session"]["id"], report["claims"][0]["session_id"])
        self.assertEqual(initialized["project_id"], self.run_op("resolve", project=str(moved))["project_id"])

    def git(self, *args, cwd=None):
        result = subprocess.run(["git", "-C", str(cwd or self.project), *args], capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        return result.stdout.strip()

    def setup_git(self):
        self.git("init", "-q")
        self.git("-c", "user.name=Runtime Test", "-c", "user.email=test@example.invalid", "commit", "--allow-empty", "-qm", "Initial")

    def test_git_worktrees_share_identity_but_clones_do_not(self):
        self.setup_git()
        initialized = self.initialize()
        worktree = self.root / "worktree"
        self.git("worktree", "add", "-qb", "chapter", str(worktree))
        resolved = self.run_op("resolve", project=str(worktree))
        self.assertEqual(initialized["project_id"], resolved["project_id"])
        self.assertNotEqual(initialized["workspace"]["id"], resolved["workspace"]["id"])
        self.assertEqual(1, len(self.snapshot()["workspaces"]), "Pure resolve must not enroll a workspace.")
        self.start(project=str(worktree))
        self.assertEqual(2, len(self.snapshot()["workspaces"]))
        cloned = self.root / "clone"
        self.git("clone", "-q", str(self.project), str(cloned))
        self.git("remote", "add", "origin", "https://example.invalid/project.git")
        self.git("remote", "set-url", "origin", "https://example.invalid/project.git", cwd=cloned)
        self.assert_error("not_initialized", "resolve", project=str(cloned))
        separate = self.run_op("init", project=str(cloned))
        self.assertNotEqual(initialized["project_id"], separate["project_id"])

    def test_migrated_git_path_and_worktree_keep_legacy_uuid(self):
        from harness_runtime import migration
        self.setup_git()
        worktree = self.root / "worktree"
        self.git("worktree", "add", "-qb", "migrated-chapter", str(worktree))
        identifier = str(uuid.uuid4())
        legacy = self.home / "projects" / identifier
        legacy.mkdir(parents=True)
        (legacy / "manifest.json").write_text(json.dumps({"id": identifier, "schema_version": 2,
            "display_name": "Existing Git project", "bindings": [{"type": "path", "value": str(self.project)}]}))
        preview = migration.execute("migrate.preview", {}, self.home)
        migration.execute("migrate.apply", {"fingerprint": preview["fingerprint"], "old_agents_stopped": True}, self.home)
        snapshot = legacy / "state.json"
        original = snapshot.read_bytes()
        self.assertEqual(identifier, self.run_op("resolve")["project_id"])
        self.assertEqual(identifier, self.run_op("resolve", project=str(worktree))["project_id"])
        self.assertEqual(original, snapshot.read_bytes(), "Resolving migrated topology must remain read-only.")
        initialized = self.run_op("init")
        self.assertFalse(initialized["created"])
        self.assertEqual(identifier, initialized["project_id"])
        self.assertEqual("git", initialized["workspace"]["kind"])
        self.assertEqual(1, len(list((self.home / "projects").iterdir())))
        self.assertEqual(identifier, self.start(project=str(worktree))["project_id"])

    def test_ancestor_init_bind_and_move_cannot_create_overlapping_identities(self):
        child = self.project / "child"
        child.mkdir()
        child_project = self.run_op("init", project=str(child))
        self.assert_error("identity_overlap", "init")
        self.assertEqual(child_project["project_id"], self.run_op("resolve", project=str(child))["project_id"])
        other = self.root / "other"
        other.mkdir()
        other_project = self.run_op("init", project=str(other))
        before = {path: path.read_bytes() for path in (self.home / "projects").glob("*/state.json")}
        self.assert_error("identity_overlap", "project.bind", project_id=other_project["project_id"], evidence=["Proposed ancestor scope."])
        other.rmdir()
        self.assert_error("identity_overlap", "project.move", project_id=other_project["project_id"], from_path=str(other), evidence=["Proposed relocation into ancestor."])
        self.assertEqual(before, {path: path.read_bytes() for path in (self.home / "projects").glob("*/state.json")})

    def test_claim_race_one_owner_and_atomic_failure(self):
        self.initialize()
        results = self.race([("task.start", {"objective": f"Writer {index}", "resources": ["shared/chapter.md"]}) for index in range(2)])
        self.assertEqual(["ok", "resource_conflict"], sorted(code for code, _ in results))
        state = self.snapshot()
        self.assertEqual(1, len(state["tasks"]))
        self.assertEqual(1, len(state["sessions"]))
        self.assertEqual(1, len(core._live_claims(state)))
        self.assertEqual(2, state["revision"])
        conflict = next(value for code, value in results if code == "resource_conflict")
        self.assertTrue(conflict["conflicts"][0]["owner"]["owner_objective"])

    def test_concurrent_checkpoints_no_lost_update(self):
        self.initialize()
        first = self.start("notes/first.md")
        second = self.run_op("task.join", task_id=first["task"]["id"], resources=["notes/second.md"])
        results = self.race([("task.checkpoint", {"session_id": session["id"], "summary": f"Contribution {index}",
                                                  "evidence": [f"notes/{index}.md"], "next_action": "Review together.", "status": "active"})
                             for index, session in enumerate((first["session"], second["session"]))])
        self.assertEqual(["ok", "ok"], sorted(code for code, _ in results))
        state = self.snapshot()
        self.assertEqual(2, len(state["checkpoints"]))
        self.assertEqual(5, state["revision"])
        self.assertEqual(list(range(1, 6)), [event["revision"] for event in state["events"]])
        self.assertEqual(4, len(state["receipts"]))

    def test_claim_overlaps_parent_file_whole_workspace_and_symlinks(self):
        self.initialize()
        (self.project / "notes").mkdir()
        alias = self.root / "notes-alias"
        alias.symlink_to(self.project / "notes", target_is_directory=True)
        started = self.start("notes")
        for resource in ("notes/chapter.md", ".", str(alias / "chapter.md")):
            self.assert_error("resource_conflict", "task.start", objective="Competing editor", resources=[resource])
        self.assert_error("unsupported_glob", "task.start", objective="Glob editor", resources=["notes/*.md"])
        self.start("notes-other/chapter.md")
        self.run_op("task.release", session_id=started["session"]["id"], reason="Handed the directory to another editor.")
        self.start(str(alias / "chapter.md"))

    def test_cross_workspace_shared_physical_file_conflicts(self):
        initialized = self.initialize()
        other = self.root / "other-workspace"
        other.mkdir()
        self.run_op("project.bind", project=str(other), project_id=initialized["project_id"], evidence=["Shared writing project."])
        shared = self.root / "sources/archive.txt"
        self.start(str(shared))
        self.assert_error("resource_conflict", "task.start", project=str(other), objective="Read and edit archive", resources=[str(shared)])
        self.start("chapter.md", project=str(other))
        self.start("chapter.md")

    def test_stale_presence_does_not_expire_claim_and_maintain_is_read_only(self):
        self.initialize()
        started = self.start()
        state = self.snapshot()
        state["sessions"][started["session"]["id"]]["updated_at"] = "2000-01-01T00:00:00+00:00"
        self.rewrite(state)
        path = core.state_path(self.home, initialized_id := state["project"]["id"])
        before = path.read_bytes()
        self.assert_error("resource_conflict", "task.start", objective="New editor", resources=["notes/a.md"])
        maintained = self.run_op("maintain")
        self.assertEqual("unknown", maintained["claims"][0]["presence"])
        self.assertIn("unknown_presence", [issue["kind"] for issue in maintained["issues"]])
        self.assertEqual(before, path.read_bytes())

    def test_request_replay_returns_original_result_current_revision_and_rejects_mismatch(self):
        self.initialize()
        started = self.start(request_id="start-one")
        self.start("other.md")
        replay = self.start(request_id="start-one")
        self.assertEqual(started["session"], replay["session"])
        self.assertEqual(2, replay["original_revision"])
        self.assertEqual(3, replay["revision"])
        self.assertTrue(replay["replayed"])
        self.assert_error("request_id_reused", "task.start", objective="Changed objective", resources=["notes/a.md"], request_id="start-one")
        self.assertEqual(2, len(self.snapshot()["sessions"]))

    def test_compare_revision_and_input_ids_are_not_trusted_participant_ids(self):
        self.initialize()
        self.assert_error("revision_conflict", "task.start", objective="stale plan", resources=["x"], expected_revision=0)
        result = self.start(session_id="made-up", task_id="made-up")
        self.assertNotEqual("made-up", result["session"]["id"])
        self.assertNotEqual("made-up", result["task"]["id"])
        self.assertEqual(2, self.snapshot()["revision"])

    def test_replace_failure_retains_snapshot_and_retry_can_succeed(self):
        self.initialize()
        started = self.start()
        path = core.state_path(self.home, started["project_id"])
        before = path.read_bytes()
        with patch.object(core.os, "replace", side_effect=OSError("injected replace failure")):
            self.assert_error("write_failed", "task.checkpoint", session_id=started["session"]["id"], summary="Ready", evidence=[],
                              next_action="Accept", status="delivered", request_id="retry-delivery")
        self.assertEqual(before, path.read_bytes())
        self.assertEqual([], list(path.parent.glob(".state-*")))
        result = self.run_op("task.checkpoint", session_id=started["session"]["id"], summary="Ready", evidence=[],
                             next_action="Accept", status="delivered", request_id="retry-delivery")
        self.assertEqual(3, result["revision"])
        self.assertEqual(0, len(core._live_claims(self.snapshot())))

    def test_delivery_retains_next_action_and_replay_does_not_revive_claims(self):
        self.initialize()
        started = self.start()
        delivered = self.checkpoint(started["session"]["id"], status="delivered", next_action="Acceptance pending.", request_id="delivery")
        self.assertEqual("delivered", delivered["task"]["status"])
        self.assertFalse(delivered["task"]["events"])
        report = self.run_op("consolidate")
        self.assertEqual([], report["claims"])
        self.assertEqual("Acceptance pending.", report["pending"][0]["next_action"])
        self.checkpoint(started["session"]["id"], status="delivered", next_action="Acceptance pending.", request_id="delivery")
        self.assert_error("session_closed", "task.checkpoint", session_id=started["session"]["id"], summary="Back", status="active")
        event = self.run_op("task.event", session_id=started["session"]["id"], kind="accepted", evidence=["Explicit user acceptance."])
        self.assertEqual("accepted", event["event"]["kind"])

    def test_release_closes_participant_and_uncertain_task_is_not_delivered(self):
        self.initialize()
        started = self.start()
        joined = self.run_op("task.join", task_id=started["task"]["id"], resources=["other.md"])
        self.run_op("task.release", session_id=joined["session"]["id"], reason="Contributor stopped before verification.")
        delivered = self.checkpoint(started["session"]["id"], status="delivered")
        self.assertEqual("blocked", delivered["task"]["status"])
        self.assert_error("session_closed", "task.claim", session_id=joined["session"]["id"], resources=["other.md"])

    def test_explicit_follow_up_resolution_keeps_history_and_exposes_lifecycle(self):
        self.initialize()
        started = self.start()
        delivered = self.checkpoint(started["session_id"], status="delivered", next_action="User acceptance pending.")
        checkpoint_id = delivered["checkpoint_id"]
        original_checkpoint = copy.deepcopy(delivered["checkpoint"])
        self.run_op("task.event", session_id=started["session_id"], kind="accepted", evidence=["User accepted the contribution."])
        self.assertEqual(1, len(self.run_op("consolidate")["pending"]), "An event kind must not silently infer follow-up resolution.")
        result = self.run_op("task.event", session_id=started["session_id"], kind="resolved", evidence=["User acceptance satisfies this checkpoint follow-up."],
                             resolves_checkpoint_ids=[checkpoint_id])
        report = self.run_op("consolidate")
        self.assertEqual([], report["pending"])
        self.assertEqual(["accepted", "resolved"], [event["kind"] for event in report["task_events"]])
        self.assertEqual(result["event"]["id"], report["contributions"][0]["next_action_resolved_by"])
        self.assertEqual(original_checkpoint, self.snapshot()["checkpoints"][checkpoint_id])
        unrelated = self.start("unrelated.md")
        self.assert_error("invalid_resolution", "task.event", session_id=unrelated["session_id"], kind="resolved", evidence=["Wrong task."],
                          resolves_checkpoint_ids=[checkpoint_id])
        self.assert_error("evidence_required", "task.event", session_id=started["session_id"], kind="resolved", evidence=[],
                          resolves_checkpoint_ids=[checkpoint_id])

    def test_replacement_delivery_can_explicitly_reconcile_released_participant(self):
        self.initialize()
        started = self.start()
        self.run_op("task.release", session_id=started["session_id"], reason="A replacement will complete this contribution.")
        replacement = self.run_op("task.join", task_id=started["task_id"], resources=["notes/a.md"])
        delivered = self.checkpoint(replacement["session_id"], status="delivered", next_action="")
        self.assertEqual("blocked", delivered["task"]["status"])
        resolved = self.run_op("task.event", session_id=replacement["session_id"], kind="resolved",
                               evidence=["Replacement delivery includes the predecessor's assigned work."], resolves_session_ids=[started["session_id"]])
        self.assertEqual("delivered", resolved["task"]["status"])
        self.assertEqual("released", self.snapshot()["sessions"][started["session_id"]]["status"])
        report = self.run_op("consolidate")
        self.assertEqual([], report["pending"])
        self.assertEqual([], report["claims"])
        active = self.run_op("task.join", task_id=started["task_id"], resources=["new.md"])
        self.assert_error("invalid_resolution", "task.event", session_id=replacement["session_id"], kind="resolved", evidence=["Cannot infer completion."],
                          resolves_session_ids=[active["session_id"]])

    def test_five_chats_consolidate_latest_evidence_and_all_claims(self):
        self.initialize()
        sessions = []
        for index in range(5):
            result = self.start(f"chapter-{index}.md")
            sessions.append(result["session"]["id"])
            self.checkpoint(sessions[-1], summary=f"Earlier contribution {index}.")
            self.checkpoint(sessions[-1], summary=f"Latest contribution {index}.", evidence=[f"chapter-{index}.md"],
                            next_action=f"Verify chapter {index}.", status="delivered" if index < 3 else "active")
        report = self.run_op("consolidate", budget_chars=1)
        self.assertEqual(5, len(report["contributions"]))
        self.assertEqual(2, len(report["claims"]))
        self.assertEqual(5, len(report["pending"]))
        self.assertTrue(all(item["summary"].startswith("Latest") for item in report["contributions"]))
        self.assertNotIn("history", report)
        self.assertEqual(10, len(self.run_op("consolidate", include_history=True)["history"]))
        self.assertFalse(report["diagnostics"]["truncated"])

    def test_unknown_workspace_contribution_remains_visible(self):
        self.initialize()
        started = self.start()
        state = self.snapshot()
        state["sessions"][started["session"]["id"]]["workspace_id"] = "unknown-workspace"
        state["sessions"][started["session"]["id"]]["presence_unknown"] = True
        self.rewrite(state)
        report = self.run_op("consolidate")
        self.assertEqual(1, len(report["unknown_workspace_contributions"]))
        self.assertEqual(1, len(report["claims"]))
        self.assertEqual(1, len(report["pending"]))

    def test_changes_paginate_without_skips_and_invalid_future_is_error(self):
        self.initialize()
        for index in range(5):
            self.start(f"chapter-{index}.md")
        page = self.run_op("changes", since=0, limit=2)
        revisions = [event["revision"] for event in page["events"]]
        through = page["through_revision"]
        self.start("later.md")
        while page["has_more"]:
            page = self.run_op("changes", cursor=page["next_cursor"], limit=2)
            revisions.extend(event["revision"] for event in page["events"])
            self.assertEqual(through, page["through_revision"])
        self.assertEqual(list(range(1, 7)), revisions)
        newer = self.run_op("changes", since=page["next_revision"])
        self.assertEqual([7], [event["revision"] for event in newer["events"]])
        blocked = self.run_op("changes", since=0, budget_chars=1)
        self.assertEqual("omitted_budget", blocked["status"])
        self.assertTrue(blocked["has_more"])
        self.assertEqual(0, blocked["next_revision"])
        resumed = self.run_op("changes", cursor=blocked["next_cursor"], budget_chars=10000)
        self.assertEqual(list(range(1, 8)), [event["revision"] for event in resumed["events"]])
        self.assert_error("invalid_cursor", "changes", since=100)
        self.assert_error("invalid_cursor", "changes", cursor="not-valid-json")

    def test_memory_epistemic_status_provenance_and_explicit_updates(self):
        self.initialize()
        memory = self.remember()["memory"]
        self.assertEqual("hypothesis", memory["kind"])
        self.start("other.md")
        updated = self.run_op("memory.update", id=memory["id"], expected_revision=memory["revision"],
                              summary="Still unverified; no automatic promotion.", status="stale")["memory"]
        self.assertEqual("hypothesis", updated["kind"])
        self.assertEqual("stale", updated["status"])
        self.assertEqual(memory["sources"], updated["sources"])
        self.assertEqual(memory["content"], updated["history"][0]["content"])
        self.assert_error("revision_conflict", "memory.update", id=memory["id"], expected_revision=memory["revision"], kind="fact")
        newer = self.remember(title="Verified authentication", kind="fact")["memory"]
        superseded = self.run_op("memory.update", id=memory["id"], expected_revision=updated["revision"], status="superseded", superseded_by=newer["id"])["memory"]
        self.assertEqual(newer["id"], superseded["superseded_by"])
        self.assert_error("invalid_supersession", "memory.update", id=newer["id"], expected_revision=newer["revision"], status="superseded", superseded_by=memory["id"])

    def test_multilingual_lexical_recall_and_budgets_distinguish_absence(self):
        self.initialize()
        memory = self.remember()["memory"]
        recall = self.run_op("recall", query="autenticação móvel", budget_chars=2000)
        self.assertEqual("found", recall["status"])
        self.assertEqual(memory["id"], recall["entries"][0]["id"])
        self.assertNotIn("content", recall["entries"][0])
        self.assertEqual("lexical", recall["diagnostics"]["method"])
        self.assertIn("authentication", recall["diagnostics"]["expanded_terms"])
        omitted = self.run_op("recall", query="autenticação", budget_chars=1)
        self.assertEqual("omitted_budget", omitted["status"])
        self.assertEqual(1, omitted["total_matches"])
        self.assertEqual("absent", self.run_op("recall", query="aardvark-nonexistent")["status"])
        self.assertEqual("omitted_limit", self.run_op("recall", query="auth", limit=0)["status"])
        self.assertEqual("omitted_budget", self.run_op("hydrate", id=memory["id"], budget_chars=1)["status"])
        self.assertEqual("found", self.run_op("hydrate", id=memory["id"], budget_chars=2000)["status"])
        self.assertEqual("absent", self.run_op("hydrate", id="nonexistent")["status"])

    def test_stale_contradictory_and_missing_source_memory_is_visible_not_deleted(self):
        self.initialize()
        first = self.remember(review_after="2000-01-01T00:00:00+00:00")["memory"]
        second = self.remember(content="Mobile authentication uses a new endpoint.", kind="fact")["memory"]
        before = self.snapshot()
        report = self.run_op("maintain")
        kinds = {issue["kind"] for issue in report["issues"]}
        self.assertTrue({"stale_memory", "possible_contradiction", "missing_source"}.issubset(kinds))
        self.assertEqual(before, self.snapshot())
        cards = self.run_op("recall", query="mobile")
        self.assertEqual({first["id"], second["id"]}, {card["id"] for card in cards["entries"]})
        self.assertTrue(next(card for card in cards["entries"] if card["id"] == first["id"])["stale"])

    def test_corruption_future_schema_and_legacy_state_fail_loud(self):
        self.initialize()
        path = core.state_path(self.home, self.initialized["project_id"])
        original = path.read_bytes()
        for payload, error in ((b'{"schema_version":3,"schema_version":3}', "corrupt_state"),
                               (b'{"schema_version":99}', "unsupported_schema"), (b'not JSON', "corrupt_state")):
            path.write_bytes(payload)
            self.assert_error(error, "init")
            self.assertEqual(1, len(list((self.home / "projects").iterdir())))
        path.write_bytes(original)
        legacy = self.home / "projects" / str(uuid.uuid4())
        legacy.mkdir()
        (legacy / "manifest.json").write_text("{}")
        self.assert_error("migration_required", "resolve")

    def test_malformed_records_and_missing_journal_revisions_are_structured_errors(self):
        self.initialize()
        started = self.start()
        checkpoint = self.checkpoint(started["session_id"])
        memory = self.remember()["memory"]
        original = self.snapshot()
        cases = (("sessions", started["session_id"], "checkpoint_ids"), ("tasks", started["task_id"], "objective"),
                 ("checkpoints", checkpoint["checkpoint_id"], "summary"), ("memories", memory["id"], "sources"))
        for collection, identifier, field in cases:
            state = copy.deepcopy(original)
            state[collection][identifier].pop(field)
            self.rewrite(state)
            self.assert_error("corrupt_state", "consolidate")
            self.assert_error("corrupt_state", "task.show", task_id=started["task_id"])
        state = copy.deepcopy(original)
        state["events"].pop(1)
        self.rewrite(state)
        self.assert_error("corrupt_state", "changes", since=0)


if __name__ == "__main__":
    unittest.main()
