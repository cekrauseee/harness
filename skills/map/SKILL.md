---
name: map
description: "Build a change map of a large branch or an orchestration from Git facts and execution records, fill only its gaps and open it in the local viewer. Use when closing an orchestration or a cross-layer change before review or QA, or when asked to map, explain or prepare QA for a change."
---

# Map

Build a change map when the plan says `Map: yes`, when a change crosses layers or modules, adds user-visible flows or carries a critical attention point, or when the user asks for one. A small single-module change of about ten files or fewer is better served by a clear pull request description; say so instead of building a map. A map explains and proves a change for reviewers; it does not replace review.

The map is built from what the work already produced: Git facts at zero tokens, the accepted run records of every front, and the plan's attention points and flows. Records written by in-host subagents are enough; the launcher is not required. The contract is [execution records](references/records.md#map).

1. Build. Run this skill's helper by its absolute path:

   ```bash
   python3 scripts/changemap.py build --environment <env> --work <work> --repo <checkout> --base <base> --head <head>
   ```

   It writes `work/<work>/map/map.json` and prints counts, a gap list and records that were never accepted. Read that output, never `map.json` or raw host output whole.

2. Fill only the gaps, in `work/<work>/map/supplement.json`, using the `supplement` definition of `schema/map.v1.json`. Read only what each gap names: a card for an unassigned file; evidence or tests for an unevidenced id; a corrected symbol for an unresolved anchor, with `replaces` naming the old one; a group for every card above 40 cards; an authored edge for an isolated card when a real relation exists. An unreported id belongs first to the front that owned it; fill it from the code only when you can establish the evidence yourself, and otherwise report it as `open` with its residual. Every statement comes from code or tests you read; never invent evidence to clear a gap.

3. Rebuild until `errors` is 0. Warnings may stay when they are true. Filling costs tokens in proportion to the gaps: a few cards and anchors are cheap, while attention evidence needs reading the code that proves it. A work without records turns the whole change into gaps; in that case report the expected cost before filling a large diff, since post-hoc explanation of about 80 files took millions of input tokens.

4. View. `python3 scripts/changemap.py view --environment <env> --work <work> --viewer <harness checkout>/apps/viewer` starts a local viewer instance on the map folder and returns its URL, or prints the command when the viewer location is unknown or its dependencies are not installed. `HARNESS_VIEWER` can name the viewer instead of `--viewer`. Installing the viewer's dependencies is reported, not done without a request. Each work gets its own instance; stop it with the printed command when done.

Deliver the map path, the counts, any remaining warnings and the viewer URL or command. The map is a retained deliverable when the work closes. Building a map authorizes no commits, comments or publication.
