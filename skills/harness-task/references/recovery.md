# Contribution recovery

Use the installed skill's `scripts/harness.py` and the intended project selector. `status` returns contribution summaries; `status --owner <id>` returns one complete handoff. Match predecessor work by purpose, resources and remaining action. Check actual results and preserve unrelated records, including inactive work whose purpose is unclear.

A released contribution cannot reopen. Claim your own resources to continue writing. After carrying useful context forward or completing the predecessor's remaining work, remove its inactive record with `drop --owner <id> --expect <version>`. An inactive-record cleanup needs no new contribution solely for that removal; its observed version protects it. Scope project-wide consolidation with a reservation for `.` before shared project-file edits.

Use `finish` for your completed contribution after its outcome and any needed knowledge consolidation are settled. Reuse the existing task evidence. On interruption before completion, retain a current handoff. If you must release without writing one, `release --owner <id> --expect <version> --reason "..."` retains the existing handoff and records why ownership stopped.

An owner ID is a cooperative handle, not identity proof. Never release another writer from age or silence. Establish that writing stopped and record the reason with `release` before cleaning up an obsolete inactive record. Read-only requests authorize no cleanup.

After a failed or uncertain operation, inspect only the affected current state. A lost initial claim response requires locating the contribution before claiming again. Content conflicts require reconciliation. A failed finish before replacement leaves the contribution intact; a post-replacement durability failure may mean it is already gone. Verify the result and retry with the observed state. Exact retries are idempotent; no historical receipt is stored. Report unresolved cleanup instead of claiming completion.
