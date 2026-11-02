# Review a modular workflow

Choose native or managed execution using the orchestration skill. These responsibilities apply to either mechanism. Use native agent tools for a native review; the named runtime transitions below apply only to a Harness-managed graph.

Partition the implemented feature into important, clearly identifiable responsibilities. Avoid fragmentation created only to increase the number of agents. The review partition may differ from the development modules.

The module coordinator defines the review focus, relevant contracts, code boundaries, and evidence required for acceptance. Give the worker enough context for a detailed investigation without loading unrelated history.

The worker reviews the assigned part deeply, identifies supported defects, and applies authorized patches. It verifies affected behavior and returns findings, corrections, evidence, and unresolved concerns in useful prose. Tests are a review stage, selected by criticality and observable behavior.

In a managed graph, use `delegate` for the initial assignment and `request_changes` for a justified follow-up. The coordinator evaluates the patch and its evidence, preserving valid work between iterations. Wait or yield according to the chosen mechanism; avoid busy polling or a new micro plan for every correction.

Accept the module only when its criteria hold. The integration coordinator examines effects across reviewed boundaries and owns the final decision. A clean local review does not automatically settle shared interfaces or combined behavior.

Return integration defects to the responsible module. In a managed graph, use `request_changes --to MODULE_COORDINATOR_ID` to reopen an accepted module, then yield. Keep the correction within the original scope and remaining limits; do not reset the review or its accumulated worker rounds. Final acceptance requires all module and helper work to be resolved.

Respect the selected models and effort, context grants, rounds, deadline, and shared attempt allowance. If those limits prevent resolution, preserve the actionable remainder and stop rather than silently escalating cost.
