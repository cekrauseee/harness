---
name: work
description: Create, reuse, or organize Harness work records for an ongoing purpose.
---

# Work

A work record preserves context that will be useful to continue a recognizable purpose. It can be small, iterative, or continuous. It does not require a plan, an agent tree, or a prescribed lifecycle.

Reuse a work record when the purpose and relevant decisions remain shared. Create one when continuity would otherwise be lost. Separate independent purposes or contexts that repeatedly interfere with one another; size, branches, PR count, and agent count alone do not justify splitting. A transient question may need no work record.

Use `work list`, `work show ID`, and `work create ID --title TITLE --purpose PURPOSE` with an explicit environment. Add plans, reviews, decisions, or handoffs only as needed through `record write`. Keep the current objective and useful state easy to find; link detailed records instead of repeating their contents.

A merge completes a delivery, not necessarily the work. Clean temporary delivery resources while preserving useful ongoing context. Archive through the tool when the record no longer needs to be active; do not manufacture a completion state for continuous work.

Use [record conventions](../../docs/records.md) for structure. The `plan`, `review`, and `handoff` skills cover those processes when they are actually needed.
