# Develop a modular workflow

Use native agent tools whenever they can meet the assignment, following the orchestration skill's mechanism decision. A modular graph does not itself require managed execution. These responsibilities apply to either mechanism; the `run decide` commands and transitions below apply only to an eligible Harness-managed graph.

The main coordinator starts from a detailed macro plan with coherent module responsibilities, dependencies, interfaces, and observable acceptance criteria. Define the graph and choose the provider, model, and effort for each assignment using the model-selection guidance; do not infer an unlimited team.

The module coordinator owns the module's execution, local decisions, worker follow-up, and acceptance within the agreed contract. It understands the assigned module and prepares the technical micro plan. Inspect the relevant code and constraints, identify meaningful implementation steps and tests, and record only the context needed for execution. Preserve valid planning across iterations. Escalate only the specific issue outside the assignment's scope, authority, or capabilities; retain responsibility for the module.

Delegate a bounded brief to a worker. In a managed graph, use `run decide --event delegate` for a configured worker and grant required record references explicitly with `--context`; generated plans should live in the coordinator's assigned work artifacts. Yield according to the chosen mechanism so it can execute the worker and return its result.

The worker implements the assigned behavior according to the application's conventions and runs proportionate checks. It returns useful evidence and remaining issues; it does not accept its own work.

The coordinator inspects the result and checks the module contract. Request a justified correction through the chosen mechanism's follow-up tools, carrying forward valid work and only the changed requirements; managed graphs use `request_changes`. Accept with a concise evidence-based reason when the contract holds. Stop with an honest unresolved result if the configured limits are exhausted.

The integration coordinator evaluates cross-module behavior and shared contracts after local acceptance. It owns final acceptance. Tests are part of implementation and verification; neither every passing test nor every accepted branch proves integration by itself.

If integration reveals a defect, return a focused correction to the responsible module coordinator. Ancestors and integration reviewers must not bypass it to direct workers or implement the module's correction themselves. In a managed graph, use `request_changes --to MODULE_COORDINATOR_ID` to reopen the accepted module, then yield. The existing execution budgets and worker rounds still apply. Accept only after the corrected modules and any assigned helpers have completed their contracts.
