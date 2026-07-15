#!/usr/bin/env python3
"""Create and index a neutral, self-contained HTML documentation artifact."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path


SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
INDEX_TEMPLATE = """# Artifacts

Final, user-facing HTML visualizations of the project live here.

| Artifact | Purpose |
| --- | --- |
"""


def render(title: str, summary: str) -> str:
    safe_title = html.escape(title)
    safe_summary = html.escape(summary)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title}</title>
  <style>
    :root {{ color-scheme: light dark; font-family: ui-sans-serif, system-ui, sans-serif; line-height: 1.5; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: Canvas; color: CanvasText; }}
    a {{ color: LinkText; }}
    a:focus-visible, button:focus-visible {{ outline: 3px solid Highlight; outline-offset: 3px; }}
    .skip-link {{ position: absolute; left: 1rem; top: -4rem; padding: .5rem .75rem; background: Canvas; }}
    .skip-link:focus {{ top: 1rem; }}
    header, main {{ width: min(72rem, calc(100% - 2rem)); margin-inline: auto; }}
    header {{ padding-block: 3rem 1rem; border-bottom: 1px solid GrayText; }}
    main {{ padding-block: 2rem 4rem; }}
    h1 {{ max-width: 24ch; margin: 0; font-size: clamp(2rem, 5vw, 3.5rem); line-height: 1.1; }}
    .summary {{ max-width: 70ch; font-size: 1.1rem; }}
    section {{ max-width: 70rem; margin-top: 2rem; }}
  </style>
</head>
<body>
  <a class="skip-link" href="#main-content">Skip to content</a>
  <header>
    <h1>{safe_title}</h1>
    <p class="summary">{safe_summary}</p>
  </header>
  <main id="main-content">
    <section aria-labelledby="overview-heading">
      <h2 id="overview-heading">Overview</h2>
      <p>{safe_summary}</p>
    </section>
  </main>
</body>
</html>
"""


def _index_row(slug: str, title: str, summary: str) -> str:
    clean_title = title.replace("|", "\\|").replace("\n", " ").strip()
    clean_summary = summary.replace("|", "\\|").replace("\n", " ").strip()
    return f"| [{clean_title}]({slug}.html) | {clean_summary} |"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root")
    parser.add_argument("slug")
    parser.add_argument("--title", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--force", action="store_true", help="Replace an existing artifact file.")
    args = parser.parse_args()

    if not SLUG.fullmatch(args.slug):
        raise SystemExit("Artifact slug must use lowercase kebab-case.")
    if not args.title.strip() or not args.summary.strip():
        raise SystemExit("Artifact title and summary must not be empty.")

    root = Path(args.project_root).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"Project root is not a directory: {root}")
    artifact_dir = root / "docs" / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    index = artifact_dir / "index.md"
    if not index.exists():
        index.write_text(INDEX_TEMPLATE, encoding="utf-8")

    target = artifact_dir / f"{args.slug}.html"
    if target.exists() and not args.force:
        raise SystemExit(f"Artifact already exists: {target}")
    target.write_text(render(args.title.strip(), args.summary.strip()), encoding="utf-8")

    index_text = index.read_text(encoding="utf-8")
    if f"({args.slug}.html)" not in index_text:
        if index_text and not index_text.endswith("\n"):
            index_text += "\n"
        index_text += _index_row(args.slug, args.title, args.summary) + "\n"
        index.write_text(index_text, encoding="utf-8")

    print(target)


if __name__ == "__main__":
    main()
