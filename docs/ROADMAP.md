# Current project roadmap

**Stage: governance/bootstrap and behavior adjudication.** No executable program exists and no feature implementation is authorized.

## 0 — Governance foundation
Record current intent, decision ownership, authority routes, commands (including verified absences), development safety constraints, provenance, and the difference between Selected, Open, and proposed requirements. This stage does not implement product behavior.

## 1 — Read-only discovery and design
The next substantive Codex task should be a **read-only plan** only after ChatGPT specifies its investigative questions. The plan should inspect real KiCad 10 sheet-instance encoding and reuse behavior, analyze failure cases, compare simple architectural alternatives, and propose behavior tests. It must clearly return unresolved product decisions for user/ChatGPT adjudication rather than silently selecting them.

ChatGPT and the user then explicitly approve a behavior specification and architecture. No execute task before that approval.

## 2 — MVP (conditional on approved design)
A focused minimal implementation of the approved renumberer, with the selected safety and preview/apply behavior. Follow semantic task boundaries, not an arbitrary number of files or prompts. No PDF generation or other workflow expansion.

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
