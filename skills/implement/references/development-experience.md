# Development experience

Treat development experience and local/remote CI as acceptance criteria for application and feature delivery. Assess existing setup as well as prerequisites affected by the change; preserve what already meets the requirements and address gaps. Aim for a development entry command that prepares the environment and starts the application predictably. Check the dependencies, configuration, generated assets, and services actually required by this application.

Preparation should be idempotent and preserve existing user configuration and data. Diagnose what is missing before changing it. Make failure actionable: identify the failed prerequisite or operation and the next useful action.

Start project-managed local services through the established tooling and check that required services are ready for use. For externally managed services, validate the required configuration, access, and availability. Distinguish a started process from a usable dependency before reporting that the application is ready.

Use concise English status phrases and a small consistent set of state indicators. Summarize routine operations; make raw diagnostics available when troubleshooting needs them. Support redirected output and avoid relying on color alone. Do not hide a failed command behind an optimistic ready message.

Provide a documented local verification command and have remote CI invoke the same project checks. Use the project's CI platform and align tool versions, configuration, and service prerequisites across local and remote execution. Cover formatting checks, lint, applicable type checks, and tests. Verification should report failures without rewriting source files.

Use maintained, idiomatic formatter and linter presets with minimal customization. Choose readable, consistent defaults for new projects and preserve established conventions. Check for unused variables and deprecated API usage where supported. Require zero lint warnings for acceptance and resolve diagnostics rather than hiding them to obtain a pass.

Verify the affected preparation and startup path from a representative initial state, including service readiness and useful diagnostics when a prerequisite is missing or unavailable. Check that repeating preparation or restarting preserves existing configuration and data. Keep verification proportional to the change and report any part that could not be exercised.

Fit the project's existing tooling. The goal is a dependable entry point, not an additional infrastructure framework.
