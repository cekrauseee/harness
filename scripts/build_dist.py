#!/usr/bin/env python3
"""Copy the single helper into independently installable skills; --check checks drift."""
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
    source = (ROOT / 'src/harness.py').read_bytes()
    folders = [p.parent / 'scripts' for p in sorted((ROOT / 'skills').glob('*/SKILL.md'))]
    problems = []
    for folder in folders:
        target = folder / 'harness.py'
        if args.check:
            if not target.exists() or target.read_bytes() != source:
                problems.append(str(folder.relative_to(ROOT)))
            continue
        make_directory(folder)
        if not target.exists() or target.read_bytes() != source:
            atomic_write(target, source)
    if problems:
        print('Generated helper drift: ' + ', '.join(problems))
        return 1
    print(f'{len(folders)} standalone helper copies match src/harness.py.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
