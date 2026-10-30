"""Public input/output flows and critical concurrency/process invariants."""

from __future__ import annotations

import concurrent.futures
import copy
import json
import os
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CLI = REPO / "bin" / "harness"


class Contracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="harness test ")
        self.base = Path(self.temp.name)
        self.root = self.base / "data"
        self.project = self.base / "project"
        self.project.mkdir()
        fixture_bin = self.base / "bin"
        fixture_bin.mkdir()
        fixture = (REPO / "tests" / "fixtures" / "provider.py").read_text().split("\n", 1)[1]
        for provider in ("codex", "claude"):
            path = fixture_bin / provider
            path.write_text(f"#!{sys.executable}\n" + fixture)
            path.chmod(0o755)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("HARNESS_")}
        self.env.update(
            HARNESS_ROOT=str(self.root),
            HARNESS_PYTHON=sys.executable,
            HARNESS_FIXTURE_CLI=str(CLI),
            PATH=str(fixture_bin) + os.pathsep + self.env["PATH"],
        )
        self.call("setup")
        self.call("environment", "ensure", "app", "--title", "Application")
        self.call(
            "--environment", "app", "resource", "add", "source", "--location", str(self.project)
        )
        self.call(
            "--environment",
            "app",
            "work",
            "create",
            "feature",
            "--title",
            "Feature",
            "--purpose",
            "Deliver the feature.",
        )
        self.run_ids = []

    def tearDown(self):
        for key in self.run_ids:
            self.call("run", "stop", key, ok=None)
        end = time.monotonic() + 6
        while time.monotonic() < end:
            with sqlite3.connect(self.root / "state.sqlite") as db:
                count = db.execute(
                    "SELECT count(*) FROM runs WHERE supervisor_pid IS NOT NULL"
                ).fetchone()[0]
            if not count:
                break
            time.sleep(0.1)
        self.temp.cleanup()

    def call(self, *args, ok=True, env=None):
        result = subprocess.run(
            [str(CLI), "--json", *args],
            env=env or self.env,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertTrue(result.stdout.strip(), result.stderr)
        value = json.loads(result.stdout)
        if ok is not None:
            self.assertEqual(value["ok"], ok, value)
        if value["ok"]:
            self.assertEqual(result.returncode, 0, result.stderr)
            return value["data"]
        self.assertEqual(result.returncode, 2, result.stderr)
        return value["error"]

    def file(self, name, value):
        path = self.base / name
        path.write_text(json.dumps(value) if not isinstance(value, str) else value)
        return str(path)

    def limits(self, **overrides):
        limits = {
            "seconds": 30,
            "attempt_seconds": 5,
            "concurrency": 2,
            "max_attempts": 12,
            "max_rounds": 3,
        }
        limits.update(overrides)
        self.call("config", "limits", "--file", self.file("limits.json", limits))

    def start(
        self,
        mode="reply",
        workflow=None,
        autonomous=False,
        brief="Complete the assigned scope.",
        provider="codex",
        model="fixture-model",
        effort="medium",
    ):
        self.env["HARNESS_FIXTURE_MODE"] = mode
        args = [
            "--environment",
            "app",
            "--work",
            "feature",
            "run",
            "start",
            "--file",
            self.file("brief.md", brief),
            "--resource",
            "source",
        ]
        if workflow:
            args += ["--workflow", workflow]
        else:
            args += [
                "--provider",
                provider,
                "--model",
                model,
                "--effort",
                effort,
                "--reason",
                "This fixture can verify the assigned observable behavior.",
            ]
        args += (
            ["--autonomous"]
            if autonomous
            else ["--authorization", "The user requested this execution."]
        )
        run = self.call(*args)
        self.run_ids.append(run["run"])
        return run["run"]

    def wait(self, key, predicate, timeout=15):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            state = self.call("run", "status", key)
            if predicate(state):
                return state
            time.sleep(0.08)
        log = self.root / ".runtime" / key / "supervisor.log"
        failures = [
            self.call("run", "result", key, p["id"], ok=None)
            for p in state["participants"]
            if p["state"] == "failed"
        ]
        self.fail(
            f"Execution did not reach the expected state: {state}\n"
            f"Failed results: {failures}\n{log.read_text() if log.exists() else ''}"
        )

    def workflow(self, mode="develop"):
        ref = "environments/app/work/feature/module.md"
        if not (self.root / ref).exists():
            self.call(
                "record", "write", ref, "--text", "# Module\n\nImplement the observable contract."
            )
        definition = self.call(
            "--environment",
            "app",
            "--work",
            "feature",
            "workflow",
            "template",
            "--mode",
            mode,
            "--module",
            "api",
            "--resource",
            "source",
            "--context",
            ref,
        )["definition"]
        definition["integration"]["selection"] = self.choice("codex")
        nodes = definition["modules"][0]["nodes"]
        nodes["coordinator"]["selection"] = self.choice("codex")
        nodes["worker"]["selection"] = self.choice("claude")
        return self.call(
            "--environment",
            "app",
            "--work",
            "feature",
            "workflow",
            "create",
            mode,
            "--file",
            self.file(mode + ".json", definition),
        )

    def choice(self, provider="codex"):
        return {
            "provider": provider,
            "model": "fixture-model",
            "effort": "medium",
            "reason": "This fixture can verify the assigned observable behavior.",
        }

    def test_setup_preserves_host_configuration_and_user_data(self):
        host = self.base / "host"
        (host / ".codex").mkdir(parents=True)
        config = host / ".codex" / "config.toml"
        config.write_text(
            'model = "chosen"\n[memories]\nuse_memories = true\ncustom = "keep"\n[other]\nvalue = 3\n'
        )
        instructions = host / ".codex" / "AGENTS.md"
        instructions.write_text("User instructions.\n")
        self.call("setup", "--host", "codex", "--host-home", str(host))
        once = config.read_text(), instructions.read_text()
        self.call("setup", "--host", "codex", "--host-home", str(host))
        self.assertEqual(once, (config.read_text(), instructions.read_text()))
        import tomllib

        data = tomllib.loads(config.read_text())
        self.assertEqual(data["other"]["value"], 3)
        self.assertEqual(data["memories"]["custom"], "keep")
        self.assertFalse(data["memories"]["use_memories"])
        self.assertIn("User instructions.", instructions.read_text())
        self.assertTrue(self.call("--environment", "app", "work", "show", "feature")["content"])

    def test_new_install_has_no_model_defaults_and_requires_a_launch_selection(self):
        settings = self.call("config", "show")["settings"]
        self.assertEqual(set(settings), {"version", "limits"})
        for partial in (
            [],
            ["--provider", "codex"],
            ["--provider", "claude", "--model", "fixture-model", "--effort", "low"],
        ):
            error = self.call(
                "--environment",
                "app",
                "run",
                "start",
                "--resource",
                "source",
                "--text",
                "Inspect the assigned code.",
                "--autonomous",
                *partial,
                ok=False,
            )
            self.assertEqual(error["code"], "invalid_selection")
        self.assertEqual(self.call("run", "list")["runs"], [])

    def test_model_choice_reaches_each_provider_without_a_fallback(self):
        self.limits(seconds=10)
        for provider, model, effort in (
            ("codex", "selected-codex", "high"),
            ("claude", "selected-claude", "low"),
        ):
            with self.subTest(provider=provider):
                key = self.start(
                    "selection", provider=provider, model=model, effort=effort, autonomous=True
                )
                state = self.wait(key, lambda s: s["state"] == "waiting")
                participant = state["participants"][0]
                chosen = participant["selection"]
                self.assertEqual(
                    (chosen["provider"], chosen["model"], chosen["effort"]),
                    (provider, model, effort),
                )
                actual = json.loads(self.call("run", "result", key, participant["id"])["content"])
                self.assertEqual(actual, {"provider": provider, "model": model, "effort": effort})
                self.assertEqual(state["limits"]["max_attempts"], 1)
                self.assertEqual(state["limits"]["concurrency"], 1)
                self.assertEqual(state["limits"]["seconds"], 10)
        # A rejected provider attempt remains failed instead of switching models or retrying.
        self.limits(seconds=20)
        key = self.start("fail", provider="claude", model="unavailable-model", effort="low")
        state = self.wait(key, lambda s: s["state"] == "waiting")
        self.assertEqual(len(state["attempts"]), 1)
        self.assertEqual(state["attempts"][0]["state"], "failed")
        self.assertEqual(state["participants"][0]["selection"]["model"], "unavailable-model")

    def test_configuration_can_remove_legacy_profiles_without_losing_unrelated_settings(self):
        legacy = json.loads((self.root / "config.json").read_text())
        legacy.update(
            profiles={"custom": {"model": "old-choice"}},
            defaults={"scout": "custom"},
            extension={"keep": True},
        )
        (self.root / "config.json").write_text(json.dumps(legacy))
        current = self.call("config", "show")
        # Legacy choices are readable, but cannot become an implicit launch choice.
        self.assertEqual(
            self.call(
                "--environment",
                "app",
                "run",
                "start",
                "--resource",
                "source",
                "--text",
                "Inspect.",
                "--autonomous",
                ok=False,
            )["code"],
            "invalid_selection",
        )
        replacement = {
            k: v for k, v in current["settings"].items() if k not in ("profiles", "defaults")
        }
        args = (
            "config",
            "write",
            "--file",
            self.file("replacement.json", replacement),
            "--revision",
            current["revision"],
        )
        self.assertEqual(self.call(*args)["settings"]["extension"], {"keep": True})
        self.assertEqual(self.call(*args, ok=False)["code"], "conflict")
        self.call("setup")
        self.assertEqual(self.call("config", "show")["settings"], replacement)

    def test_workflow_template_requires_agent_choices_before_it_can_be_saved(self):
        definition = self.call(
            "workflow", "template", "--mode", "develop", "--module", "api", "--resource", "source"
        )["definition"]
        self.assertIsNone(definition["integration"]["selection"])
        self.assertTrue(
            all(node["selection"] is None for node in definition["modules"][0]["nodes"].values())
        )
        error = self.call(
            "--environment",
            "app",
            "--work",
            "feature",
            "workflow",
            "create",
            "unassigned",
            "--file",
            self.file("unassigned.json", definition),
            ok=False,
        )
        self.assertEqual(error["code"], "invalid_selection")
        self.assertFalse(
            (self.root / "environments/app/work/feature/workflows/unassigned.json").exists()
        )

    def test_capture_retrieve_and_synthesize_through_record_operations(self):
        capture = self.call(
            "--environment",
            "app",
            "memory",
            "capture",
            "--title",
            "Timeout observation",
            "--text",
            "Checkout retries require a bounded timeout.",
            "--source",
            "Observed endpoint test",
        )
        self.assertEqual(
            self.call("--environment", "app", "memory", "search", "--query", "timeout")["items"], []
        )
        self.assertEqual(
            len(
                self.call(
                    "--environment", "app", "memory", "search", "--captures", "--query", "timeout"
                )["items"]
            ),
            1,
        )
        note = self.call(
            "--environment",
            "app",
            "memory",
            "put",
            "checkout",
            "--text",
            "# Checkout retries\n\nBound retries by the request deadline.\n\n## Source\n\nObserved endpoint test.",
        )
        self.assertEqual(
            len(
                self.call("--environment", "app", "memory", "search", "--query", "retries")["items"]
            ),
            1,
        )
        self.call("record", "delete", capture["path"], "--revision", capture["revision"])
        self.assertIn("request deadline", self.call("record", "read", note["path"])["content"])
        self.assertEqual(
            self.call("memory", "search", "--global", "--query", "retries")["items"], []
        )

    def test_concurrent_record_updates_detect_conflict(self):
        path = "environments/app/work/feature/decision.md"
        old = self.call("record", "write", path, "--text", "# Decision\n\nOriginal.")

        def write(text):
            return self.call(
                "record", "write", path, "--text", text, "--revision", old["revision"], ok=None
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            values = list(pool.map(write, ["# Decision\n\nOne.", "# Decision\n\nTwo."]))
        self.assertEqual(sum(v.get("code") == "conflict" for v in values), 1)
        self.assertIn(
            self.call("record", "read", path)["content"],
            ("# Decision\n\nOne.\n", "# Decision\n\nTwo.\n"),
        )
        alias = path.replace("decision.md", "Decision.md")
        if (self.root / alias).exists():
            current = self.call("record", "read", path)

            def update_alias(target):
                return self.call(
                    "record",
                    "write",
                    target,
                    "--text",
                    "# Decision\n\nUpdated through " + target,
                    "--revision",
                    current["revision"],
                    ok=None,
                )

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                values = list(pool.map(update_alias, [path, alias]))
            self.assertEqual(sum(v.get("code") == "conflict" for v in values), 1)

    def test_path_boundaries_and_pagination(self):
        self.assertEqual(
            self.call("record", "write", "../escape.md", "--text", "# Escape", ok=False)["code"],
            "invalid_path",
        )
        target = self.root / "environments" / "app" / "work" / "feature" / "outside"
        target.symlink_to(self.base)
        self.assertEqual(
            self.call(
                "record",
                "write",
                "environments/app/work/feature/outside/escape.md",
                "--text",
                "# Escape",
                ok=False,
            )["code"],
            "invalid_path",
        )
        self.assertEqual(
            self.call("record", "read", "environments/app/work/feature/work.md", "--limit", "1")[
                "content"
            ],
            "#",
        )
        self.assertEqual(len(self.call("environment", "list")["items"]), 1)
        canonical = "environments/app/work/feature/work.md"
        current = self.call("record", "read", canonical)
        for alias in (canonical.replace("/app/", "//app/"), "./" + canonical):
            self.assertEqual(self.call("record", "read", alias, ok=False)["code"], "invalid_path")
            self.assertEqual(
                self.call(
                    "record",
                    "write",
                    alias,
                    "--text",
                    "# Overwrite",
                    "--revision",
                    current["revision"],
                    ok=False,
                )["code"],
                "invalid_path",
            )
            self.assertEqual(
                self.call("record", "delete", alias, "--revision", current["revision"], ok=False)[
                    "code"
                ],
                "invalid_path",
            )
        self.assertEqual(self.call("record", "read", canonical)["revision"], current["revision"])

    def test_invalid_json_shapes_return_structured_errors_without_partial_writes(self):
        before = (self.root / "config.json").read_bytes()
        revision = self.call("config", "show")["revision"]
        for value, error in (
            ([], "invalid_config"),
            (None, "invalid_config"),
            ({"version": 1, "limits": []}, "invalid_limits"),
        ):
            self.assertEqual(
                self.call(
                    "config",
                    "write",
                    "--file",
                    self.file("config.json", value),
                    "--revision",
                    revision,
                    ok=False,
                )["code"],
                error,
            )
        self.assertEqual((self.root / "config.json").read_bytes(), before)
        self.workflow()
        original = self.call(
            "--environment", "app", "--work", "feature", "workflow", "read", "develop"
        )["definition"]
        cases = [
            ([], "invalid_workflow"),
            ({**original, "modules": [None]}, "invalid_workflow"),
            ({**original, "limits": []}, "invalid_limits"),
            ({**original, "integration": []}, "invalid_workflow"),
        ]
        for choice in (
            None,
            [],
            {},
            {**self.choice(), "reason": ""},
            {**self.choice(), "effort": False},
        ):
            definition = copy.deepcopy(original)
            definition["modules"][0]["nodes"]["worker"]["selection"] = choice
            cases.append((definition, "invalid_selection"))
        for field, value in (
            ("nodes", {"coordinator": None, "worker": {}}),
            ("edges", [None]),
            ("resource", []),
            ("depends_on", [None]),
        ):
            definition = copy.deepcopy(original)
            definition["modules"][0][field] = value
            cases.append((definition, "invalid_workflow"))
        for definition, code in cases:
            self.assertEqual(
                self.call(
                    "--environment",
                    "app",
                    "workflow",
                    "validate",
                    "--file",
                    self.file("invalid.json", definition),
                    ok=False,
                )["code"],
                code,
            )

    def test_exit_success_requires_explicit_acceptance_and_message_receipts(self):
        self.limits()
        key = self.start()
        state = self.wait(key, lambda s: s["state"] == "waiting")
        participant = state["participants"][0]["id"]
        result = self.call("run", "result", key, participant)
        self.assertEqual(result["content"], "Fixture result verified.")
        message = self.call(
            "message", "send", key, "--to", "operator", "--text", "Inspect this result."
        )["message"]
        self.assertEqual(self.call("message", "ack", message, ok=False)["code"], "not_read")
        first = self.call("message", "read", message)
        second = self.call("message", "read", message)
        self.assertEqual(first["read_at"], second["read_at"])
        ack = self.call("message", "ack", message)
        self.assertEqual(ack["acknowledged"], self.call("message", "ack", message)["acknowledged"])
        self.call(
            "run",
            "decide",
            key,
            "--event",
            "accept",
            "--reason",
            "Verified the contract.",
            "--revision",
            str(state["revision"]),
        )
        self.assertEqual(self.call("run", "status", key)["state"], "accepted")

    def test_both_graphs_correct_and_accept_through_public_tools(self):
        for mode in ("develop", "review"):
            with self.subTest(mode=mode):
                self.limits(seconds=45)
                self.workflow(mode)
                key = self.start("graph", workflow=mode)
                state = self.wait(
                    key, lambda s: s["state"] in ("accepted", "failed", "expired"), timeout=25
                )
                self.assertEqual(state["state"], "accepted", state)
                workers = [p for p in state["participants"] if p["role"] == "worker"]
                self.assertEqual(workers[0]["rounds"], 3)
                self.assertLessEqual(len(state["attempts"]), 12)

    def test_graph_handles_fast_results_and_integration_helpers(self):
        self.limits(seconds=45, max_attempts=16)
        self.workflow()
        for mode in ("graph-race", "graph-helpers", "graph-helper-retry"):
            with self.subTest(mode=mode):
                key = self.start(mode, workflow="develop")
                state = self.wait(
                    key, lambda s: s["state"] in ("accepted", "failed", "expired"), timeout=25
                )
                self.assertEqual(state["state"], "accepted", state)
                self.assertEqual(
                    next(p for p in state["participants"] if p["role"] == "worker")["rounds"], 3
                )
                if mode in ("graph-helpers", "graph-helper-retry"):
                    self.assertEqual(
                        next(p for p in state["participants"] if p["role"] == "helper")["state"],
                        "complete",
                    )
                if mode == "graph-helper-retry":
                    helper = next(p for p in state["participants"] if p["role"] == "helper")
                    self.assertEqual(
                        helper["selection"],
                        {
                            "provider": "claude",
                            "model": "fixture-helper",
                            "effort": "low",
                            "reason": "A bounded economical check with a clear fixture result.",
                        },
                    )
                    self.assertTrue(helper["read_only"])
                    self.assertEqual(
                        [
                            a["state"]
                            for a in state["attempts"]
                            if a["participant_id"] == helper["id"]
                        ],
                        ["failed", "complete"],
                    )

    def test_cancelled_workflow_can_resume_and_explicitly_retry_interrupted_worker(self):
        self.limits(seconds=45, attempt_seconds=10, max_attempts=16)
        self.workflow()
        key = self.start("graph-resume", workflow="develop")
        before = self.wait(key, lambda s: (self.project / "worker-started").exists())
        self.call("run", "stop", key)
        saved = self.call(
            "--environment", "app", "--work", "feature", "workflow", "read", "develop"
        )
        saved["definition"]["modules"][0]["nodes"]["worker"]["selection"]["model"] = (
            "next-execution-model"
        )
        self.call(
            "--environment",
            "app",
            "--work",
            "feature",
            "workflow",
            "write",
            "develop",
            "--file",
            self.file("next-workflow.json", saved["definition"]),
            "--revision",
            saved["revision"],
        )
        (self.project / "allow-worker").touch()
        until = time.monotonic() + 5
        while time.monotonic() < until:
            result = self.call(
                "run", "resume", key, "--reason", "The user requested continuation.", ok=None
            )
            if result.get("state") == "active":
                break
            self.assertEqual(result.get("code"), "in_use", result)
            time.sleep(0.05)
        else:
            self.fail("Previous supervisor did not finish cancellation")
        after = self.wait(
            key, lambda s: s["state"] in ("accepted", "failed", "expired"), timeout=20
        )
        self.assertEqual(after["state"], "accepted", after)
        self.assertEqual(after["deadline"], before["deadline"])
        self.assertEqual(
            {p["id"]: p["selection"] for p in after["participants"]},
            {p["id"]: p["selection"] for p in before["participants"]},
        )
        self.assertEqual(
            next(p for p in after["participants"] if p["role"] == "worker")["rounds"], 3
        )
        self.assertTrue(any(a["state"] == "interrupted" for a in after["attempts"]))

    def test_cancel_stops_descendants_and_does_not_resume_from_message(self):
        self.limits(attempt_seconds=20)
        key = self.start("sleep")
        self.wait(key, lambda s: bool(s["attempts"]) and s["attempts"][0]["state"] == "running")
        end = time.monotonic() + 5
        while not (self.project / "child.pid").exists() and time.monotonic() < end:
            time.sleep(0.05)
        child = int((self.project / "child.pid").read_text())
        self.call("run", "stop", key)
        state = self.wait(key, lambda s: s["state"] == "cancelled")
        self.call(
            "message",
            "send",
            key,
            "--to",
            state["participants"][0]["id"],
            "--text",
            "Pending context.",
        )
        time.sleep(0.4)
        self.assertEqual(self.call("run", "status", key)["state"], "cancelled")
        ps = subprocess.run(["ps", "-p", str(child), "-o", "stat="], capture_output=True, text=True)
        self.assertTrue(not ps.stdout.strip() or ps.stdout.strip().startswith("Z"), ps.stdout)

    def test_attempt_deadline_and_resumption_share_budget(self):
        self.limits(seconds=20, attempt_seconds=1, max_attempts=1)
        key = self.start("sleep")
        state = self.wait(key, lambda s: s["state"] == "waiting")
        self.assertEqual(state["attempts"][0]["reason"], "Attempt deadline reached")
        self.assertEqual(
            self.call("run", "resume", key, "--reason", "Retry requested.", ok=False)["code"],
            "budget_exhausted",
        )
        self.assertEqual(self.call("run", "status", key)["deadline"], state["deadline"])

    def test_attempt_deadline_remains_active_when_provider_does_not_read_stdin(self):
        self.limits(seconds=15, attempt_seconds=1, max_attempts=1)
        start = time.monotonic()
        key = self.start("no-stdin", brief="🧪" * 32000)
        state = self.wait(key, lambda s: s["state"] == "waiting", timeout=6)
        self.assertEqual(state["attempts"][0]["reason"], "Attempt deadline reached")
        self.assertLess(time.monotonic() - start, 6)

    def test_cancel_revokes_a_reserved_attempt_before_provider_launch(self):
        gate = self.base / "prompt-gate"
        hooks = self.base / "python-hooks"
        hooks.mkdir()
        (hooks / "sitecustomize.py").write_text(
            "import sys, time\nfrom pathlib import Path\n"
            f"sys.path.insert(0, {str(REPO / 'src')!r})\n"
            "from harness import providers\noriginal = providers.prompt\n"
            f"gate = Path({str(gate)!r})\n"
            "def delayed(*args):\n"
            "    gate.with_suffix('.ready').touch()\n"
            "    until = time.monotonic() + 8\n"
            "    while not gate.exists() and time.monotonic() < until:\n        time.sleep(0.02)\n"
            "    return original(*args)\nproviders.prompt = delayed\n"
        )
        self.env["PYTHONPATH"] = str(hooks)
        self.limits(attempt_seconds=15)
        key = self.start("effect")
        self.wait(key, lambda s: bool(s["attempts"]) and gate.with_suffix(".ready").exists())
        self.call("run", "stop", key)
        gate.touch()
        state = self.wait(key, lambda s: s["participants"][0]["state"] == "interrupted")
        self.assertEqual(state["state"], "cancelled")
        self.assertTrue(all(a["started"] is None for a in state["attempts"]))
        self.assertFalse((self.project / "executed_after_stop").exists())

    def test_crash_guard_stops_execution_without_relaunch(self):
        self.limits(attempt_seconds=20)
        key = self.start("sleep")
        state = self.wait(
            key, lambda s: bool(s["attempts"]) and s["attempts"][0]["state"] == "running"
        )
        with sqlite3.connect(self.root / "state.sqlite") as db:
            pid = db.execute("SELECT supervisor_pid FROM runs WHERE id=?", (key,)).fetchone()[0]
        os.kill(pid, signal.SIGKILL)
        state = self.wait(key, lambda s: s["state"] == "interrupted")
        self.assertEqual(len(state["attempts"]), 1)
        self.call("run", "recover", key)
        self.assertEqual(len(self.call("run", "status", key)["attempts"]), 1)

    def test_crash_guard_stops_descendants_after_the_group_leader_has_exited(self):
        self.limits(attempt_seconds=20)
        key = self.start("orphan")
        self.wait(key, lambda s: (self.project / "child.pid").exists())
        child = int((self.project / "child.pid").read_text())
        with sqlite3.connect(self.root / "state.sqlite") as db:
            supervisor = db.execute(
                "SELECT supervisor_pid FROM runs WHERE id=?", (key,)
            ).fetchone()[0]
            leader = db.execute("SELECT pid FROM attempts WHERE run_id=?", (key,)).fetchone()[0]
        processes = subprocess.run(
            ["ps", "-axo", "pid=,ppid=,args="], capture_output=True, text=True
        ).stdout
        guard = next(
            int(fields[0])
            for line in processes.splitlines()
            if len(fields := line.split(None, 2)) == 3
            and fields[1] == str(supervisor)
            and " guard " in fields[2]
        )
        try:
            os.kill(guard, signal.SIGSTOP)
            os.kill(supervisor, signal.SIGSTOP)
            (self.project / "release-provider").touch()
            time.sleep(0.1)
            os.kill(supervisor, signal.SIGKILL)
            until = time.monotonic() + 3
            while time.monotonic() < until:
                state = subprocess.run(
                    ["ps", "-p", str(leader), "-o", "stat="], capture_output=True, text=True
                ).stdout.strip()
                if not state or state.startswith("Z"):
                    break
                time.sleep(0.02)
            os.kill(guard, signal.SIGCONT)
            state = self.wait(key, lambda s: s["state"] == "interrupted")
            self.assertEqual(state["attempts"][0]["state"], "interrupted")
            child_state = subprocess.run(
                ["ps", "-p", str(child), "-o", "stat="], capture_output=True, text=True
            ).stdout.strip()
            self.assertTrue(not child_state or child_state.startswith("Z"), child_state)
        finally:
            for pid in (guard, supervisor):
                try:
                    os.kill(pid, signal.SIGCONT)
                except ProcessLookupError:
                    pass


if __name__ == "__main__":
    unittest.main()
