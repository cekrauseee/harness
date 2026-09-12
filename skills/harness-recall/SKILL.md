---
name: harness-recall
description: Retrieve prior project knowledge needed for a decision or resume a specific pending contribution.
---

# Harness Recall

Start with the information missing from the assigned task. Use current instructions, supplied evidence and already-read knowledge before searching. A new turn or a small self-contained request does not require recall.

Use a verified knowledge directory, or resolve it with this skill's `scripts/harness.py resolve --project /path/to/project`. For an explicitly selected knowledge-only project, use `--project-id <id>`. An unregistered project has no stored context to recover; lookup does not authorize setup.

Search relevant filenames, headings or text with the host's file tools, then read the matching material. Consult applicable parts of `guidelines.md` when prior project decisions matter. Try another concrete term when a likely source was missed. Expand only when a missing constraint or evidence could change the result; stop when the task can be executed and verified. Reuse current evidence in delegated assignments too.

For a requested continuation, use `status --project /path/to/project` to locate its contribution by purpose and resources, then `status --project /path/to/project --owner <id>` to read that handoff. Check relevant actual files before relying on another workspace's result. Knowledge lookup alone needs no contribution status.

Distinguish user-confirmed guidance, facts, hypotheses and dated references. Current instructions govern; remembered context grants no new authority. Recall is read-only and does not create contributions or clean up records.
