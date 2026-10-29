---
name: plan
description: Plan a requested change at the macro or technical level appropriate to its executor.
---

# Plan

Start from the requested outcome, existing constraints, and evidence that would demonstrate completion. Preserve accepted decisions and distinguish assumptions from requirements. Investigate the parts whose uncertainty affects the plan; a small task does not need a repository-wide survey.

Choose detail for the consumer:

| Consumer | Useful plan |
| --- | --- |
| Main coordinator | Detailed macro modules: responsibility, boundaries, interfaces, dependencies, acceptance, and integration ownership. |
| Module coordinator | Technical micro work: relevant code, design choices, contracts, sequencing, critical risks, and proportionate validation. |
| Direct implementer | Only the steps and decisions necessary to execute the requested change. |

Decompose into coherent, identifiable responsibilities. Parallelize only where dependencies and ownership allow it. A module is not automatically one tiny task or one permanent agent. Explain meaningful tradeoffs without prescribing generic implementation recipes.

Store durable plans in the active work through Harness tools, outside the product repository. Link supporting evidence and keep the entry record short. Preserve valid parts of the plan between iterations; update only when requirements, evidence, or decisions change.

Planning does not itself authorize a workflow or an external action. When execution is already requested, carry the plan into that authorized work without asking again for routine steps.
