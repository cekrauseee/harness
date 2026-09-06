#!/usr/bin/env python3
"""Check actual selective skills installations in disposable homes."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(command, cwd, env, content=None):
    result = subprocess.run(command, cwd=cwd, env=env, input=content, text=True,
                            capture_output=True, timeout=120)
    if result.returncode:
        raise RuntimeError(f'{command}\n{result.stdout}\n{result.stderr}')
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workflows', type=Path)
    parser.add_argument('--cli', type=Path, help='Existing skills bin/cli.mjs')
    args = parser.parse_args()
    env = dict(os.environ, DISABLE_TELEMETRY='1', NO_COLOR='1')
    cli = args.cli or Path(run(['npx', '--yes', '--package', 'skills@1.5.23', '--', 'which', 'skills'], ROOT, env).strip().splitlines()[-1]).resolve()
    command = [shutil.which('node') or 'node', str(cli)]
    print('skills CLI ' + run(command + ['--version'], ROOT, env).strip())
    packages = [ROOT] + ([args.workflows.resolve()] if args.workflows else [])
    count = 0
    for package in packages:
        for skill in sorted((package / 'skills').glob('*/SKILL.md')):
            for copy_mode in (False, True):
                with tempfile.TemporaryDirectory(prefix='skills-install-check-') as temporary:
                    root = Path(temporary).resolve()
                    source, home, project = root/'source', root/'home', root/'project'
                    home.mkdir(); project.mkdir()
                    shutil.copytree(skill.parent, source/'skills'/skill.parent.name, ignore=shutil.ignore_patterns('__pycache__'))
                    # Only these child processes use disposable installation and state directories.
                    child = dict(env, HOME=str(home), CODEX_HOME=str(home/'.codex'),
                                 CLAUDE_CONFIG_DIR=str(home/'.claude'), XDG_CONFIG_HOME=str(home/'.config'),
                                 HARNESS_HOME=str(root/'state'), PYTHONPATH='', CI='1')
                    install = command + ['add', str(source), '--skill', skill.parent.name, '-g', '-a', 'codex', 'claude-code', '-y']
                    if copy_mode: install.append('--copy')
                    assert skill.parent.name in run(command+['add',str(source),'--list'],project,child)
                    probe = source/'skills'/skill.parent.name/'update-probe.txt'
                    retired = source/'skills'/skill.parent.name/'removed-probe.txt'
                    probe.write_text('before'); retired.write_text('removed next')
                    run(install,project,child)
                    probe.write_text('after'); retired.unlink()
                    run(install,project,child)
                    target=home/'.agents/skills'/skill.parent.name
                    if not target.exists(): target=next(home.glob(f'.*/skills/{skill.parent.name}'))
                    assert (target/'update-probe.txt').read_text()=='after'
                    assert not (target/'removed-probe.txt').exists()
                    for original in skill.parent.rglob('*'):
                        if original.is_file() and '__pycache__' not in original.parts:
                            assert original.read_bytes()==(target/original.relative_to(skill.parent)).read_bytes()
                    shutil.rmtree(source)
                    helper=target/'scripts/harness.py'
                    if helper.exists():
                        def call(op,*flags,content=None):
                            return json.loads(run([sys.executable,str(helper),op,'--project',str(project),*flags],project,child,content))
                        call('init')
                        owner=call('claim','--purpose','Verify copied helper','--resource','draft.md')['contribution']
                        call('handoff','--owner',owner['id'],'--expect',str(owner['version']),'--input','-','--release',content='Copied helper works; no project file was changed.\n')
                        assert not call('status')['reservations']
                        call('write','--file','note.md','--expect','missing','--input','-',content='# Source\n\nA current note.\n')
                        assert call('read','--file','note.md')['content']=='# Source\n\nA current note.\n'
                    assert not list(project.iterdir())
                    assert skill.parent.name in run(command+['list','-g','--json'],project,child)
                    run(command+['remove',skill.parent.name,'-g','-a','codex','claude-code','-y'],project,child)
                    assert skill.parent.name not in run(command+['list','-g','--json'],project,child)
                    count+=1
                    print(f'{package.name}/{skill.parent.name}: {"copy" if copy_mode else "symlink"} passed',flush=True)
    print(f'{count} isolated installations, updates and removals passed.')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
