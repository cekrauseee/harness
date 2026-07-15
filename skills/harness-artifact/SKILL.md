---
name: harness-artifact
description: Create, update, index, and validate final user-facing HTML visualizations in docs/artifacts/. Use when a project needs a versioned architecture map, flow, comparison, report, or other inspectable HTML explanation rather than application UI or temporary agent output.
---

# Harness Artifact

Create final documentation visualizations for project users. An artifact is versioned canonical documentation, not application code, a product prototype, or a draft.

## Procedure

1. Verify that HTML materially improves understanding over concise Markdown, a table, or Mermaid.
2. Keep exploration and intermediate renders in the Harness workspace.
3. Run `scripts/create_artifact.py <project-root> <slug> --title "<title>" --summary "<summary>"` to create a neutral baseline and index entry. Use a lowercase kebab-case slug.
4. Replace the baseline body with a focused visualization derived from verified project sources.
5. Keep the result at `docs/artifacts/<slug>.html` and its catalog entry in `docs/artifacts/index.md`.
6. Ensure `docs/index.md` routes readers to `docs/artifacts/index.md`.
7. Run `scripts/check_artifacts.py <project-root>` and fix every issue.

## Artifact Contract

- Write visible content in simple, objective, coherent, and concise English.
- Produce static, self-contained HTML that opens directly from disk.
- Include `<!doctype html>`, `lang="en"`, UTF-8 metadata, a responsive viewport, a unique title, one `h1`, and a `main` landmark.
- Use semantic HTML, keyboard-visible focus, sufficient contrast, and text alternatives for meaningful images.
- Use a neutral Harness presentation with system fonts and restrained layout styles.
- Keep CSS and any necessary script inline. Prefer HTML and CSS; use inline JavaScript only when it materially improves the explanation.
- Do not load fonts, styles, scripts, images, media, or data from external URLs.
- Do not use frameworks, package dependencies, build steps, analytics, or network calls.
- Do not copy project branding, colors, logos, or application interface patterns.
- Link to supporting canonical documentation when useful, but keep the visualization understandable on its own.

## Boundaries

- Store drafts, generated source data, screenshots, and discarded variants in the Harness workspace, never in `docs/artifacts/`.
- Do not route final artifacts to a temporary output folder when they belong to the project documentation.
- Do not present an artifact as an implementation proposal unless the user explicitly requests that kind of documentation.
- Remove or update stale artifacts with the documentation change that invalidates them.
