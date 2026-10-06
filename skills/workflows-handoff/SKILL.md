---
name: workflows-handoff
description: Transfer or assume responsibility for ongoing work across agents or chats; a status report alone is not a handoff.
---

# Handoff

Handle a transfer of responsibility, either for the whole plan and coordination or for a specific deliverable. Start with the transferred scope and the intended recipient or recipient role. A result report or a context lookup alone is not a handoff.

For preparation, identify what the recipient is authorized to assume, its canonical entry point, relevant constraints, current continuation point and the next useful action. Reference the existing plan, module, front context and team configuration. When those files already carry everything necessary, send their pointers with the assignment; do not create a redundant handoff document. Persist additional necessary transfer information under `work/<work>/handoffs/<recipient-scope>.md`.

For reception, establish the authorized responsibility and read its scoped entry point. Compare execution facts with the relevant workspace or host when the saved context could be stale. Continue from that point without recreating the plan, re-surveying the project or automatically producing another recap. No new work ID or acceptance receipt is required. Update the receiving front's context when responsibility or continuation changes.

Historical permission notes do not independently authorize new actions. After a transfer is delivered or assumed, keep any retained handoff accurate about its remaining use; remove obsolete next-recipient instructions rather than presenting them as an active assignment. Preserve material needed by another pending consumer. This is maintenance of useful context, not a handoff history or receipt.

Read [file contracts](references/file-context.md) only when creating or restructuring transfer material. This skill includes `scripts/harness.py` for missing location and atomic Markdown updates.

Preparing a handoff does not itself authorize creating or messaging an agent. If the request includes delivery to an authorized destination, complete it using the host's supported tools. Respect named models and effort; do not silently substitute. Report the transfer prepared, delivered or assumed and any actual limitation.
