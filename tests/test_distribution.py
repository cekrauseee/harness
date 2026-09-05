from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ('harness-init', 'harness-recall', 'harness-task', 'harness-remember', 'harness-maintain')


class DistributionTests(unittest.TestCase):
    def test_generated_outputs_are_current(self):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/build_dist.py'), '--check'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_every_skill_runs_independently_without_source_checkout(self):
        for name in SKILLS:
            with self.subTest(skill=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                installed = root / 'installed' / name
                shutil.copytree(ROOT / 'skills' / name, installed, ignore=shutil.ignore_patterns('__pycache__'))
                env = dict(os.environ, HARNESS_HOME=str(root / 'state'), PYTHONPATH='')
                project = root / 'project'
                project.mkdir()
                script = installed / 'scripts/harness.py'
                def run(op, data=None):
                    result = subprocess.run([sys.executable, str(script), op, '--project', str(project), '--data', json.dumps(data or {})], cwd=root, env=env, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    return json.loads(result.stdout)
                identity = run('init')
                start = run('task.start', {'objective':'Check copied installation','resources':['draft.md'],'request_id':'start'})
                run('task.checkpoint', {'session_id':start['session']['id'],'summary':'Copied runtime executed.','evidence':['isolated installation'],'next_action':'','status':'delivered','request_id':'finish'})
                run('remember', {'title':'Sources','summary':'Source provenance','content':'Use the referenced source.','kind':'hypothesis','sources':['draft.md'],'scope':'project','aliases':['fontes'],'request_id':'memory'})
                self.assertEqual(len(run('recall', {'query':'fontes'})['entries']), 1)
                self.assertEqual(run('consolidate')['claims'], [])
                self.assertEqual(list(project.iterdir()), [])
                self.assertEqual(run('resolve')['project_id'], identity['project_id'])

    def test_cli_errors_are_structured_and_input_file_works(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            script=ROOT/'skills/harness-task/scripts/harness.py'
            env=dict(os.environ,HARNESS_HOME=str(root/'state'))
            for args in (['task.start','--data','[]'],['recall','--data','{'],['init','--missing-option']):
                result=subprocess.run([sys.executable,str(script),*args],cwd=root,env=env,capture_output=True,text=True)
                self.assertEqual(result.returncode,2)
                self.assertFalse(json.loads(result.stdout)['success'])
            source=root/'input.json';source.write_text(json.dumps({'operation':'task.start'}))
            result=subprocess.run([sys.executable,str(script),'guide','--input',str(source)],cwd=root,env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('request_id',json.loads(result.stdout)['guide']['required'])

    def test_removed_operations_are_not_dispatched_or_documented(self):
        script = ROOT / 'skills/harness-maintain/scripts/harness.py'
        self.assertFalse((ROOT / 'src/harness_runtime/migration.py').exists())
        self.assertFalse((ROOT / 'src/harness_runtime/legacy/fingerprints.json').exists())
        self.assertFalse((ROOT / 'skills/harness-maintain/references/migration.md').exists())
        for name in SKILLS:
            bundled = ROOT / 'skills' / name / 'scripts/harness_runtime'
            self.assertFalse((bundled / 'migration.py').exists())
            self.assertFalse((bundled / 'legacy/fingerprints.json').exists())
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / 'project'
            project.mkdir()
            env = dict(os.environ, HARNESS_HOME=str(root / 'state'))
            guide = subprocess.run([sys.executable, str(script), 'guide'], cwd=root, env=env,
                                   capture_output=True, text=True)
            self.assertEqual(guide.returncode, 0, guide.stdout + guide.stderr)
            operations = json.loads(guide.stdout)['operations']
            self.assertFalse(any(name.startswith(('migrate.', 'legacy.')) for name in operations))
            for operation in ('migrate.preview', 'migrate.apply', 'migrate.restore', 'legacy.scan', 'legacy.clean'):
                with self.subTest(operation=operation):
                    result = subprocess.run([sys.executable, str(script), operation, '--project', str(project)],
                                            cwd=root, env=env, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                    self.assertEqual(json.loads(result.stdout)['error']['code'], 'unknown_operation')


if __name__ == '__main__':
    unittest.main()
