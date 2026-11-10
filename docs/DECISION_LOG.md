# Decision history

This file is historical decision/provenance evidence, **not** the authority for current intended behavior. See [REQUIREMENTS.md](REQUIREMENTS.md), [ROADMAP.md](ROADMAP.md), and [README.md](../README.md) for current direction. The decision status and provenance are separate; editing this file does not make the editor the decision maker.

## Current summary
User-selected: build a maintainable KiCad hierarchical page renumbering utility with built-in checks and preserve the electrical design. Round 1 selects natural name-sorted depth-first parent-first numbering, continuous root-first pages including instantiated empty sheets, and complete-project scope. Round 2 selects an explicit .kicad_pro entry point, standalone Python CLI, default read-only preview with explicit --apply, and terminal-only reporting; its initial one-root-only restriction was superseded by the user on November 10. All top-level schematic roots are now included, with natural ordering and continuous numbering. Round 3 selects mandatory timestamped backups, closed-editor apply, fail-closed input/change checks, no-op stability and proportional recovery. User and ChatGPT make product and architecture decisions; Codex implements approved tasks. Supported version baselines, detailed write/recovery implementation and semantic verification remain **Open**.

## History

### 2026-11-10 — Standing authorization for necessary development and test dependencies
- **Status:** current
- **Provenance:** explicit user instruction in response to Codex reporting that `pytest` was absent and package installation prohibited by the earlier task.
- **Decision:** Codex may install reasonably necessary development/test dependencies without repeated permission requests, including `pytest` in an isolated Python virtual environment and appropriate official OS/KiCad test tools in an isolated execution environment, with trusted sources, minimal scope, and transparent command/version/test receipts. This supersedes earlier task-level blanket no-install language.
- **Boundary:** no broad upgrades, changes to the user's system, untrusted install sources, invented runtime dependencies, or new product/architecture decisions. The code's approved standard-library runtime remains unchanged.
- **Current authority:** [AGENTS.md](../AGENTS.md), with testing guidance in [TESTING_STRATEGY.md](TESTING_STRATEGY.md).


### 2026-11-10 — User-authorized Codex GitHub refresh and task publication
- **Status:** current
- **Provenance:** explicit user directive after Codex encountered an outdated local checkout: Codex has internet access enabled, must pull current repository source, and must publish each completed task commit to GitHub.
- **Decision:** allow and require controlled remote Git inspection/fetch and fast-forward source preparation; implement on a named feature branch; after validated tracked execution, commit locally and push that commit to the same remote feature branch, then verify publication. Stop on conflicts, uncommitted work, missing authentication, or non-fast-forward conditions; no force push, reset, or unapproved merge. ChatGPT/user retain PR acceptance and merge authority.
- **Scope:** this repository only. This intentionally supersedes its earlier blanket no-network/no-push rule. The upstream `Codex_guide` remains unchanged and has a conflicting generic prepared-local policy; that guide-wide issue is not silently declared resolved by this local authorization.
- **Current authority:** [AGENTS.md](../AGENTS.md).


### 2026-11-10 — Post-planning format evidence and MVP implementation architecture
- **Status:** current
- **Provenance:** ChatGPT engineering review/adjudication of Codex's read-only plan, user-approved Round 1–3 behavior, current KiCad 10 AFC evidence, and published KiCad source/format evidence.
- **Decision:** implement a Python 3.11+ standalone CLI with a lossless S-expression page-span parser, instance-path-based multi-root DFS numbering, source verification, backup of each changed file, per-file staged replacement, minimal interruption marker, and conservative rollback. Keep foreign-project records unchanged. Repair valid old page-value strings, but reject ambiguous/missing page records. Reject external references/aliased source files for the MVP rather than copying or mutating unexpected paths.
- **Architecture authority:** [ARCHITECTURE.md](ARCHITECTURE.md).
- **Limits:** these are engineering mechanism adjudications, not claims of completed implementation or KiCad 10 test execution. The read-only preview implementation precedes separately reviewed write capability.


### 2026-11-10 — Multiple top-level sheets and Round 3 safety
- **Status:** current
- **Provenance:** explicit user revision of Round 2 and answers to Round 3; ChatGPT engineering adjudication of multi-root ordering and proportional recovery.
- **Decision:** support all top-level schematic roots declared by the project; treat them as natural-name-sorted siblings with depth-first subtree traversal and one continuous page sequence starting at the first actual sheet as page 1. No phantom root. Supersedes the single-root MVP restriction.
- **Safety:** require closed schematic editor for apply; mandatory verified backups under `backup-renumber/<local timestamp>/`; fail on invalid/changed inputs; perform no writes or backups when numbering is already correct. Favor simple rollback plus interrupted-operation detection over a complex transaction journal; power-loss recovery cannot be guaranteed by atomic individual-file replacement.
- **Authority:** [REQUIREMENTS.md](REQUIREMENTS.md).
- **Open:** parser implementation, precise recovery state mechanics, and validation/compatibility baselines.


### 2026-11-10 — Round 2 architecture and operator workflow approved
- **Status:** current
- **Provenance:** explicit user selections in Round 2, with ChatGPT engineering adjudication of root discovery, preview/apply planner consistency, and unsupported-state behavior.
- **Decision originally selected:** standalone Python CLI; explicitly supplied `.kicad_pro` entry point; reject multi-root/ambiguous-root projects in the MVP; read-only preview by default and opt-in `--apply`; only human-readable terminal reporting.
- **Later supersession:** the user explicitly replaced the multi-root rejection with support for multiple top-level sheets on 2026-11-10. See the later entry above.
- **Retained implementation constraints:** use one plan-calculation implementation for preview/apply; reload source on apply; do not modify the `.kicad_pro`; fail closed for root *identity* ambiguity; no database, config, or machine-readable reports in the MVP. Exact parsing and persistence mechanisms are still Open.
- **Authority:** [REQUIREMENTS.md](REQUIREMENTS.md).
- **Still Open:** implementation details for approved file-modification safety, platform/version support, and validation contract.


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
