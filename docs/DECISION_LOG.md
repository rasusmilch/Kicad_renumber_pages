# Decision history

This file is historical decision/provenance evidence, **not** the authority for current intended behavior. See [REQUIREMENTS.md](REQUIREMENTS.md), [ROADMAP.md](ROADMAP.md), and [README.md](../README.md) for current direction. The decision status and provenance are separate; editing this file does not make the editor the decision maker.

## Current summary
User-selected: build a maintainable KiCad hierarchical page renumbering utility with built-in checks and preserve the electrical design. Round 1 now selects natural name-sorted depth-first parent-first numbering, a continuous sequence from root page 1 including instantiated empty sheets, and complete-project scope. User and ChatGPT make product and architecture decisions; Codex implements approved tasks. Interface, multi-top-level handling, supported versions, and error/write policies remain **Open**.

## History

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
- **Proposal:** standalone Python command-line program, parsed S-expression editing, dry-run, explicit apply, backups/rollback, and semantic verification; optional reuse across projects.
- **Authority:** pending user/ChatGPT adjudication under [REQUIREMENTS.md](REQUIREMENTS.md). No implementation is authorized by this entry.

### 2026-11-09 — PDF export as separate workstream
- **Status:** current
- **Provenance:** user requested a renumberer and separately discussed unwieldy KiCad PDFs; ChatGPT recommended separating PDF publication from the numbering MVP.
- **Decision:** no PDF implementation is authorized by the current renumbering scope. Any later addition requires explicit selection.
- **Authority:** [REQUIREMENTS.md](REQUIREMENTS.md).
