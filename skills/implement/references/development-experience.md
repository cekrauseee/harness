# Development experience

Aim for a development entry command that prepares the environment and starts the application predictably. Check the dependencies, configuration, generated assets, and local services actually required by this application.

Preparation should be idempotent and preserve existing user configuration and data. Diagnose what is missing before changing it. Make failure actionable: identify the failed prerequisite or operation and the next useful action.

Use concise English status phrases and a small consistent set of state indicators. Summarize routine operations; make raw diagnostics available when troubleshooting needs them. Support redirected output and avoid relying on color alone. Do not hide a failed command behind an optimistic ready message.

Fit the project's existing tooling. The goal is a dependable entry point, not an additional infrastructure framework.
