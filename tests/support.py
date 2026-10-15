"""Synthetic project, environment and records shared by the records, map and launcher tests."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import harness  # noqa: E402

WORK = 'checkout'
PLAN = """# Plan: checkout sessions

## Attention points

| Id | Category | Severity | Scenario | Handling | Proof | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| ap-session-race | concurrency | critical | A session is issued while the credential rotates. | Recheck the generation when issuing. | test | sessions |
| ap-schema-drift | data integrity | medium | The table and the code disagree on columns. | Keep one migration. | review | storage |

## Flows

| Id | Actor | Trigger | Outcome | Modules |
| --- | --- | --- | --- | --- |
| fl-sign-in | customer | Opens the sign-in page. | Reaches the cart. | sessions, web |

Map: yes. Three layers and a critical attention point.
"""

BASE_FILES = {
    'README.md': '# Shop\n',
    'src/store.py': 'def load(key):\n    return {}\n',
}
HEAD_COMMITS = [
    ('feat(sessions): issue sessions after rechecking the generation\n\nSessions are issued only when the credential generation is unchanged.', {
        'src/store.py': ('def load(key):\n    return {}\n\n\nclass Session:\n    def issue(self, generation):\n'
                         '        if generation != load("generation"):\n            raise ValueError("stale")\n'
                         '        return {"generation": generation}\n'),
        'src/api.py': 'from .store import Session\n\n\ndef sign_in(generation):\n    return Session().issue(generation)\n',
        'tests/test_store.py': ('from src.store import Session\n\n\ndef test_issue_rejects_a_stale_generation():\n'
                                '    assert Session\n'),
    }),
    ('feat(web): add the sign-in page\n\nThe page calls the client, which posts to the API.', {
        'web/page.ts': 'import { signIn } from "./client";\n\nexport function SignInPage() {\n  return signIn(1);\n}\n',
        'web/client.ts': 'export async function signIn(generation: number) {\n  return fetch("/api/sign-in");\n}\n',
    }),
    ('feat(storage): add the sessions table', {
        'db/sessions.sql': 'create table sessions (\n  generation integer not null\n);\n',
    }),
]


def git(cwd, *args):
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_AUTHOR_NAME='Harness Test', GIT_AUTHOR_EMAIL='harness@example.invalid',
               GIT_COMMITTER_NAME='Harness Test', GIT_COMMITTER_EMAIL='harness@example.invalid')
    result = subprocess.run(['git', '-C', str(cwd), '-c', 'commit.gpgsign=false', *args],
                            capture_output=True, text=True, timeout=20, env=env)
    if result.returncode:
        raise RuntimeError(result.stderr)
    return result.stdout.strip()


def commit_files(project, files, message):
    for name, content in files.items():
        path = project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    git(project, 'add', '-A')
    git(project, 'commit', '-q', '-m', message)
    return git(project, 'rev-parse', 'HEAD')


def project_with_change(root):
    """A repository whose main is the base and whose feature branch adds sessions, a page and a table."""
    project = root / 'project'
    project.mkdir()
    git(project, 'init', '-q', '-b', 'main')
    base = commit_files(project, BASE_FILES, 'chore: initialize')
    git(project, 'checkout', '-q', '-b', 'feat/sessions')
    for message, files in HEAD_COMMITS:
        head = commit_files(project, files, message)
    return project, base, head


def environment(home, project, plan=PLAN):
    folder = Path(harness.execute('init', {'project': str(project)}, home)['environment'])
    work = folder / 'work' / WORK
    work.mkdir(parents=True)
    (work / 'README.md').write_text(plan)
    return folder


def sessions_record(base, head, run='impl-1', **changes):
    record = {
        'format': 'harness-record-v1', 'work': WORK, 'front': 'sessions', 'run': run, 'kind': 'implement',
        'iteration': 1, 'base': base, 'head': head,
        'summary': 'Sessions are issued after rechecking the credential generation.',
        'owned': ['ap-session-race'],
        'cards': [
            {'id': 'sessions', 'layer': 'domain', 'title': 'Sessions', 'summary': 'Issues sessions.',
             'files': ['src/store.py', 'tests/test_store.py']},
            {'id': 'api', 'layer': 'api', 'title': 'Sign-in API', 'summary': 'Signs customers in.',
             'files': ['src/api.py']},
        ],
        'files': {'src/store.py': 'Session issuance.', 'src/api.py': 'Sign-in entry point.',
                  'tests/test_store.py': 'Proves stale generations are rejected.'},
        'notes': [{'path': 'src/store.py', 'symbol': 'Session.issue', 'text': 'Rejects a stale generation.'}],
        'attention': [{'id': 'ap-session-race', 'status': 'handled', 'handling': 'Generation recheck at issue.',
                       'evidence': [{'path': 'src/store.py', 'symbol': 'Session.issue', 'note': 'The recheck.'}],
                       'tests': [{'path': 'tests/test_store.py', 'title': 'test_issue_rejects_a_stale_generation'}]}],
        'flows': [], 'tests': [{'path': 'tests/test_store.py', 'title': 'test_issue_rejects_a_stale_generation',
                                'ids': ['ap-session-race']}],
        'followups': [],
    }
    record.update(changes)
    return record
