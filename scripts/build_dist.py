#!/usr/bin/env python3
"""Copy the single helper into independently installable skills; --check checks drift."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    source = (ROOT / 'src/harness.py').read_bytes()
    folders = [p.parent / 'scripts' for p in sorted((ROOT / 'skills').glob('*/SKILL.md'))]
    problems = []
    for folder in folders:
        target = folder / 'harness.py'
        extras = [p for p in folder.rglob('*') if p.is_file() and p != target and '__pycache__' not in p.parts]
        if args.check:
            if not target.exists() or target.read_bytes() != source or extras:
                problems.append(str(folder.relative_to(ROOT)))
            continue
        sys.path.insert(0, str(ROOT / 'src'))
        from harness import atomic_write, make_directory
        make_directory(folder)
        for extra in extras:
            extra.unlink()
        if not target.exists() or target.read_bytes() != source:
            atomic_write(target, source)
        for path in sorted(folder.rglob('*'), key=lambda p: len(p.parts), reverse=True):
            if path.is_dir():
                try:
                    path.rmdir()
                except OSError:
                    pass
    if problems:
        print('Generated helper drift: ' + ', '.join(problems))
        return 1
    print(f'{len(folders)} standalone helper copies match src/harness.py.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
