# Recall selection

Recall uses lowercase alphanumeric terms from the query. Entries with no overlap are omitted when the query is non-empty. Active sessions receive a small score bonus so immediate handoffs sort ahead of equally relevant durable memories.

The budget is an estimate of four characters per token. Harness never claims exact tokenizer parity. Entries that do not fit are skipped rather than truncated, which keeps every returned memory attributable and intact.

Candidates are excluded because they have not been classified. Archived and superseded items are excluded because they are not current knowledge.
