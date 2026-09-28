#!/usr/bin/env python3
"""Generate only the helper/reference copies a self-contained skill actually uses."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from harness import atomic_write, make_directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    copies = []
    for entry in sorted((ROOT / 'skills').glob('*/SKILL.md')):
        text = entry.read_text()
        if 'scripts/harness.py' in text:
            copies.append((ROOT / 'src/harness.py', entry.parent / 'scripts/harness.py'))
        if 'references/file-context.md' in text:
            copies.append((ROOT / 'docs/file-context.md', entry.parent / 'references/file-context.md'))
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
    print(f'{len(copies)} standalone helper/reference copies match canonical sources.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
