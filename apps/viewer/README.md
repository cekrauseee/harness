# Map viewer

A local, read-only web app that renders a Harness change map: the cards, flows, attention points and code that an execution produced. It serves one map folder, watches it, and updates the page while an orchestration is still writing to it. It never writes.

The viewer is application source, not part of any installed skill. It needs Node and pnpm; the map data stays valid without it, and the Python test suite never needs Node.

## Commands

Run everything from `apps/viewer`:

```bash
pnpm install
pnpm dev --map /path/to/work/<work>/map
```

- `--map <folder>` (or `--map=<folder>`, or the `HARNESS_MAP_DIR` environment variable) selects the map folder. Without it the synthetic fixture in `fixtures/synthetic` is served. The folder may not exist yet; the viewer starts and picks it up once it appears.
- The server listens on `127.0.0.1:5179`. Start one instance per orchestration; each takes the next free port, or pass `--port <n>` (add `--strictPort` to fail instead).
- `pnpm build` then `pnpm preview --map <folder>` serves the built app with the same read-only map route, without live updates.

`scripts/serve.mjs` turns `--map` into `HARNESS_MAP_DIR` and hands every other argument to the Vite CLI.

Checks:

```bash
pnpm typecheck      # tsc, strict
pnpm lint           # ESLint, including React hooks rules and import boundaries
pnpm format:check   # Prettier (pnpm format to fix)
pnpm test           # Vitest + Testing Library
pnpm check          # generated types up to date, then all of the above
```

## Data contract

The viewer renders `map.json` (format `harness-map-v1`) from the served folder; the map skill writes it to `work/<work>/map/`. Other files there, such as `supplement.json`, are inputs to the map skill and are ignored. The contract is `schema/map.v1.json` at the repository root, with field meanings in `docs/records.md`; the viewer never defines its own shape:

- `src/data/map.v1.ts` is generated from the schema with `pnpm gen:types` (`HARNESS_MAP_SCHEMA=<file>` points at another copy). `pnpm check` fails when it is out of date, and skips that step when the schema is absent.
- `src/data/selectors.ts` is the only adapter between the schema and the features: canvas model and grouping, selection, highlights, code references, coverage.
- The fixtures validate against the schema in the tests.

Every list in a map is present and may be empty; empty sections are hidden. Edges derived from imports are solid; authored edges are dotted and show their label on the canvas and in the card detail. Changed files that no card claims are listed in the overview. Flows with steps open as a stepper, flows without steps show trigger, outcome and path. Code comes from the map's `code` payload: added files are split by their symbol notes, changed files by hunk, and a hunk without a note shows the subjects of the commits that introduced it.

`plugins/map-source.ts` serves the folder under `/map/`: GET and HEAD only, regular files only, no directory listing, no dotfiles, nothing outside the folder (symlinks included), `Cache-Control: no-store`. In dev it watches the folder and sends a `harness-map:changed` event; `src/data/source.ts` reloads the map on that event. A reload that fails (for example a file read mid-write) keeps the last good map and logs a warning. Missing lists become empty and edges that point at unknown cards are dropped, so a partial map still renders.

Everything shown comes from the data: title, summary, layers, module names, actors. The viewer never rewrites that text, so the data must be written for display as `docs/records.md` (Display copy) describes; the UI copy in code is generic.

## Structure

```text
src/
  app/          entry composition: providers, theme, ChangeMap (layout shell and the state features share), global CSS and tokens
  data/         generated map types, loader with live reload, MapContext, selectors (index, canvas model, grouping, selection, highlights)
  features/
    graph/        own canvas: layout, pan, zoom, drag, animated relayout, module scope bar
    sheet/        floating panel shell, index (flows, attention) and overview
    cards/        card and module detail
    flows/        flow detail and reproduction stepper
    attention/    attention point detail
    code/         code panel with Shiki highlighting
    search/       ⌘K command menu
    toolbar/      canvas tools and theme toggle
  shared/
    ui/         shadcn registry components, untouched except theming
    blocks/     building blocks composed from registry primitives: section, header, references, chips, tags
    motion/     motion tokens and the cascade (Stagger, Item)
    lib/        small hooks and utilities
  test/         test setup
plugins/        Vite plugin serving the map folder
scripts/        `serve.mjs` (CLI wrapper), `gen-types.mjs` (types from the schema)
fixtures/       synthetic maps: `synthetic` (9 cards with code, runs and follow-ups), `grouped` (48 cards in 6 modules)
```

Layering is app → features → data and shared. A feature is imported only through its `index.ts`; features never import the app or each other, so cross-feature state lives in `app/` or `data/`. ESLint enforces these boundaries.

When a change has more than 40 cards and the map declares modules, the canvas shows modules first; clicking one drills in, and search or card chips switch modules as needed.

## Components and visual language

Use shadcn registry components first (`pnpm dlx shadcn@4.21.5 add <name>`, style `radix-nova`, configured in `components.json`) and style on top: theme variables in `src/app/index.css`, then `className`. Build an own component only for integrated pieces such as the canvas, sheet, stepper, code panel or toolbar, and compose it from registry primitives.

The look is technical and minimal, with monospace in a leading role. One easing (`cubic-bezier(.2,.8,.2,1)`), critically damped springs, a shared "rise" entrance with cascades by nesting, sequential view transitions, and `prefers-reduced-motion` respected everywhere. The focus ring appears only after keyboard input; cursors always express the action. Tailwind only emits class names written literally, so dynamic values map to static class lists (see `LayerDot`).

## Tests

Tests cover what breaks silently: the read-only guarantees of the map route, fixtures against the schema, canvas grouping and selection resolution, layout of dependency cycles, and the essential interactions (open a card and go back, search to an attention point, step through a flow, open and close code). Visual details and animation timing are not tested.
