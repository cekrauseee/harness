#!/usr/bin/env python3
"""Generate only the script, schema and reference copies a self-contained skill actually uses."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from harness import atomic_write, make_directory

# A path named in SKILL.md, or needed by another generated file, is copied from its canonical source.
SOURCES = {
    'scripts/harness.py': 'scripts/harness.py',
    'scripts/records.py': 'scripts/records.py',
    'scripts/run.py': 'scripts/run.py',
    'scripts/changemap.py': 'scripts/changemap.py',
    'references/file-context.md': 'docs/file-context.md',
    'references/records.md': 'docs/records.md',
    'references/host-integration.md': 'docs/host-integration.md',
}
# Imports and links between generated files; 'schema' stands for every schema/*.json, shipped only with scripts that load it.
NEEDS = {
    'scripts/records.py': ('scripts/harness.py', 'schema'),
    'scripts/run.py': ('scripts/records.py',),
    'scripts/changemap.py': ('scripts/records.py',),
    'references/file-context.md': ('references/records.md',),
}


def generated(text):
    selected = {path for path in SOURCES if path in text}
    pending = list(selected)
    while pending:
        for needed in NEEDS.get(pending.pop(), ()):
            if needed not in selected:
                selected.add(needed)
                pending.append(needed)
    for path in sorted(selected):
        if path == 'schema':
            for schema in sorted((ROOT / 'schema').glob('*.json')):
                yield schema, f'schema/{schema.name}'
        else:
            yield ROOT / SOURCES[path], path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    copies = []
    for entry in sorted((ROOT / 'skills').glob('*/SKILL.md')):
        copies += [(source, entry.parent / target) for source, target in generated(entry.read_text())]
    problems = []
    for source, target in copies:
        content = source.read_bytes()
        if target.exists() and target.read_bytes() == content:
            continue
        if args.check:
            problems.append(str(target.relative_to(ROOT)))
        else:
            make_directory(target.parent)
            atomic_write(target, content)
    if problems:
        print('Generated content drift: ' + ', '.join(problems))
        return 1
    print(f'{len(copies)} standalone script/schema/reference copies match canonical sources.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
