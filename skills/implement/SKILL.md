---
name: implement
description: "Implement a change in a project: build or modify behavior, fix a bug, or apply review findings, using the project's conventions and the Harness environment for context. Use for coding work, including a module or front assigned from a plan."
---

# Implement

Start from the requested behavior or the concrete set of corrections. Use the context at hand and the project's conventions, investigate only the gaps that affect the change, and make routine implementation decisions yourself within the request.

A small correction with enough context needs no plan or work record. When unknown project constraints could affect the change, resolve the environment with `python3 scripts/harness.py resolve --project /path/to/project` (this skill's helper, by absolute path), read its README map and follow the applicable links. When assigned a module or front, begin with that entry and its dependencies rather than the whole team or all knowledge. On resumption, compare the workspace with the saved context and continue without a recap.

Plan first when the change needs it; finishing that planning returns to implementation under the same request. For review corrections, work from the existing findings and their version: fix, contest or report each as still pending, without repeating the review, and apply a supplied patch only after checking that it fits the current code. Preserve unrelated work and avoid incidental redesign; report pre-existing problems as follow-ups.

Own verification. Apply the user's testing policy and the project's requirements, deciding separately whether to run existing checks, write tests or exercise a flow. Reuse valid evidence and stop when the outcome is established; reopen for changed behavior, a failure or a concrete concern. A missing credential limits a live check: report it rather than creating credentials.

Code, comments and project documentation describe real concepts and behavior, never temporary module labels or orchestration details. Preserve decisions, investigation and continuation in the environment when losing the conversation would cost later work, even before any work record exists. When continuation context exists, update the front's `context.md` at a useful milestone with changed facts, evidence references and the next action; read [file contracts](references/file-context.md) only when creating that structure. Finishing a module does not close the work.

Deliver the implemented behavior, its verification and material limitations. Implementation does not imply commit, push, PR, merge, release or deployment; do those only when the request covers them.
