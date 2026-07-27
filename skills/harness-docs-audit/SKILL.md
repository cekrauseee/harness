---
name: harness-docs-audit
description: Audit project documentation and HTML artifacts for structure, routing, links, size, accessibility, dependencies, drift, duplication, and Harness boundaries. Use during documentation review or before publication.
---

# Harness Docs Audit

Run deterministic checks first, then review semantic accuracy against the project.

## Procedure

1. Run `scripts/check_docs.py <project-root> --strict`.
2. Use `--format json` when structured findings are useful.
3. Read `docs/index.md`, then only files implicated by the findings.
4. Compare behavior claims with relevant source, tests, configuration, and explicit decisions.
5. Fix issues when authorized; otherwise report the smallest actionable set.
6. Re-run the checker after changes.

## Review Rules

- Require the canonical baseline created by `harness-docs-init`.
- Route each module document from `docs/index.md` and each HTML artifact from `docs/artifacts/index.md`.
- Keep local Markdown links valid and use one canonical source for each active explanation.
- Write in simple, objective, coherent, and concise English.
- Treat size thresholds as prompts to improve routing, not reasons for arbitrary splitting.
- Verify that diagrams, commands, architecture claims, and module contracts match the project.
- Keep memory, session state, drafts, investigations, and provisional decisions out of versioned docs.
- Require artifacts to be final, static, self-contained, accessible HTML with a neutral Harness presentation.
- Reject project branding, application UI imitation, frameworks, build steps, and external runtime dependencies in artifacts.

## Severity

- Issues fail every run: missing baseline paths, broken local links, invalid artifact structure, external artifact dependencies, or unindexed artifacts.
- Warnings fail only with `--strict`: oversized files, unindexed module docs, or maintainability concerns.

## Size Guidance

- `README.md`: 120 lines.
- `docs/index.md`: 100 lines.
- Macro documents: 220 lines.
- Module documents: 180 lines.
- `docs/artifacts/index.md`: 160 lines.
