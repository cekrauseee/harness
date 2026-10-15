"""Mechanical guarantees of events, run records and symbol anchors."""
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import support
from support import ROOT, WORK, sessions_record
import records


def append(environment, front, count):
    for index in range(count):
        records.append_event(Path(environment), WORK, front, {'kind': 'returned', 'run': f'impl-{index + 1}',
                                                              'note': 'x' * 100})
    return count


class RecordsTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='harness-records-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.home = self.root / 'state'
        self.project, self.base, self.head = support.project_with_change(self.root)
        self.env = support.environment(self.home, self.project)
        self.front = self.env / 'work' / WORK / 'fronts' / 'sessions'

    def error(self, code, function, *args):
        with self.assertRaises(records.Error) as caught:
            function(*args)
        self.assertEqual(caught.exception.code, code)
        return caught.exception

    def complete(self, record):
        return records.complete(record, self.project)

    def cli(self, *args, stdin=None):
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'src/records.py'), '--home', str(self.home), *args],
                                capture_output=True, text=True, input=stdin, timeout=30)
        return result.returncode, json.loads(result.stdout)

    def test_concurrent_appends_keep_every_line_whole(self):
        with ProcessPoolExecutor(max_workers=4) as pool:
            counts = list(pool.map(append, [str(self.env)] * 4, ['sessions'] * 4, [40] * 4))
        events, invalid = records.read_events(self.front)
        self.assertEqual((len(events), invalid), (sum(counts), 0))
        lines = (self.front / 'events.jsonl').read_bytes().split(b'\n')
        self.assertEqual(lines[-1], b'')
        self.assertTrue(all(json.loads(line)['format'] == 'harness-event-v1' for line in lines[:-1]))

    def test_torn_line_is_isolated_and_invalid_events_are_not_written(self):
        records.append_event(self.env, WORK, 'sessions', {'kind': 'spawn', 'run': 'impl-1'})
        with (self.front / 'events.jsonl').open('ab') as stream:
            stream.write(b'{"format": "harness-ev')
        records.append_event(self.env, WORK, 'sessions', {'kind': 'delivered', 'run': 'impl-1',
                                                          'tokens': {'input': 10, 'cached': 4, 'output': 2}})
        before = (self.front / 'events.jsonl').read_bytes()
        for data in ({'kind': 'started'}, {'kind': 'spawn', 'note': 'x' * 141}, {'kind': 'spawn', 'front': 'other'},
                     {'kind': 'spawn', 'tokens': {'input': -1}}, ['kind']):
            self.error('invalid_event', records.append_event, self.env, WORK, 'sessions', data) if isinstance(data, dict) \
                else self.error('invalid_input', records.append_event, self.env, WORK, 'sessions', data)
        self.assertEqual((self.front / 'events.jsonl').read_bytes(), before)
        events, invalid = records.read_events(self.front)
        self.assertEqual(([e['kind'] for e in events], invalid), (['spawn', 'delivered'], 1))

    def test_records_are_written_once_and_never_replaced(self):
        record = self.complete(sessions_record(self.base, self.head))
        target = self.front / 'runs' / 'impl-1.record.json'
        self.assertTrue(records.write_record(self.env, record, self.project)['changed'])
        written = target.read_bytes()
        self.assertFalse(records.write_record(self.env, record, self.project)['changed'])
        self.error('record_exists', records.write_record, self.env, dict(record, summary='Another summary.'), self.project)
        self.assertEqual(target.read_bytes(), written)
        self.assertEqual([p.name for p in target.parent.iterdir()], ['impl-1.record.json'])

    def test_paths_stay_inside_existing_work_and_reject_symlinks(self):
        record = self.complete(sessions_record(self.base, self.head))
        for key, value in (('run', '../../escape'), ('front', 'a/b'), ('work', '..')):
            self.assertIn(self.error_code(records.write_record, self.env, dict(record, **{key: value}), self.project),
                          {'invalid_record', 'invalid_input'})
        self.error('work_missing', records.write_record, self.env, dict(record, work='other'), self.project)
        self.error('invalid_input', records.append_event, self.env, '../x', 'sessions', {'kind': 'spawn'})
        outside = self.root / 'outside'
        outside.mkdir()
        (self.env / 'work' / WORK / 'fronts').mkdir()
        (self.env / 'work' / WORK / 'fronts' / 'linked').symlink_to(outside, target_is_directory=True)
        self.error('unsafe_path', records.append_event, self.env, WORK, 'linked', {'kind': 'spawn'})
        self.error('unsafe_path', records.write_record, self.env, dict(record, front='linked'), self.project)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse(list(self.root.glob('**/escape*')))

    def error_code(self, function, *args):
        with self.assertRaises(records.Error) as caught:
            function(*args)
        return caught.exception.code

    def test_valid_record_passes_and_complete_fills_git_facts(self):
        draft = sessions_record(self.base, 'feat/sessions')
        del draft['head']
        record = self.complete(draft)
        self.assertEqual(record['head'], self.head)
        self.assertEqual(set(record['changed']), {'src/store.py', 'src/api.py', 'tests/test_store.py',
                                                  'web/page.ts', 'web/client.ts', 'db/sessions.sql'})
        self.assertEqual(records.record_errors(self.env, record, self.project), [])
        stale = dict(record, head=self.base, changed=[])
        self.assertEqual(records.complete(stale, self.project, head=self.head)['changed'], record['changed'])

    def test_schema_errors_point_at_their_location(self):
        record = self.complete(sessions_record(self.base, self.head, kind='deploy', extra=1))
        record['attention'][0]['status'] = 'done'
        del record['summary']
        locations = {e['at'] for e in records.record_errors(self.env, record, self.project)}
        self.assertEqual(locations, {'$', '$.kind', '$.extra', '$.attention[0].status'})

    def test_each_git_and_plan_check_reports_its_location(self):
        record = self.complete(sessions_record(self.base, self.head))
        record['changed'] = record['changed'][1:]
        record['files']['README.md'] = 'Unchanged.'
        record['cards'][1]['files'].append('src/unchanged.py')
        record['notes'].append({'path': 'src/api.py', 'symbol': 'Session.missing', 'text': 'Missing symbol.'})
        record['attention'][0]['evidence'].append({'path': 'src/gone.py', 'note': 'Missing file.'})
        record['attention'][0]['tests'].append({'path': 'tests/test_store.py', 'title': 'test_not_written'})
        record['attention'].append({'id': 'ap-undeclared', 'status': 'open'})
        record['owned'].append('fl-sign-in')
        record['cards'].append(dict(record['cards'][0]))
        locations = [e['at'] for e in records.record_errors(self.env, record, self.project)]
        self.assertEqual(sorted(locations), sorted([
            '$.changed', '$.cards[1].files[1]', '$.files["README.md"]', '$.notes[1].symbol',
            '$.attention[0].evidence[1].path', '$.attention[0].tests[1].title', '$.attention', '$.owned', '$.cards']))

    def test_symbols_resolve_to_declaration_ranges(self):
        cases = [
            ('a.py', 'class A:\n    def run(self):\n        pass\n\n    def stop(self):\n        pass\n\nx = 1\n',
             {'A': (1, 6), 'A.run': (2, 3), 'A.stop': (5, 6), 'run': None, 'x': None}),
            ('a.ts', 'export class Store {\n  load() {\n    return 1;\n  }\n}\nexport const f = () => {\n  return 2;\n};\n',
             {'Store': (1, 5), 'Store.load': (2, 4), 'f': (6, 8), 'load': None}),
            ('a.rs', 'struct Foo;\n\nimpl Foo {\n    pub fn bar(&self) {}\n}\n', {'Foo.bar': (4, 4)}),
            ('a.md', '# A\n\n## B\n\ntext\n\n## C\n', {'B': (3, 5), 'A': (1, 7)}),
        ]
        for path, text, expected in cases:
            for symbol, span in expected.items():
                with self.subTest(path=path, symbol=symbol):
                    self.assertEqual(records.resolve_symbol(text, path, symbol), span)

    def test_cli_validates_writes_and_reports_errors_as_json(self):
        draft = self.root / 'draft.json'
        record = sessions_record(self.base, self.head)
        draft.write_text(json.dumps(record))
        args = ['--environment', str(self.env), '--input', str(draft), '--repo', str(self.project)]
        self.assertEqual(self.cli('record', 'validate', *args)[0], 0)
        self.assertEqual(self.cli('record', 'write', *args)[1]['changed'], True)
        draft.write_text(json.dumps(dict(record, run='impl-2', owned=['ap-unknown'])))
        code, output = self.cli('record', 'validate', *args)
        self.assertEqual((code, output['valid']), (1, False))
        code, output = self.cli('record', 'write', *args)
        self.assertEqual((code, output['error']['code']), (1, 'invalid_record'))
        self.assertFalse((self.front / 'runs' / 'impl-2.record.json').exists())
        code, output = self.cli('event', '--environment', str(self.env), '--work', WORK, '--front', 'sessions',
                                '--data', '{"kind": "accepted", "run": "impl-1"}')
        self.assertEqual((code, output['event']['kind']), (0, 'accepted'))
        code, output = self.cli('symbol', '--repo', str(self.project), '--path', 'src/store.py', '--symbol', 'Session.issue')
        self.assertEqual((code, output['start']), (0, 6))


if __name__ == '__main__':
    unittest.main()
