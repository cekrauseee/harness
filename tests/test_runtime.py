"""Mechanical guarantees of the current-only Harness file helper."""
from concurrent.futures import ProcessPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import harness


def worker(home, operation, args):
    try:
        return harness.execute(operation, args, home)
    except harness.Error as exc:
        return {'error': exc.code}


class RuntimeTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='harness-test-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.home = self.root / 'state'
        self.project = self.root / 'project'
        self.project.mkdir()

    def call(self, operation, **args):
        if 'project' not in args and (operation == 'init' or 'environment' not in args):
            args['project'] = str(self.project)
        return harness.execute(operation, args, self.home)

    def git(self, *args, cwd=None):
        result = subprocess.run(['git', '-C', str(cwd or self.project), *args],
                                capture_output=True, text=True, timeout=20,
                                env={k: v for k, v in os.environ.items() if not k.startswith('GIT_')})
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def repository(self):
        self.git('init', '-b', 'main')
        self.git('-c', 'user.name=Harness Test', '-c', 'user.email=harness@example.invalid',
                 '-c', 'commit.gpgsign=false', 'commit', '--allow-empty', '-m', 'chore: initialize')

    def env(self):
        return Path(self.call('init')['environment'])

    def write(self, name, content, expect='missing'):
        source = self.root / 'input.md'
        source.write_text(content)
        return self.call('write', file=name, input=str(source), expect=expect)

    def error(self, code, function, *args, **kwargs):
        with self.assertRaises(harness.Error) as caught:
            function(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)
        return caught.exception

    def test_uninitialized_resolve_has_no_side_effect(self):
        self.error('not_initialized', self.call, 'resolve')
        self.assertFalse(self.home.exists())
        self.assertEqual(list(self.project.iterdir()), [])

    def test_init_is_external_minimal_and_idempotent(self):
        result = self.call('init')
        folder = Path(result['environment'])
        before = {p.name: p.stat().st_mtime_ns for p in folder.iterdir()}
        self.assertTrue(result['changed'])
        self.assertEqual(set(before), {'README.md', 'environment.json'})
        self.assertFalse(self.call('init')['changed'])
        self.assertEqual(before, {p.name: p.stat().st_mtime_ns for p in folder.iterdir()})
        self.assertEqual(list(self.project.iterdir()), [])
        self.assertEqual(self.call('resolve')['worktrees'], str(folder / 'worktrees'))

    def test_directory_descendants_share_binding(self):
        environment = self.env()
        child = self.project / 'notes' / 'topic'
        child.mkdir(parents=True)
        self.assertEqual(self.call('resolve', project=str(child))['environment'], str(environment))
        self.assertFalse(self.call('init', project=str(child))['changed'])

    def test_repository_subdirectories_and_worktrees_share_identity(self):
        self.repository()
        environment = self.env()
        child = self.project / 'apps' / 'one'
        child.mkdir(parents=True)
        checkout = environment / 'worktrees' / 'feature'
        checkout.parent.mkdir()
        self.git('worktree', 'add', '-b', 'feat/example', str(checkout))
        for selector in (child, checkout):
            result = self.call('resolve', project=str(selector))
            self.assertEqual(result['environment'], str(environment))
            self.assertEqual(result['project']['root'], str(self.project))
            self.assertFalse(self.call('init', project=str(selector))['changed'])
        self.assertEqual(self.call('resolve', project=str(checkout))['workspace'], str(checkout))

    def test_init_from_linked_checkout_uses_primary_root(self):
        self.repository()
        checkout = self.root / 'existing-linked'
        self.git('worktree', 'add', '-b', 'feat/linked', str(checkout))
        created = self.call('init', project=str(checkout))
        self.assertEqual(created['project']['root'], str(self.project))
        self.assertEqual(self.call('resolve')['environment'], created['environment'])

    def test_projects_with_same_name_remain_distinct(self):
        first = self.env()
        other = self.root / 'other' / 'project'
        other.mkdir(parents=True)
        second = Path(self.call('init', project=str(other))['environment'])
        self.assertNotEqual(first, second)
        self.assertTrue(second.name.startswith('project-'))
        self.error('identity_changed', self.call, 'init', project=str(self.root / 'other'), environment=str(first))

    def test_git_clone_is_not_bound_by_remote_or_contents(self):
        self.repository()
        first = self.env()
        clone = self.root / 'clone'
        self.git('clone', str(self.project), str(clone))
        self.error('not_initialized', self.call, 'resolve', project=str(clone))
        self.assertNotEqual(str(first), self.call('init', project=str(clone))['environment'])

    def test_nested_git_repository_is_not_parent_directory_project(self):
        self.env()
        nested = self.project / 'nested'
        nested.mkdir()
        self.git('init', '-b', 'main', cwd=nested)
        self.error('not_initialized', self.call, 'resolve', project=str(nested))

    def test_git_environment_overrides_cannot_change_project_identity(self):
        self.repository()
        first = self.env()
        with patch.dict(os.environ, {'GIT_DIR': str(self.root / 'wrong.git'), 'GIT_WORK_TREE': '/'}):
            self.assertEqual(self.call('resolve')['environment'], str(first))

    def test_explicit_environment_is_exclusive_and_not_moved(self):
        folder = self.root / 'chosen-environment'
        self.assertEqual(self.call('init', environment=str(folder))['environment'], str(folder))
        self.assertFalse(self.call('init', environment=str(folder))['changed'])
        self.error('already_bound', self.call, 'init', environment=str(self.root / 'elsewhere'))
        other = self.root / 'other-project'
        other.mkdir()
        self.error('identity_changed', self.call, 'init', project=str(other), environment=str(folder))
        self.assertTrue((folder / 'environment.json').exists())

    def test_refuses_storage_in_a_repository(self):
        self.error('unsafe_path', self.call, 'init', environment=str(self.project / 'state'))
        self.assertFalse(self.home.exists())
        other = self.root / 'other-repo'
        other.mkdir()
        self.git('init', '-b', 'main', cwd=other)
        self.error('unsafe_path', self.call, 'init', environment=str(other / 'state'))
        self.assertFalse(self.home.exists())

    def test_refuses_home_containing_or_inside_primary_project(self):
        for home in (self.root, self.project / '.harness'):
            self.error('unsafe_path', harness.execute, 'init', {'project': str(self.project)}, home)
        self.assertFalse((self.project / '.harness').exists())

    def test_explicit_root_aliases_are_canonicalized(self):
        alias = self.root / 'alias'
        alias.symlink_to(self.root, target_is_directory=True)
        created = harness.execute('init', {'project': str(self.project),
            'environment': str(alias / 'environment')}, alias / 'state')
        self.assertEqual(created['environment'], str(self.root / 'environment'))
        result = harness.execute('resolve', {'project': str(self.project)}, alias / 'state')
        self.assertEqual(result['environment'], created['environment'])

    def test_binding_storage_and_nested_environments_are_rejected(self):
        folder = self.env()
        other = self.root / 'other'
        other.mkdir()
        self.error('unsafe_path', self.call, 'init', project=str(other),
                   environment=str(folder / 'nested'))
        self.error('unsafe_path', self.call, 'init', project=str(other),
                   environment=str(self.home / 'bindings' / 'nested'))
        self.git('init', '-b', 'main', cwd=other)
        self.error('unsafe_path', harness.execute, 'init',
                   {'project': str(self.project), 'environment': str(self.root / 'external')},
                   other / 'state')

    def test_read_only_does_not_create_lock_or_document(self):
        folder = self.env()
        before = sorted(p.name for p in folder.iterdir())
        value = self.call('read', file='knowledge/absent.md')
        self.assertEqual(value, {'file': str(folder / 'knowledge/absent.md'), 'sha256': 'missing', 'content': None})
        self.assertEqual(sorted(p.name for p in folder.iterdir()), before)

    def test_atomic_cas_write_and_idempotent_retry(self):
        folder = self.env()
        first = self.write('knowledge/one.md', '# One\n')
        mtime = (folder / 'knowledge/one.md').stat().st_mtime_ns
        self.assertFalse(self.write('knowledge/one.md', '# One\n')['changed'])
        self.assertEqual(mtime, (folder / 'knowledge/one.md').stat().st_mtime_ns)
        self.error('document_conflict', self.write, 'knowledge/one.md', '# Stale\n')
        second = self.write('knowledge/one.md', '# Two\n', first['sha256'])
        self.assertNotEqual(first['sha256'], second['sha256'])
        self.assertEqual(self.call('read', file='knowledge/one.md')['content'], '# Two\n')

    def test_delete_requires_current_hash_and_retries_idempotently(self):
        self.env()
        first = self.write('knowledge/one.md', 'one')
        second = self.write('knowledge/one.md', 'two', first['sha256'])
        self.error('document_conflict', self.call, 'delete', file='knowledge/one.md', expect=first['sha256'])
        self.error('invalid_input', self.call, 'delete', file='knowledge/one.md', expect='missing')
        self.assertTrue(self.call('delete', file='knowledge/one.md', expect=second['sha256'])['changed'])
        self.assertFalse(self.call('delete', file='knowledge/one.md', expect=second['sha256'])['changed'])

    def test_document_path_boundaries_and_worktree_exclusion(self):
        self.env()
        for name in ('../escape.md', '/escape.md', 'knowledge/../escape.md', 'worktrees/code.md',
                     'environment.json', 'knowledge//x.md', 'work/.hidden/x.md', 'knowledge/link.txt',
                     'knowledge\\x.md', './README.md'):
            with self.subTest(name=name):
                self.error('unsafe_path', self.call, 'read', file=name)

    def test_symlink_files_and_directories_are_rejected(self):
        folder = self.env()
        outside = self.root / 'outside'
        outside.mkdir()
        (folder / 'knowledge').symlink_to(outside)
        self.error('unsafe_path', self.call, 'read', file='knowledge/one.md')
        (folder / 'knowledge').unlink()
        (folder / 'knowledge').mkdir()
        (folder / 'knowledge/one.md').symlink_to(outside / 'missing.md')
        self.error('unsafe_path', self.write, 'knowledge/one.md', 'no')
        (folder / '.harness.lock').unlink(missing_ok=True)
        (folder / '.harness.lock').symlink_to(outside / 'lock')
        self.error('unsafe_path', self.write, 'knowledge/two.md', 'no')
        self.assertEqual(list(outside.iterdir()), [])

    def test_current_format_and_duplicate_keys_required(self):
        folder = self.env()
        path = folder / 'environment.json'
        path.write_text('{"format": 1, "roots": [], "contributions": {}}')
        self.error('invalid_state', self.call, 'resolve')
        path.write_text('{"format":"harness-project-v1", "format":"harness-project-v1"}')
        self.error('invalid_state', self.call, 'resolve')

    def test_unrelated_legacy_data_is_not_read_or_changed(self):
        legacy = self.home / 'environments' / 'legacy'
        legacy.mkdir(parents=True)
        (legacy / 'environment.json').write_text('invalid old state')
        self.env()
        self.assertEqual((legacy / 'environment.json').read_text(), 'invalid old state')
        self.call('resolve')

    def test_concurrent_initialization_publishes_one_environment(self):
        args = {'project': str(self.project)}
        with ProcessPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(worker, str(self.home), 'init', args) for _ in range(8)]
            results = [f.result() for f in futures]
        self.assertEqual(len({r['environment'] for r in results}), 1)
        self.assertEqual(sum(r['changed'] for r in results), 1)

    def test_concurrent_writers_do_not_lose_an_update(self):
        self.env()
        inputs = []
        for i in range(4):
            path = self.root / f'input-{i}.md'
            path.write_text(str(i))
            inputs.append(path)
        with ProcessPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(worker, str(self.home), 'write', {
                'project': str(self.project), 'file': 'knowledge/shared.md',
                'expect': 'missing', 'input': str(path)}) for path in inputs]
            results = [f.result() for f in futures]
        self.assertEqual(sum(r.get('changed', False) for r in results), 1)
        self.assertEqual(sum(r.get('error') == 'document_conflict' for r in results), 3)
        self.assertIn(self.call('read', file='knowledge/shared.md')['content'], {'0','1','2','3'})

    def test_pre_replace_failure_keeps_previous_bytes(self):
        folder = self.env()
        first = self.write('knowledge/one.md', 'old')
        with patch.object(harness.os, 'replace', side_effect=OSError('simulated')):
            self.error('write_failed', self.write, 'knowledge/one.md', 'new', first['sha256'])
        self.assertEqual((folder / 'knowledge/one.md').read_text(), 'old')
        self.assertEqual([p.name for p in (folder / 'knowledge').iterdir()], ['one.md'])

    def test_post_replace_uncertainty_is_reported(self):
        folder = self.env()
        first = self.write('knowledge/one.md', 'old')
        with patch.object(harness, 'sync_directory', side_effect=OSError('simulated')):
            self.error('write_uncertain', self.write, 'knowledge/one.md', 'new', first['sha256'])
        self.assertEqual((folder / 'knowledge/one.md').read_text(), 'new')

    def test_close_only_removes_selected_work_and_no_receipt(self):
        folder = self.env()
        self.write('work/one/README.md', 'complete')
        self.write('work/other/README.md', 'keep')
        self.write('knowledge/keep.md', 'keep')
        checkout = folder / 'worktrees/one'
        checkout.mkdir(parents=True)
        (checkout / 'code.py').write_text('keep')
        snapshot = self.call('inspect-work', work='one')
        self.assertTrue(self.call('close-work', work='one', expect=snapshot['sha256'])['changed'])
        self.assertFalse(self.call('close-work', work='one', expect=snapshot['sha256'])['changed'])
        self.assertEqual([p.name for p in (folder / 'work').iterdir()], ['other'])
        self.assertTrue((folder / 'knowledge/keep.md').exists())
        self.assertEqual((checkout / 'code.py').read_text(), 'keep')

    def test_close_refuses_intervening_changes_and_symlinks(self):
        folder = self.env()
        self.write('work/one/README.md', 'complete')
        snapshot = self.call('inspect-work', work='one')
        self.write('work/one/handoffs/pending.md', 'pending')
        self.error('document_conflict', self.call, 'close-work', work='one', expect=snapshot['sha256'])
        self.assertTrue((folder / 'work/one/handoffs/pending.md').exists())
        (folder / 'work/one/external').symlink_to(self.project)
        self.error('unsafe_path', self.call, 'inspect-work', work='one')
        self.error('invalid_input', self.call, 'inspect-work', work='../one')

    def test_close_moves_work_to_trash_without_overwriting(self):
        folder = self.env()
        self.write('work/one/README.md', 'complete')
        (folder / 'work/one/output.html').write_text('<p>kept</p>')
        snapshot = self.call('inspect-work', work='one')
        first = self.call('close-work', work='one', expect=snapshot['sha256'])
        trashed = Path(first['trash'])
        self.assertEqual(trashed.parent, folder / 'trash')
        self.assertTrue(trashed.name.startswith('one-'))
        self.assertEqual((trashed / 'output.html').read_text(), '<p>kept</p>')
        self.assertFalse((folder / 'work/one').exists())
        self.write('work/one/README.md', 'new work')
        snapshot = self.call('inspect-work', work='one')
        with patch.object(harness.time, 'strftime', return_value=trashed.name[len('one-'):]):
            second = self.call('close-work', work='one', expect=snapshot['sha256'])
        self.assertNotEqual(second['trash'], first['trash'])
        self.assertEqual((Path(second['trash']) / 'README.md').read_text(), 'new work')
        self.assertEqual((trashed / 'README.md').read_text(), 'complete')
        self.assertEqual(sorted(p.name for p in (folder / 'trash').iterdir()), sorted([trashed.name, Path(second['trash']).name]))
        self.error('unsafe_path', self.call, 'read', file='trash/one/README.md')
        self.assertEqual(self.call('resolve')['trash'], str(folder / 'trash'))

    def test_cli_json_input_stdin_and_errors(self):
        command = [sys.executable, '-B', str(ROOT / 'src/harness.py'), '--home', str(self.home)]
        init = subprocess.run(command + ['init', '--project', str(self.project)], capture_output=True, text=True)
        self.assertEqual(init.returncode, 0, init.stderr)
        result = subprocess.run(command + ['write', '--project', str(self.project), '--file', 'work/one/README.md',
                                '--expect', 'missing', '--input', '-'], input='hello', capture_output=True, text=True)
        self.assertTrue(json.loads(result.stdout)['changed'])
        result = subprocess.run(command + ['read', '--project', str(self.project), '--file', '../no.md'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)['error']['code'], 'unsafe_path')
