# Develop a modular workflow

The main coordinator starts from a detailed macro plan with coherent module responsibilities, dependencies, interfaces, and observable acceptance criteria. Configure the workflow graph and profiles for that plan; do not infer an unlimited team.

The module coordinator understands the assigned module and prepares the technical micro plan. Inspect the relevant code and constraints, identify meaningful implementation steps and tests, and record only the context needed for execution. Preserve valid planning across iterations.

Delegate a bounded brief to a configured worker with `run decide --event delegate`. Grant required record references explicitly with `--context`; generated plans should live in the coordinator's assigned work artifacts. After delegation, yield the turn so the runtime can execute the worker and return its result.

The worker implements the assigned behavior according to the application's conventions and runs proportionate checks. It returns useful evidence and remaining issues; it does not accept its own work.

The coordinator inspects the result and checks the module contract. Request a justified correction with `request_changes`, carrying forward valid work and only the changed requirements. Accept with a concise evidence-based reason when the contract holds. Stop with an honest unresolved result if the configured limits are exhausted.

The integration coordinator evaluates cross-module behavior and shared contracts after local acceptance. It owns final acceptance. Tests are part of implementation and verification; neither every passing test nor every accepted branch proves integration by itself.

If integration reveals a defect, use `request_changes --to MODULE_COORDINATOR_ID` to return a focused correction to the responsible accepted module, then yield. The existing execution budgets and worker rounds still apply. Accept only after the corrected modules and any assigned helpers have completed their contracts.
