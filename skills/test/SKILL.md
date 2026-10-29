---
name: test
description: Select and run proportionate behavioral tests for a software change or critical invariant.
---

# Test

Prefer tests of observable input and output at the meaningful boundary: for an API, the request, response, and relevant externally observable effects. Test the behavior consumers depend on rather than the internal arrangement that currently produces it.

Critical logic warrants deeper tests, including pure functions or internal invariants when those are the most reliable boundary. Critical frontend behavior may warrant automation; ordinary visual changes do not automatically need a permanent test suite.

Use a balanced TDD approach. Write a focused failing test first when it clarifies an important contract or reproduces a defect. Implement first when that better resolves uncertainty, then verify the meaningful behavior. Neither sequence is universal.

Use project-required checks and tests appropriate to the affected risk. After a fix, rerun the affected checks. Broaden testing when dependencies, failures, or unresolved concerns justify it. Avoid artificial coverage targets, trivial tests that mirror implementation, and repeated passing runs without a new reason.

Separate a product defect from an environment failure. Investigate repeated failures before retrying; obey execution limits and escalate missing prerequisites instead of looping indefinitely. Tests are stages of development and review, not a separate mandatory orchestration.

Report what the evidence demonstrates and any important gap. A passing command alone is not acceptance of an entire feature.
