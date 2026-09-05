"""Small JSON command interface shared by every independently installed skill."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from . import __version__
from .core import HarnessError

GUIDES = {
    'init': {'required': [], 'optional': ['title', 'host', 'host_project_id'], 'next': 'Save project/workspace IDs; task.start before shared writes.'},
    'resolve': {'required': [], 'next': 'Read identity without initialization. Missing or unsupported state is an error, not an empty project.'},
    'task.start': {'required': ['objective', 'resources', 'request_id'], 'example': {'objective': 'Update the introduction', 'resources': ['notes/introduction.md'], 'request_id': 'introduction-start'}, 'next': 'Save session_id. If conflict, inspect owners and continue only independent work.'},
    'task.join': {'required': ['task_id', 'resources', 'request_id'], 'next': 'Creates a separate participant; does not reuse another participant\'s claims.'},
    'task.claim': {'required': ['session_id', 'resources', 'request_id'], 'next': 'Claim additional resources atomically before writing. Resources are project/workspace-relative paths, not globs.'},
    'task.checkpoint': {'required': ['session_id', 'summary', 'evidence', 'next_action', 'status', 'request_id'], 'example': {'session_id': '<returned-id>', 'summary': 'Updated the introduction.', 'evidence': ['Reviewed notes/introduction.md'], 'next_action': 'User acceptance pending.', 'status': 'delivered', 'request_id': 'introduction-delivery'}, 'next': 'active or blocked preserves claims; delivered releases this session\'s claims. Evidence is a report, not automatic verification or approval.'},
    'task.release': {'required': ['session_id', 'reason', 'request_id'], 'next': 'Release your responsibility, or explicitly reconcile a former writer with independent evidence recorded in reason. Age alone is insufficient. This closes the participant. Join the task again for a new session before further writes; silence never releases claims.'},
    'task.list': {'required': [], 'optional': ['scope'], 'next': 'Inspect task IDs, status, participants and workspace provenance.'},
    'task.show': {'required': ['task_id'], 'next': 'Read relevant checkpoints and pending actions for this task.'},
    'task.event': {'required': ['session_id', 'kind', 'evidence', 'request_id'], 'optional': ['resolves_checkpoint_ids', 'resolves_session_ids'], 'next': 'Record accepted, committed, published or resolved with evidence. Resolve follow-ups by naming their checkpoint IDs; reconcile released participants by naming their session IDs. Events alone do not infer which pending text is resolved.'},
    'consolidate': {'required': [], 'next': 'Read all current-workspace claims and contributions. To establish a cooperative stable point, task.start with resources ["."] first, then compare this report to actual files. This read alone does not acquire ownership.'},
    'changes': {'required': ['since'], 'optional': ['limit', 'budget_chars', 'cursor'], 'next': 'Use returned next_cursor as cursor until caught up. A truncated page is not absence of further updates.'},
    'recall': {'required': ['query'], 'optional': ['limit', 'budget_chars'], 'next': 'Inspect compact cards then hydrate selected IDs. Lexical retrieval with aliases does not guarantee multilingual semantic equivalence. Reformulate or supply translations for a relevant gap.'},
    'hydrate': {'required': ['id'], 'optional': ['budget_chars'], 'next': 'Inspect omitted/truncated diagnostics before concluding content is complete.'},
    'remember': {'required': ['title', 'summary', 'content', 'kind', 'sources', 'scope', 'request_id'], 'optional': ['aliases', 'review_after'], 'example': {'title': 'Source ownership', 'summary': 'The archive is the source for quotations.', 'content': 'Use the cited archive when checking quotations.', 'kind': 'decision', 'sources': ['notes/editorial-decisions.md'], 'scope': 'project', 'aliases': ['fontes', 'citacoes'], 'request_id': 'source-decision'}, 'next': 'kind is fact, hypothesis, decision or historical. Keep canonical document content in that source; store only useful additional context. Exact retries return record identity only; hydrate the ID for current content.'},
    'memory.update': {'required': ['id', 'expected_revision', 'request_id'], 'next': 'Use the current memory record revision. Make reclassification or supersession explicit; retain provenance. Exact retries return record identity only; hydrate the ID for current content.'},
    'maintain': {'required': [], 'next': 'Read integrity, stale presence, duplicate and broken-reference diagnostics. It does not infer semantic truth or delete active work.'},
    'project.bind': {'required': ['project_id', 'evidence', 'request_id'], 'next': 'Bind an explicitly identified existing project. Never infer project equality from a remote URL.'},
    'project.move': {'required': ['project_id', 'from_path', 'evidence', 'request_id'], 'next': 'Use guide/reference to confirm the move, including old path and preservation of claims.'},
    'integration.preview': {'required': ['file'], 'optional': ['runtime'], 'next': 'Review exact block and expected_sha256. No file changes occur.'},
    'integration.install': {'required': ['file', 'expected_sha256'], 'optional': ['runtime'], 'next': 'Only after authorization to modify this instruction file. Reinstall is idempotent; user edits are preserved or reported.'},
    'integration.status': {'required': ['file'], 'next': 'Verify managed block integrity and selected installed runtime.'},
    'integration.remove': {'required': ['file', 'expected_sha256'], 'next': 'Remove only the intact managed block. Obtain current sha256 from integration.status.'},
}


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise HarnessError('invalid_arguments', message, {'recovery': 'Run --help or guide for the requested operation.'})


def main(argv: list[str] | None = None) -> int:
    try:
        parser = Parser(description='Harness: project continuity in local files. Every result is JSON; exit 2 means the operation failed.')
        parser.add_argument('operation', nargs='?', default='guide', help='Operation name, such as task.start, recall, integration.preview, or guide.')
        parser.add_argument('--project', help='Project directory (defaults to the current directory).')
        inputs = parser.add_mutually_exclusive_group()
        inputs.add_argument('--data', help='JSON object containing semantic inputs. Use --input for long content.')
        inputs.add_argument('--input', help='Read a JSON object from this file, or - for stdin.')
        parser.add_argument('--version', action='store_true')
        args = parser.parse_args(argv)
        if args.version:
            print(json.dumps({'version': __version__, 'schema_version': 3, 'defaults_version': 8}))
            return 0
        raw = args.data or '{}'
        if args.input:
            raw = sys.stdin.read() if args.input == '-' else Path(args.input).read_text(encoding='utf-8')
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise HarnessError('invalid_input', 'Input must be a JSON object.')
        if args.operation == 'guide':
            operation = data.get('operation')
            if operation and operation not in GUIDES:
                raise HarnessError('unknown_operation', f'Unknown operation: {operation}', {'operations': list(GUIDES)})
            result = {'success': True, 'operation': operation, 'guide': GUIDES[operation]} if operation else {'success': True, 'operations': list(GUIDES), 'usage': 'harness.py <operation> --project PATH --data JSON (or --input FILE)', 'retry': 'Reuse request_id only for the exact same operation and inputs. New actions need new keys.'}
        else:
            if args.project:
                if 'project' in data and data['project'] != args.project:
                    raise HarnessError('invalid_input', 'Project in --data disagrees with --project.')
                data['project'] = args.project
            data.setdefault('project', str(Path.cwd()))
            if args.operation.startswith('integration.'):
                from .integration import execute
                data.setdefault('runtime', str(Path(sys.argv[0]).resolve()))
            else:
                from .core import execute
            result = execute(args.operation, data)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except HarnessError as exc:
        print(json.dumps({'success': False, 'error': {'code': exc.code, 'message': str(exc), 'details': exc.details}}, ensure_ascii=False))
        return 2
    except (ValueError, OSError, TypeError) as exc:
        print(json.dumps({'success': False, 'error': {'code': 'invalid_input' if isinstance(exc, (ValueError, TypeError)) else 'io_error', 'message': str(exc)}}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
