---
name: workflows-integrate
description: Merge, rebase or resolve Git conflicts within authorized integration work, preserving both lines of intent.
---

# Integrate

Use this process when integration is requested or necessary within an explicitly authorized integration scope. Do not add merge or rebase to ordinary implementation by default. Establish source, destination, base and intended resulting behavior before changing history or the checkout.

Inspect relevant local changes and branch state. Preserve unrelated work and maintain a recoverable starting point through native Git references when needed; do not discard changes to obtain a clean checkout. Respect shared/published history and authorization for rewriting or force-pushing. Integration does not imply remote merge or publication.

For conflicts, understand the intent of both lines of work from the relevant changes and requirements. Preserve both where compatible; resolve overlapping behavior against the intended result. Never choose ours/theirs across conflicts simply to complete the operation. Generated files should follow their maintained sources and generators.

Check the resulting change for omitted behavior and unresolved conflicts, and perform the project's verification appropriate to the integrated result. Reuse existing evidence that remains valid. Marker removal alone does not establish a correct integration. If the two intentions are incompatible and the request does not determine the choice, preserve a recoverable state and ask about that specific decision.

Deliver the integrated reference or local result, the meaningful resolution choices, verification and any unresolved limitation. Report interruption or failure honestly; do not silently abort, overwrite or drop one side's work to claim completion.
