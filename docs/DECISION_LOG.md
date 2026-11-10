# Decision history

This file is historical decision/provenance evidence, **not** the authority for current intended behavior. See [REQUIREMENTS.md](REQUIREMENTS.md), [ROADMAP.md](ROADMAP.md), and [README.md](../README.md) for current direction. The decision status and provenance are separate; editing this file does not make the editor the decision maker.

## Current summary
User-selected: build a maintainable KiCad hierarchical page renumbering utility with built-in checks and preserve the electrical design. Round 1 selects natural name-sorted depth-first parent-first numbering, continuous root-first pages including instantiated empty sheets, and complete-project scope. Round 2 selects an explicit .kicad_pro entry point, one root only, standalone Python CLI, default read-only preview with explicit --apply, and terminal-only reporting. User and ChatGPT make product and architecture decisions; Codex implements approved tasks. Supported version baselines, file-write/recovery rules, and detailed verification remain **Open**.

## History

### 2026-11-10 — Round 2 architecture and operator workflow approved
- **Status:** current
- **Provenance:** explicit user selections in Round 2, with ChatGPT engineering adjudication of root discovery, preview/apply planner consistency, and unsupported-state behavior.
- **Decision:** standalone Python CLI; explicitly supplied `.kicad_pro` entry point; reject multi-root/ambiguous-root projects in the MVP; read-only preview by default and opt-in `--apply`; only human-readable terminal reporting.
- **Implementation constraints:** use one plan-calculation implementation for preview/apply; reload source on apply; do not modify the `.kicad_pro`; fail closed for root ambiguity; no database, config, or machine-readable reports in the MVP. Exact parsing and persistence mechanisms are still Open.
- **Authority:** [REQUIREMENTS.md](REQUIREMENTS.md).
- **Still Open:** file-modification safety, crash recovery, platform/version support, and validation contract.


### 2026-11-10 — Round 1 numbering behavior approved
- **Status:** current
- **Provenance:** explicit user selections in the project's Round 1 interview. The secondary comparison details are ChatGPT engineering adjudication consistent with those selections, not an additional explicit user selection.
- **Decision:** natural alphabetical and numeric-aware sibling ordering at all hierarchy levels; depth-first, parent-first traversal; continuous page numbers beginning with root=1; include instantiated empty sheets; whole-project operation only. Case-insensitive numeric-aware normalization and deterministic tie-breaking are the specified implementation comparison behavior, without treating old page numbers or positions as sort inputs.
- **Authority:** [REQUIREMENTS.md](REQUIREMENTS.md).
- **Open boundary:** project selection, multiple top-level sheets, file-write safety, and the verification contract remain to be adjudicated.

### 2026-11-09 — Hierarchical numbering goal
- **Status:** current
- **Provenance:** explicit user request in project conversation.
- **Decision:** renumber schematics so parent sheets are followed by their nested descendants rather than retaining scattered numbers resulting from hierarchy edits. Built-in checks are required.
- **Authority:** [REQUIREMENTS.md](REQUIREMENTS.md).
- **Boundary:** the user's request does not itself select sibling ordering or file-edit implementation mechanisms.

### 2026-11-09 — Implementation delegation and approval boundary
- **Status:** current
- **Provenance:** explicit user directive accompanying new repository creation.
- **Decision:** user supplies desired behavior; ChatGPT interviews as necessary, selects/adjudicates architecture and behavior with the user, and creates executable Codex tasks; Codex does not decide product behavior or architecture.
- **Authority:** [AGENTS.md](../AGENTS.md).

### 2026-11-09 — Initial implementation form and safety mechanisms
- **Status:** proposal
- **Provenance:** prior ChatGPT engineering recommendation, **not confirmed by user**.
- **Original proposal:** standalone Python command-line program, parsed S-expression editing, dry-run, explicit apply, backups/rollback, and semantic verification; optional reuse across projects.
- **Later decision:** user selected the standalone CLI and preview/apply boundary in Round 2. A structured parser, backups/rollback and semantic checks remain unselected proposals.
- **Authority:** [REQUIREMENTS.md](REQUIREMENTS.md). This history is not implementation authorization.

### 2026-11-09 — PDF export as separate workstream
- **Status:** current
- **Provenance:** user requested a renumberer and separately discussed unwieldy KiCad PDFs; ChatGPT recommended separating PDF publication from the numbering MVP.
- **Decision:** no PDF implementation is authorized by the current renumbering scope. Any later addition requires explicit selection.
- **Authority:** [REQUIREMENTS.md](REQUIREMENTS.md).
