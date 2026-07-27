---
name: harness-docs-init
description: Create or repair a concise English developer-documentation baseline without overwriting content. Use when a code project lacks canonical README, architecture, development, module, or artifact routing.
---

# Harness Docs Init

Create the smallest useful canonical documentation surface. Keep agent memory, handoffs, drafts, and provisional findings outside the repository documentation.

## Procedure

1. Inspect the repository, existing documentation, configuration, and relevant source files.
2. Run `scripts/init_docs.py <project-root>` to create only missing baseline files and directories.
3. Replace generic content with facts verified from source, configuration, tests, or explicit user decisions.
4. Preserve existing user content. Resolve conflicts deliberately instead of overwriting files.
5. Link focused documents from `docs/index.md` with a clear reason to read each one.
6. Run the checker bundled with `harness-docs-audit` when that skill is available.

## Canonical Layout

```text
README.md
docs/
  index.md
  project.md
  architecture.md
  development.md
  modules/
  artifacts/
    index.md
```

## File Roles

- `README.md`: short project entry point, basic development path, and link to `docs/index.md`.
- `docs/index.md`: routing map for the rest of the documentation.
- `docs/project.md`: purpose, scope, concepts, and stable product boundaries.
- `docs/architecture.md`: system components, boundaries, data flow, and invariants.
- `docs/development.md`: prerequisites, setup, commands, testing, and contribution rules.
- `docs/modules/*.md`: one bounded subsystem or capability per file.
- `docs/artifacts/index.md`: catalog of final, user-facing HTML visualizations.

## Writing Rules

- Write all repository documentation in English.
- Use simple, objective, coherent, and concise language.
- Prefer active voice, short paragraphs, descriptive headings, and exact commands.
- Keep one canonical explanation and link to it elsewhere.
- State unknowns plainly. Never invent behavior, commands, or architecture.
- Use Mermaid only when relationships or sequences are materially clearer than prose.
- Keep draft HTML and intermediate work in the Harness workspace. Route final HTML visualizations through `harness-artifact`.
