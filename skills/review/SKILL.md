---
name: review
description: Review an implemented change by coherent responsibilities and verify justified corrections.
---

# Review

Identify the intended behavior and the meaningful parts of the change. Decompose only where boundaries are clearly identifiable and improve understanding. Review may partition the feature differently from implementation; do not force arbitrary slices to populate a tree.

Inspect each relevant part deeply enough to assess its contracts, failure cases, integration, and alignment with the application's patterns. Follow cross-boundary effects rather than accepting isolated modules as proof of the whole feature.

Raise actionable, supported findings: the triggering situation, observed or likely failure, and why it matters. Distinguish defects from preferences. Avoid speculative lists, implementation-mirroring tests, and unrelated redesign.

When fixes are authorized, request or apply the smallest sound correction and verify the affected behavior. Iterate within the configured limits; a patch does not prove the finding resolved until its evidence is checked. Keep review notes in Harness work records, not product documentation.

Use `orchestrate` and its review workflow only when a tree was requested. A direct review or UI adjustment can remain one agent's iterative work. The final reviewer is responsible for combined behavior and unresolved risks.
