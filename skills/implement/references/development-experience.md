# Development experience

Treat development experience as part of application and feature delivery when the change introduces or alters development prerequisites. Aim for a development entry command that prepares the environment and starts the application predictably. Check the dependencies, configuration, generated assets, and services actually required by this application.

Preparation should be idempotent and preserve existing user configuration and data. Diagnose what is missing before changing it. Make failure actionable: identify the failed prerequisite or operation and the next useful action.

Start project-managed local services through the established tooling and check that required services are ready for use. For externally managed services, validate the required configuration, access, and availability. Distinguish a started process from a usable dependency before reporting that the application is ready.

Use concise English status phrases and a small consistent set of state indicators. Summarize routine operations; make raw diagnostics available when troubleshooting needs them. Support redirected output and avoid relying on color alone. Do not hide a failed command behind an optimistic ready message.

Verify the affected preparation and startup path from a representative initial state, including service readiness and useful diagnostics when a prerequisite is missing or unavailable. Check that repeating preparation or restarting preserves existing configuration and data. Keep verification proportional to the change and report any part that could not be exercised.

Fit the project's existing tooling. The goal is a dependable entry point, not an additional infrastructure framework.
