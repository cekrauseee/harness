---
name: implement
description: Implement a requested software change using the application's conventions and relevant acceptance criteria.
---

# Implement

Understand the behavior to change and the relevant application boundaries. Follow the project's established architecture, naming, and design patterns. Make routine implementation choices within the request; surface a material conflict or scope change without abandoning independent authorized work.

Choose the simplest complete solution. Reuse suitable project code, platform features, and existing dependencies before adding new ones. Organize modules and components around cohesive responsibilities (SRP), and share logic that represents the same behavior (DRY). Let actual use justify abstractions, layers, and extension points. Judge simplicity by readability, correctness, and maintenance cost.

Keep scaffolds limited to current requirements: remove unused demo content, placeholders, and generated features together with their unused references and dependencies. Use current, idiomatic practices compatible with the project's supported technology versions; verify version-sensitive choices against official documentation.

Use the current plan when it helps. Make targeted changes, preserve unrelated user work, and keep internal work IDs, agent topology, plans, and debugging residue out of product code and remote-facing artifacts. Do not turn a local finding into an unrelated refactor.

Validate observable behavior according to the `test` skill and the risk of the change. Resolve failures caused by the requested work and rerun affected checks. Preserve useful execution context through Harness tools; promote durable knowledge separately through memory capture.

When creating an application, introducing or changing its development dependencies, services, or environment configuration, or working on development tooling, use [development experience](references/development-experience.md). Use `document` when product contracts or usage documentation need to change, and `git` when preparing commits or PRs.

Finish the requested deliverable, including its required integration and verification. Report the outcome, evidence, and material limitations in the user's language.
