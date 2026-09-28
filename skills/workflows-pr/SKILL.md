---
name: workflows-pr
description: Draft, create or update a pull request describing the final macro change and expected behavior.
---

# Pull request

Match the requested result: text, remote creation or remote update. Establish the repository, base, head and complete proposed change from current evidence. A wording-only revision needs the relevant PR text and facts, not a new repository investigation. Local uncommitted changes are not part of a published PR.

Use an English title in Conventional Commits form, such as `feat(auth): add resource-level access control`, unless an explicit project convention differs. The type describes the macro change presented for review; its individual commits may have other types. Keep the branch semantically aligned, for example `feat/access-control`, without renaming it for ordinary title edits.

Write the description as human prose about the concrete problem, resulting behavior and relevant implications. Explain the final implementation to a reviewer without the chat history. Do not label paragraphs with commit prefixes or describe temporary agent modules, assignments or abandoned approaches. Scale detail to the change and follow the repository template. Include only verification actually performed and material limitations.

Before remote creation or update, confirm the intended target and current relevant remote state. Preserve actual newlines; use structured body arguments or a file for CLI descriptions. Publish only within existing authorization and verify the resulting content. Attach the PR to the chat when the host supports it.

Return the draft or PR link and material remaining limitations. Creating a feature does not authorize commit, push or PR by itself. A PR request does not authorize merge, release or deployment.
