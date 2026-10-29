---
name: document
description: Maintain canonical product documentation with clear ownership and a hierarchical structure.
---

# Document

Product documentation explains the code's supported behavior, contracts, configuration, and use. Treat it as a maintained source of truth: verify claims against the intended contract and implementation, and resolve discrepancies rather than documenting an accidental defect as intended behavior.

Write in English. Organize hierarchically by ownership and responsibility. In a monorepo, each application or package owns its documentation; the root contains shared context and cross-application contracts. Link focused pages rather than duplicating complete explanations.

Add material when it helps a future reader understand or use the product. Keep headings, examples, terminology, and formatting consistent. Update affected examples and references when behavior changes. Avoid generic tutorials, placeholder sections, and documents whose only purpose is to recount development.

Plans, execution logs, internal task names, review conversations, and orchestration details belong in Harness work records. They are not versioned product documentation. A useful synthesis can clarify an existing document, but it must preserve the document's authority, evidence, and ownership.
