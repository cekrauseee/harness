---
name: close-work
description: "Close a completed work item in the Harness environment: consolidate durable knowledge, preserve retained outputs and move work/<name> to the environment trash. Use when the user says the work is done and asks to close or clean it up."
disable-model-invocation: true
---

# Close work

Close the temporary context of a work item whose whole objective is complete, on the user's request. Finishing one module, one review round or one agent's part does not complete the work, and a pending handoff or an active front keeps it open.

1. Inspect. `python3 scripts/harness.py inspect-work --environment /path/to/environment --work <name>` lists every file and a hash of the tree. Open non-Markdown outputs as well.
2. Preserve. Consolidate confirmed durable knowledge into `knowledge/<subject>.md` when it is not already canonical there. Move or copy each retained deliverable, including original HTML or other outputs that cannot be regenerated, to a durable destination outside the work tree, verify the copy and update the references its consumers use. Resolve pending consumers, or leave the work open and report the specific blocker.
3. Close. Take a fresh hash after step 2 and run `python3 scripts/harness.py close-work --environment /path/to/environment --work <name> --expect <sha256>`. The helper moves `work/<name>/` to `<environment>/trash/<name>-<timestamp>/` in one atomic rename; the user purges the trash manually. A `document_conflict` means the tree changed: inspect again instead of forcing.

Run the helper by its absolute path inside this skill's directory. It lists and hashes all file types, but its document commands accept Markdown only; use ordinary file tools for other outputs. It cannot judge whether a handoff was consumed, a front finished or an output is worth keeping.

Report what was consolidated, where deliverables went and the trash path. Worktree removal, branch deletion, commits, publication and chat archival are separate requests.
