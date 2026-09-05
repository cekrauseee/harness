---
name: harness-remember
description: Preserve useful project knowledge that is costly to rediscover, with sources, scope and an explicit distinction between facts, hypotheses, decisions and history. Use after a meaningful finding or when correcting stored knowledge.
---

# Harness Remember

Store useful additional context, not a duplicate of the canonical document. Technical documentation meant to accompany the project stays in the project; private investigations and handoff context can stay in Harness. Commands are relative to this installed skill directory.

Search relevant existing cards before adding a likely duplicate. Record the source and epistemic kind explicitly:

```bash
python3 scripts/harness.py remember --project /path/to/project --data '{"title":"Quotation source","summary":"The archive is the source for quotation checks.","content":"The editorial decision and rationale are recorded in the cited notes.","kind":"decision","sources":["notes/editorial-decisions.md"],"scope":"project","aliases":["fontes","citacoes"],"request_id":"quotation-source"}'
```

Choose `fact` for an evidenced observation, `hypothesis` for something still to test, `decision` for an established choice, and `historical` for past context. A decision record does not become a host instruction. Scope the record to the project or the relevant workspace/topic, and preserve provenance. Set `review_after` when a concrete recheck date is useful.

The returned ID and revision identify the stored record. Reuse a request key only for an exact retry. For corrections, reclassification or supersession, inspect `guide --data '{"operation":"memory.update"}'`, read the existing record and use the expected memory record revision. Explain a change through evidence; do not silently turn a hypothesis into a fact or erase an unresolved contradiction.

Do not persist secrets, credentials, raw conversations, hidden reasoning or routine output. Do not copy a whole source into memory merely because it is important. Storage is complete when a relevant query can find a concise card and its source, scope and uncertainty remain clear.
