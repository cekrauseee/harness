"""Launcher guarantees on synthetic host output: no network, no real CLI."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import support
from support import ROOT, WORK
import records
import run

# Fake host CLIs: they log their arguments and stdin, then print synthetic output by mode.
FAKE = r'''#!{python}
import json, os, sys, time
host, args = os.path.basename(sys.argv[0]), sys.argv[1:]
calls = os.environ["FAKE_LOG"]
with open(calls, "a") as log:
    log.write(json.dumps({{"host": host, "args": args, "stdin": sys.stdin.read()}}) + "\n")
count = sum(1 for _ in open(calls))
mode = os.environ.get("FAKE_MODE", "ok")
limited = mode == "fail" or mode == "limit" or mode == "limit-once" and count == 1
if mode == "slow":
    time.sleep(2)
if host == "codex":
    if "-o" in args:
        open(args[args.index("-o") + 1], "w").write("Delivered. Record written.\n")
    print(json.dumps({{"type": "thread.started", "thread_id": "thread-1"}}))
    print(json.dumps({{"type": "item.completed", "item": {{"type": "reasoning", "text": "SECRET-REASONING"}}}}))
    print("not json")
    if limited:
        message = "invalid request" if mode == "fail" else "429 Too Many Requests"
        print(json.dumps({{"type": "turn.failed", "error": {{"message": message}}}}))
        sys.exit(1)
    print(json.dumps({{"type": "item.completed", "item": {{"type": "agent_message", "text": "Delivered."}}}}))
    print(json.dumps({{"type": "turn.completed", "usage": {{"input_tokens": 1000, "cached_input_tokens": 600,
                                                          "output_tokens": 50, "reasoning_output_tokens": 20}}}}))
else:
    session = args[args.index("--session-id" if "--session-id" in args else "--resume") + 1]
    usage = {{"input_tokens": 10, "cache_creation_input_tokens": 20, "cache_read_input_tokens": 300, "output_tokens": 5}}
    error = limited
    print(json.dumps({{"type": "result", "subtype": "success", "is_error": error, "session_id": session, "usage": usage,
                      "result": "API Error: 429 rate_limit_error" if error else "Delivered."}}))
    sys.exit(1 if error else 0)
'''


class LauncherTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='harness-run-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.home = self.root / 'state'
        self.project, self.base, self.head = support.project_with_change(self.root)
        self.env = support.environment(self.home, self.project)
        self.front = self.env / 'work' / WORK / 'fronts' / 'sessions'
        bin_dir = self.root / 'bin'
        bin_dir.mkdir()
        for host in ('codex', 'claude'):
            (bin_dir / host).write_text(FAKE.format(python=sys.executable))
            (bin_dir / host).chmod(0o755)
        self.log = self.root / 'calls.jsonl'
        self.environ = dict(os.environ, PATH=f"{bin_dir}{os.pathsep}{os.environ['PATH']}", FAKE_LOG=str(self.log))
        self.prompt = self.root / 'prompt.md'
        self.prompt.write_text('Implement the sessions module.\n')

    def cli(self, *args, mode='ok'):
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'src/run.py'), '--home', str(self.home), args[0],
                                 '--environment', str(self.env), '--work', WORK, '--front', 'sessions', *args[1:]],
                                capture_output=True, text=True, timeout=60, env=dict(self.environ, FAKE_MODE=mode))
        return result.returncode, json.loads(result.stdout)

    def start(self, run_id, host='codex', mode='ok', *extra):
        return self.cli('start', '--run', run_id, '--host', host, '--cwd', str(self.project), '--prompt', str(self.prompt),
                        '--owned', 'ap-session-race', '--retry-delay', '0', *extra, mode=mode)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def kinds(self):
        return [e['kind'] for e in records.read_events(self.front)[0]]

    def test_codex_run_is_parsed_drafted_and_kept_as_raw_evidence(self):
        self.assertEqual(self.start('impl-1')[0], 0)
        code, result = self.cli('wait', '--run', 'impl-1')
        self.assertEqual((code, result['status'], result['session']), (0, 'delivered', 'thread-1'))
        self.assertEqual(result['tokens'], {'input': 1000, 'cached': 600, 'output': 50})
        self.assertEqual(result['message'], 'Delivered. Record written.\n')
        call = self.calls()[0]
        self.assertEqual(call['args'][:4], ['exec', '--json', '-C', str(self.project)])
        self.assertEqual((call['args'][-1], call['stdin']), ('Implement the sessions module.\n', ''))
        self.assertNotIn('-m', call['args'])
        self.assertEqual(self.kinds(), ['spawn', 'delivered'])
        draft = json.loads((self.front / 'runs' / 'impl-1.draft.json').read_text())
        self.assertEqual((draft['base'], draft['head'], draft['owned']), (self.head, self.head, ['ap-session-race']))
        self.assertEqual(draft['changed'], [])
        raw = {p.name for p in (self.front / 'runs' / 'raw').iterdir()}
        self.assertTrue({'impl-1.1.jsonl', 'impl-1.1.stderr', 'impl-1.state.json'} <= raw)
        for path in (self.front / 'events.jsonl', self.front / 'runs' / 'raw' / 'impl-1.state.json'):
            self.assertNotIn('SECRET-REASONING', path.read_text())
        self.assertNotIn('SECRET-REASONING', json.dumps(result))
        self.assertEqual(self.start('impl-1')[1]['error']['code'], 'run_exists')

    def test_rate_limit_retries_only_when_requested_and_resumes_the_session(self):
        self.start('impl-1', 'codex', 'limit')
        code, result = self.cli('wait', '--run', 'impl-1')
        self.assertEqual((code, result['status'], result['attempts']), (1, 'rate_limited', 1))
        self.assertEqual(self.kinds(), ['spawn', 'rate_limited'])
        self.log.unlink()  # the fake fails only the first call it logs
        self.start('impl-2', 'codex', 'limit-once', '--retry', '1')
        code, result = self.cli('wait', '--run', 'impl-2')
        self.assertEqual((code, result['status'], result['attempts']), (0, 'delivered', 2))
        retry = self.calls()[-1]['args']
        self.assertEqual(retry[:3], ['exec', 'resume', '--json'])
        self.assertEqual(retry[-2:], ['thread-1', run.CONTINUE])
        self.assertEqual(self.kinds()[2:], ['spawn', 'rate_limited', 'resume', 'delivered'])
        self.start('impl-3', 'codex', 'fail', '--retry', '2')
        self.assertEqual(self.cli('wait', '--run', 'impl-3')[1]['attempts'], 1)

    def test_claude_session_is_assigned_and_resumed_as_a_new_iteration(self):
        self.start('ui-1', 'claude', 'ok', '--model', 'example-model', '--', '--permission-mode', 'plan')
        result = self.cli('wait', '--run', 'ui-1')[1]
        self.assertEqual(result['tokens'], {'input': 330, 'cached': 300, 'output': 5})
        first = self.calls()[0]['args']
        self.assertEqual(first[:2], ['-p', '--session-id'])
        self.assertEqual(first[2], result['session'])
        self.assertEqual(first[-5:], ['--model', 'example-model', '--permission-mode', 'plan',
                                      'Implement the sessions module.\n'])
        feedback = self.root / 'feedback.md'
        feedback.write_text('Address the review findings.\n')
        self.cli('resume', '--run', 'ui-2', '--from', 'ui-1', '--prompt', str(feedback))
        result = self.cli('wait', '--run', 'ui-2')[1]
        self.assertEqual(result['status'], 'delivered')
        self.assertEqual(self.calls()[1]['args'][:3], ['-p', '--resume', first[2]])
        events = records.read_events(self.front)[0]
        self.assertEqual([(e['kind'], e['run'], e['iteration']) for e in events],
                         [('spawn', 'ui-1', 1), ('delivered', 'ui-1', 1), ('resume', 'ui-2', 2), ('delivered', 'ui-2', 2)])

    def test_wait_timeout_reports_a_running_run(self):
        self.start('impl-1', 'codex', 'slow')
        code, result = self.cli('wait', '--run', 'impl-1', '--timeout', '0.2')
        self.assertEqual((code, result['status'], result['timeout']), (2, 'running', True))
        self.assertEqual(self.cli('wait', '--run', 'impl-1')[1]['status'], 'delivered')

    def test_parsers_and_classification(self):
        parsed = run.parse_codex(['{"type": "thread.started", "thread_id": "t"}', '[1]', 'garbage',
                                  '{"type": "turn.completed", "usage": {"input_tokens": 3}}',
                                  '{"type": "turn.completed", "usage": {"input_tokens": 4, "output_tokens": 1}}'])
        self.assertEqual((parsed['session'], parsed['tokens'], parsed['error']), ('t', {'input': 7, 'output': 1}, None))
        failed = run.parse_claude('{"type": "result", "subtype": "error_during_execution", "is_error": true}')
        self.assertEqual(failed['error'], 'error_during_execution')
        self.assertEqual(run.parse_claude('')['error'], 'no result')
        self.assertEqual(run.classify(1, {'error': 'stream disconnected before completion'}, ''), 'transient')
        self.assertEqual(run.classify(1, {'error': None}, 'HTTP 429'), 'rate_limited')
        self.assertEqual(run.classify(0, {'error': None}, ''), 'delivered')
        self.assertEqual(run.classify(1, {'error': 'invalid request'}, ''), 'failed')


if __name__ == '__main__':
    unittest.main()
