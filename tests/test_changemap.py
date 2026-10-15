"""Change map consolidation on a synthetic repository with accepted and unaccepted records."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import support
from support import ROOT, WORK, sessions_record
import changemap
import records

SUPPLEMENT = {
    'format': 'harness-map-supplement-v1',
    'title': 'Checkout sessions',
    'layers': [{'id': 'ui', 'title': 'Interface'}, {'id': 'api', 'title': 'API'},
               {'id': 'domain', 'title': 'Domain'}, {'id': 'storage', 'title': 'Storage'}],
    'cards': [{'id': 'storage', 'layer': 'storage', 'title': 'Sessions table', 'summary': 'Stores generations.',
               'files': ['db/sessions.sql']}],
    'edges': [{'from': 'sessions', 'to': 'storage', 'label': 'reads the generation'}],
    'notes': [{'path': 'web/page.ts', 'symbol': 'SignInPage', 'replaces': 'SignIn', 'text': 'Renders the page.'}],
    'attention': [{'id': 'ap-schema-drift', 'status': 'handled', 'handling': 'One table definition.',
                   'evidence': [{'path': 'db/sessions.sql', 'symbol': 'sessions', 'note': 'The only definition.'}]}],
    'flows': [{'id': 'fl-sign-in', 'title': 'Sign in', 'steps': [
        {'actor': 'customer', 'do': 'Open the sign-in page.', 'expect': 'The cart appears.', 'url': '/sign-in',
         'cards': ['web', 'api'], 'code': [{'path': 'src/api.py', 'symbol': 'sign_in'}],
         'test': {'path': 'tests/test_store.py', 'title': 'test_issue_rejects_a_stale_generation'}}]}],
}


class ChangeMapTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='harness-map-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.home = self.root / 'state'
        self.project, self.base, self.head = support.project_with_change(self.root)
        self.env = support.environment(self.home, self.project)
        self.work = self.env / 'work' / WORK
        record = records.complete(sessions_record(self.base, self.head), self.project)
        records.write_record(self.env, record, self.project)
        records.append_event(self.env, WORK, 'sessions', {'kind': 'delivered', 'run': 'impl-1',
                                                          'tokens': {'input': 100, 'cached': 40, 'output': 10}})
        records.append_event(self.env, WORK, 'sessions', {'kind': 'accepted', 'run': 'impl-1'})
        # A record whose anchor drifted after a rebase, written directly as an older delivery would be.
        web = dict(record, front='web', run='web-1', owned=[], attention=[], tests=[],
                   cards=[{'id': 'web', 'layer': 'ui', 'title': 'Sign-in page', 'summary': 'Page and client.',
                           'files': ['web/page.ts', 'web/client.ts']}],
                   files={'web/page.ts': 'The page.', 'web/client.ts': 'The client.'},
                   notes=[{'path': 'web/page.ts', 'symbol': 'SignIn', 'text': 'Renders the page.'}])
        runs = self.work / 'fronts' / 'web' / 'runs'
        runs.mkdir(parents=True)
        for run in ('web-1', 'web-0'):
            (runs / f'{run}.record.json').write_text(json.dumps(dict(web, run=run)))
        records.append_event(self.env, WORK, 'web', {'kind': 'accepted', 'run': 'web-1'})

    def cli(self, *args):
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'src/changemap.py'), '--home', str(self.home), *args,
                                 '--environment', str(self.env), '--work', WORK], capture_output=True, text=True, timeout=60,
                                env={k: v for k, v in os.environ.items() if k != 'HARNESS_VIEWER'})
        return result.returncode, json.loads(result.stdout)

    def build(self):
        return self.cli('build', '--repo', str(self.project), '--base', 'main', '--head', 'feat/sessions')

    def test_gap_list_is_exact_and_filling_it_leaves_no_errors(self):
        code, result = self.build()
        self.assertEqual(code, 1)
        self.assertEqual([{k: v for k, v in g.items() if k != 'at'} for g in result['gaps']], [
            {'kind': 'unassigned_file', 'level': 'error', 'path': 'db/sessions.sql'},
            {'kind': 'unresolved_anchor', 'level': 'error', 'path': 'web/page.ts', 'symbol': 'SignIn'},
            {'kind': 'unreported_id', 'level': 'error', 'id': 'ap-schema-drift'},
            {'kind': 'unreported_id', 'level': 'error', 'id': 'fl-sign-in'},
        ])
        self.assertEqual(result['unaccepted'], ['fronts/web/runs/web-0.record.json'])
        view = json.loads(Path(result['map']).read_text())
        self.assertEqual(records.schema_errors(view, 'map.v1.json'), [])
        self.assertEqual([r['run'] for r in view['runs']], ['impl-1', 'web-1'])
        self.assertEqual(view['runs'][0]['tokens'], {'input': 100, 'cached': 40, 'output': 10})
        self.assertEqual(view['edges'], [{'from': 'api', 'to': 'sessions', 'kind': 'import'}])
        hunk = view['code']['src/store.py']['hunks'][0]
        self.assertEqual(hunk['notes'], [0])
        self.assertTrue(view['commits'][hunk['commits'][0]]['subject'].startswith('feat(sessions)'))
        self.assertIn('lines', view['code']['web/page.ts'])

        supplement = dict(SUPPLEMENT)
        del supplement['edges']
        (self.work / 'map' / 'supplement.json').write_text(json.dumps(supplement))
        code, result = self.build()
        self.assertEqual((code, result['errors']), (0, 0))
        self.assertEqual(result['gaps'], [{'kind': 'isolated_card', 'level': 'warning', 'card': 'storage'}])

        (self.work / 'map' / 'supplement.json').write_text(json.dumps(SUPPLEMENT))
        code, result = self.build()
        self.assertEqual((code, result['errors'], result['warnings'], result['changed']), (0, 0, 0, True))
        view = json.loads(Path(result['map']).read_text())
        self.assertEqual(records.schema_errors(view, 'map.v1.json'), [])
        self.assertEqual(view['title'], 'Checkout sessions')
        self.assertEqual([a['status'] for a in view['attention']], ['handled', 'handled'])
        self.assertEqual(view['flows'][0]['steps'][0]['test']['line'], 4)
        self.assertEqual(self.build()[1]['changed'], False)

    def test_invalid_supplement_and_unknown_references_are_reported(self):
        (self.work / 'map').mkdir()
        (self.work / 'map' / 'supplement.json').write_text(json.dumps({'format': 'harness-map-supplement-v1', 'cards': [{}]}))
        code, result = self.build()
        self.assertEqual((code, result['error']['code']), (1, 'invalid_supplement'))
        self.assertFalse((self.work / 'map' / 'map.json').exists())
        (self.work / 'map' / 'supplement.json').write_text(json.dumps(dict(
            SUPPLEMENT, edges=[{'from': 'storage', 'to': 'nowhere'}],
            attention=[{'id': 'ap-undeclared', 'status': 'open'}, *SUPPLEMENT['attention']])))
        kinds = {(g['kind'], g.get('id') or g.get('edge')) for g in self.build()[1]['gaps']}
        self.assertTrue({('invalid_reference', 'storage->nowhere'), ('invalid_reference', 'ap-undeclared')} <= kinds)

    def test_view_without_a_viewer_prints_the_command(self):
        self.build()
        code, result = self.cli('view')
        self.assertEqual((code, result['started']), (0, False))
        self.assertIn(f"HARNESS_MAP_DIR={self.work / 'map'}", result['command'])


if __name__ == '__main__':
    unittest.main()
