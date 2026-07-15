---
name: harness-docs-maintain
description: Maintain concise, canonical, English developer documentation in README.md and docs/. Use when documenting a project change, architecture, module, setup, command, workflow, contract, or stable decision, or when reorganizing documentation and removing stale or duplicate guidance.
---

# Harness Docs Maintain

Update the narrowest canonical document affected by the change. Documentation must describe verified current behavior, not the implementation process or agent conversation.

## Procedure

1. Read `docs/index.md`, then only the documents routed for the affected subject.
2. Verify each claim against source, configuration, tests, or an explicit user decision.
3. Update the narrowest canonical file. Create `docs/modules/<subject>.md` when a bounded topic would make a macro document harder to scan.
4. Update `docs/index.md` when adding, moving, renaming, or removing a document.
5. Remove or replace stale and duplicate guidance in the same change.
6. Use `harness-artifact` for a final user-facing HTML visualization. Keep drafts in the Harness workspace.
7. Run `harness-docs-audit` after structural changes.

## Placement

- Use `README.md` for the project entry point and first-run path.
- Use `docs/project.md` for product purpose, scope, concepts, and boundaries.
- Use `docs/architecture.md` for cross-cutting structure, components, data flow, and invariants.
- Use `docs/development.md` for setup, commands, testing, and contributor workflow.
- Use `docs/modules/*.md` for focused subsystem behavior and contracts.
- Use `docs/artifacts/*.html` only for final user-facing visualizations and list them in `docs/artifacts/index.md`.

## Writing Rules

- Write in English, even when the request is in another language.
- Use simple, objective, coherent, and concise language.
- Prefer active voice, short sentences, descriptive headings, and one main idea per paragraph.
- Keep names, paths, commands, constraints, and ownership explicit.
- Avoid marketing language, decorative prose, raw investigation logs, and repeated explanations.
- Prefer a compact table for exact mappings. Use Mermaid only for meaningful multi-component relationships or sequences.
- Mark uncertainty and verify it before presenting it as fact.
- Keep operational memory, session state, drafts, and provisional decisions in the Harness, not in versioned documentation.
