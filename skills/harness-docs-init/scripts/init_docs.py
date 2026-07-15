#!/usr/bin/env python3
"""Create missing canonical project documentation without overwriting content."""

from __future__ import annotations

import argparse
from pathlib import Path


TEMPLATES = {
    "README.md": """# Project Name

Describe the project purpose in one short paragraph.

## Development

See the [developer documentation](docs/index.md).
""",
    "docs/index.md": """# Developer Documentation

Read only the documents relevant to the task.

| Document | Read when |
| --- | --- |
| [Project](project.md) | Understanding project purpose, scope, or concepts |
| [Architecture](architecture.md) | Changing system boundaries or cross-cutting behavior |
| [Development](development.md) | Setting up, testing, or contributing |
| [Artifacts](artifacts/index.md) | Viewing project diagrams, flows, or reports |

## Modules

Add focused module documents here as they are created.
""",
    "docs/project.md": """# Project

## Purpose

Describe the verified project purpose.

## Scope

Describe what the project includes and excludes.

## Core Concepts

Define the concepts a developer must understand.

## Boundaries

State the stable product boundaries.
""",
    "docs/architecture.md": """# Architecture

## Overview

Describe the system at a high level.

## Components

Describe the main components and their responsibilities.

## Data Flow

Describe how data moves through the system.

## Invariants

List constraints that must remain true.
""",
    "docs/development.md": """# Development

## Prerequisites

List required tools and versions.

## Setup

Document the shortest verified setup path.

## Commands

List the commands developers use.

## Testing

Explain how to verify changes.

## Conventions

Document project-specific contribution rules.
""",
    "docs/artifacts/index.md": """# Artifacts

Final, user-facing HTML visualizations of the project live here.

| Artifact | Purpose |
| --- | --- |
""",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", nargs="?", default=".")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"Project root is not a directory: {root}")

    (root / "docs" / "modules").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "artifacts").mkdir(parents=True, exist_ok=True)

    created: list[str] = []
    for relative, content in TEMPLATES.items():
        target = root / relative
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        created.append(relative)

    print(f"Documentation root: {root / 'docs'}")
    print(f"Files created: {len(created)}")
    for relative in created:
        print(f"- {relative}")


if __name__ == "__main__":
    main()
