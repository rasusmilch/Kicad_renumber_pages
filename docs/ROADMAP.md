# Current project roadmap

**Stage: planning reviewed; initial read-only implementation ready for an explicit Codex execute task.** No program exists yet. The safety-critical apply phase remains separately gated.

## 0 — Governance foundation
Record current intent, decision ownership, authority routes, commands (including verified absences), development safety constraints, provenance, and the difference between Selected, Open, and proposed requirements. This stage does not implement product behavior.

## 1 — Read-only discovery and design (completed with qualified review)
Codex completed a read-only plan, but its local environment contained KiCad 9 and an older governance snapshot. ChatGPT independently inspected current KiCad 10 schematic and project evidence, including a public upstream multi-root/shared-subsheet regression fixture. The approved MVP architecture and remaining validation boundary are specified in [ARCHITECTURE.md](ARCHITECTURE.md).

A refreshed prepared checkout containing the latest current-state authority is required for execute work. A historical planning receipt is evidence, not approval to invent behavior.

## 2 — MVP (approved design; implementation pending)
First implement and test the **read-only** parser, root/sheet instance graph, deterministic numbering plan, and terminal preview. Review the receipt and source. Then implement **apply** with mandatory verified timestamped backups, minimal interruption detection, rollback limits, and failure-injection tests. Follow semantic task boundaries, not an arbitrary number of files or prompts. No PDF generation or other workflow expansion.

## 3 — Stabilization
Adversarial validation of nested/reused sheet instances, malformed/unsupported input, consistency guards, accidental-write prevention, deterministic outputs, and failure recovery as required by the subsequently approved validation contract. Repair discovered flaws through focused work.

## 4 — Pilot
Run an explicitly approved operation on a disposable or version-controlled copy of a representative KiCad project. Compare intended page traversal and protected design information. Obtain a user review before any live-project write process.

## 5 — Expansion (not approved)
Optional GUI/KiCad plugin front end, alternate numbering policies, PDF export tools, broader version coverage, packaging, and CI. These are candidates only: require purpose, evidence, scope, and explicit approval before planning them.

## Stage transitions
- User/ChatGPT establish or update current authority before feature execution.
- Codex reports local evidence; ChatGPT independently reviews source and receipts.
- An integrated validation result is required before claiming ready for general use.
- A passing test suite does not by itself authorize a changed product contract or a live user-project mutation.
