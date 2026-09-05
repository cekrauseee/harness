#!/usr/bin/env python3
"""Verify real skills CLI installs with disposable homes and unavailable sources."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
CLI_VERSION = '1.5.23'


def run(command, cwd, env, allowed=(0,)):
    result = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, timeout=120)
    if result.returncode not in allowed:
        raise RuntimeError(f'Failed ({result.returncode}): {command}\n{result.stdout}\n{result.stderr}')
    return result


def child_environment(home, state):
    # These overrides belong only to the disposable CLI child processes.
    env = dict(os.environ)
    env.update(HOME=str(home), CODEX_HOME=str(home / '.codex'), CLAUDE_CONFIG_DIR=str(home / '.claude'),
               XDG_CONFIG_HOME=str(home / '.config'), HARNESS_HOME=str(state), PYTHONPATH='',
               DISABLE_TELEMETRY='1', CI='1', NO_COLOR='1')
    return env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workflows', type=Path)
    parser.add_argument('--cli', type=Path, help='Existing skills bin/cli.mjs; otherwise resolve the pinned CLI through npx.')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    node = shutil.which('node')
    if not node:
        parser.error('Node.js is needed only for this installation verification.')
    base_env = dict(os.environ, DISABLE_TELEMETRY='1', NO_COLOR='1')
    if args.cli:
        cli = args.cli.resolve()
    else:
        found = run(['npx', '--yes', '--package', f'skills@{CLI_VERSION}', '--', 'which', 'skills'], ROOT, base_env)
        cli = Path(found.stdout.strip().splitlines()[-1]).resolve()
    version = run([node, str(cli), '--version'], ROOT, base_env).stdout.strip()
    report = {'skills_cli': version, 'python': sys.version.split()[0], 'node': run([node, '--version'], ROOT, base_env).stdout.strip(), 'telemetry': False, 'cases': []}
    packages = [ROOT] + ([args.workflows.resolve()] if args.workflows else [])
    started = time.monotonic()
    for package in packages:
        skills = sorted(p.name for p in (package / 'skills').iterdir() if (p / 'SKILL.md').is_file())
        for copy_mode in (False, True):
            for name in skills:
                with tempfile.TemporaryDirectory(prefix='harness-install-') as temporary:
                    root = Path(temporary).resolve()
                    source = root / 'source'
                    source.mkdir()
                    shutil.copytree(package / 'skills' / name, source / 'skills' / name, ignore=shutil.ignore_patterns('__pycache__'))
                    home = root / 'home'; home.mkdir()
                    project = root / 'project'; project.mkdir()
                    env = child_environment(home, root / 'state')
                    command = [node, str(cli)]
                    before = time.monotonic()
                    listing = run(command + ['add', str(source), '--list'], project, env)
                    if name not in listing.stdout:
                        raise RuntimeError(f'Skill not discovered: {name}')
                    install = ['add', str(source), '--skill', name, '-g', '-a', 'codex', 'claude-code', '-y']
                    if copy_mode:
                        install.append('--copy')
                    probe = source / 'skills' / name / 'install-verification.txt'
                    probe.write_text('first installed version\n')
                    removed_probe = source / 'skills' / name / 'removed-file.txt'
                    removed_probe.write_text('File removed by the next version\n')
                    run(command + install, project, env)
                    # Reinstall changed bytes, not merely identical content.
                    probe.write_text('updated installed version\n')
                    removed_probe.unlink()
                    run(command + install, project, env)
                    listing = run(command + ['list', '-g', '--json'], project, env)
                    if name not in listing.stdout:
                        raise RuntimeError(f'Installed skill not listed: {name}')
                    shutil.rmtree(source)
                    installed = home / '.agents' / 'skills' / name
                    if not installed.is_dir():
                        candidates = list(home.glob(f'.*/skills/{name}'))
                        if not candidates:
                            raise RuntimeError(f'No installed artifact found: {name}')
                        installed = candidates[0]
                    if (installed / 'install-verification.txt').read_text() != 'updated installed version\n':
                        raise RuntimeError(f'Local update did not replace installed content: {name}')
                    if (installed / 'removed-file.txt').exists():
                        raise RuntimeError(f'Removed source file remains installed: {name}')
                    script = installed / 'scripts/harness.py'
                    if script.exists():
                        def harness(op, data=None):
                            value = run([sys.executable, str(script), op, '--project', str(project), '--data', json.dumps(data or {})], project, env)
                            return json.loads(value.stdout)
                        harness('init')
                        start = harness('task.start', {'objective':'Test standalone installation','resources':['draft.txt'],'request_id':'start'})
                        harness('task.checkpoint', {'session_id':start['session']['id'],'summary':'Standalone execution verified.','evidence':['installed source unavailable'],'next_action':'','status':'delivered','request_id':'delivery'})
                        if harness('consolidate')['claims']:
                            raise RuntimeError('Delivery did not release the installed runtime claim.')
                        harness('remember', {'title':'Installed knowledge','summary':'Portable package works.','content':'A sourced test record.','kind':'fact','sources':['installation verification'],'scope':'project','aliases':['instalacao'],'request_id':'memory'})
                        if len(harness('recall', {'query':'instalacao'})['entries']) != 1:
                            raise RuntimeError('Installed recall did not recover its knowledge.')
                        harness('maintain')
                    else:
                        for helper in sorted((installed / 'scripts').glob('*.py')):
                            run([sys.executable, str(helper), '--help'], project, env)
                    if list(project.iterdir()):
                        raise RuntimeError(f'Global install/runtime changed the project: {list(project.iterdir())}')
                    run(command + ['remove', name, '-g', '-a', 'codex', 'claude-code', '-y'], project, env)
                    removed = run(command + ['list', '-g', '--json'], project, env)
                    if name in removed.stdout:
                        raise RuntimeError(f'Skill still listed after removal: {name}')
                    report['cases'].append({'package':package.name,'skill':name,'mode':'copy' if copy_mode else 'symlink','source_removed':True,'reinstall':True,'updated_bytes_verified':True,'remove':True,'seconds':round(time.monotonic()-before,3)})
                    print(f'{package.name}: {name} ({report["cases"][-1]["mode"]}) passed', flush=True)
    report['total_seconds'] = round(time.monotonic() - started, 3)
    report['limitations'] = ['Local reinstall tested; remote skills update and public indexing require a published version.', 'Workflows helpers execute --help here; their semantic behavior is covered by the Workflows unit suite.']
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
