# Product requirements and unresolved decisions

**Status:** Design discovery; no implemented product. This document contains selected intent, engineering constraints already expressed by the user, and **Open** decisions. A proposed option is not an approved contract.

## Purpose and users
The intended utility serves KiCad schematic authors managing large hierarchical designs with repeated sheet instances. The initiating use case is an approximately 84-page AFC Interface schematic with multiple nested and repeated channels. Editing sheets causes manual page numbers to become scattered.

The user wants **correct parent-first renumbering** with **built-in safeguards**. The utility is intended to be reusable, not a one-off modification of that AFC project.

## Selected user requirements
1. **Renumber hierarchical schematic pages** with depth-first, parent-first traversal. Every parent is numbered immediately before its descendants; the complete subtree is numbered before the next sibling. See the selected Round 1 policy below.
2. **Support nested and repeated sheet instances.** Pages belong to schematic instances; the same source `.kicad_sch` may be instantiated multiple times. Renumbering by filename alone would be incorrect.
3. **Built-in checks are required.** There must be a way to establish the intended scope and detect problems, rather than blindly rewriting files.
4. **Preserve electrical design intent.** The operation is page renumbering, not a circuit edit, component reannotation, library modification, project conversion, or sheet restructuring.
5. **Design and behavioral authority remain with the user and ChatGPT.** Codex must not invent program behavior or an architecture to resolve open choices.
6. **Keep the initial product focused on numbering.** Producing, splitting, or reorganizing PDF exports is a distinct potential workstream, not part of the approved renumbering MVP.

## Selected numbering policy — Round 1 (2026-11-10)
- **Sibling order at every level:** natural, alphabetical, numeric-aware comparison of sheet-instance display names. This is independent of physical symbol location, existing page number, and file enumeration order.
- **Comparison details:** case-insensitive normalization followed by numeric comparison of digit runs (`Channel 2` before `Channel 10`); when normalized comparisons tie, compare original names and finally stable sheet-instance UUID identity to avoid nondeterminism. These are ChatGPT engineering tie-break specifications consistent with the user's selected sorting policy, not separately user-specified features.
- **Page assignment:** the first top-level schematic sheet is page `1`, then consecutively assign `2..N` without gaps or preserving old assignments, traversing each top-level subtree completely before the next. Empty but instantiated sheets count as pages. In a single-top-level project, its root remains page 1.
- **Traversal:** depth-first pre-order across a forest of one or more top-level sheets; natural name-sort top-level sheets as siblings, then process each entire descendant subtree before the next sibling subtree. Do not synthesize a numbered project root.
- **Scope:** renumber the complete hierarchy of the selected project, not an individual subtree. Ignore unreferenced `.kicad_sch` files outside the hierarchy; fail rather than quietly omit missing required referenced files. Shared source sheets are represented by each distinct instance path, not by source filename.
- **Still Open:** remaining detailed file/integrity guarantees, interrupted-run recovery verification, and KiCad/Python version baselines. These must not be inferred from the selected sorting policy.

## Selected architecture and workflow — Round 2 (2026-11-10)
- **Interface:** standalone Python command-line utility, without KiCad GUI/plugin integration for the MVP.
- **Project entry point:** require the user to supply a specific existing `.kicad_pro` file. Read the project's schematic metadata to identify the schematic; do not search the directory and choose a root by guesswork. This project file is read-only for page renumbering.
- **Root admissibility (superseded restriction):** accept **one or more** positively identified top-level schematic sheets from the project's `schematic.top_level_sheets` metadata. **All** roots belong to one whole-project ordering and continuous page-number sequence. Treat each top-level sheet as a sibling root; sort the roots by the same selected natural alphabetical order and traverse each subtree. Never add a synthetic numbered root. Missing, conflicting, duplicate, or ambiguous root metadata blocks mutation; do not guess. KiCad 10 format details and representation of page/instance records still require read-only validation.
- **Execution:** the default command only discovers, validates, calculates, and prints a proposed numbering plan; it performs no writes. Only an explicit `--apply` can authorize writes, subject to the separate safety policy still to be selected.
- **Plan reuse:** preview and apply use one deterministic numbering-plan computation. Apply re-reads and validates the current source; apply must not act on a stale in-memory result. Controls for source changes between separate preview and apply invocations remain Round 3.
- **Reporting:** human-readable terminal output showing project/root, complete intended ordering, old-to-new page numbers, affected files, change/no-op summary, and actionable diagnostic errors. No JSON, CSV, or additional persistent reporting format for MVP.
- **Portability direction:** intended for Kubuntu and Windows; exact Python/KiCad version support and platform-specific validations remain Round 4.

## Selected modification safety — Round 3 (2026-11-10)
- **Editor state:** the KiCad schematic editor must be closed before `--apply`. Check for detectable project/editor lock indicators, reject detected conflicts, and warn that lock checks cannot prove that all unsaved editor sessions are closed. Preview remains read-only.
- **Mandatory backup:** on an operation that will change page values, first save and verify complete original copies of **every affected schematic file**, preserving their relative paths, under `<project-directory>/backup-renumber/YYYY-MM-DD_HH-MM-SS/` (local timestamp; choose a unique directory without overwriting older backups). No user-facing backup-disable flag for MVP.
- **Write and consistency checks:** validate all referenced schematic inputs and instance paths before any edit. Reject malformed, unsupported, missing, structurally inconsistent, or ambiguously resolved data. Read/check all inputs against the plan and recheck on apply; abort rather than overwrite concurrently modified files. Valid but scattered/duplicated old page numbers may be renumbered as intended, provided instance mapping is unambiguous.
- **Minimal recovery:** prefer verified backups, staged temporary replacements, and best-effort automatic rollback when a detectable write error occurs. Because multi-file writes are not intrinsically atomic, provide a simple interruption indicator and clear recovery guidance; never claim guaranteed automatic recovery after power loss. A complex transaction journal, automatic cross-process resumption, or a database is **not selected**. Additional recovery machinery requires evidence that the simpler approach cannot meet this requirement.
- **Already correct:** if the numbering plan yields no changes, report a no-op; create no backups, rewrite no files, and avoid incidental timestamp changes.

**Approved technical architecture and format contract:** see [ARCHITECTURE.md](ARCHITECTURE.md). Use structured lossless KiCad S-expression parsing, byte-span-only page edits, the approved source/backup/restore sequence, and whole-graph verification. These are ChatGPT's post-planning engineering adjudications of implementation mechanisms, not independent user-specified functionality. KiCad 10 installation-based validation remains required before a production-use claim.

## Protected properties to specify before execution
A safe design should establish a precise allowable-change set and detect violations. Candidate protected properties include schematic sheet UUIDs, instance UUID paths, source file associations, component references, symbol/net connectivity, all non-page-number S-expressions, and KiCad readability. The **exact validation contract and what constitutes an acceptable KiCad automatic rewrite are Open**.

Do not silently treat editing a shared source sheet as a single instance; each instance may have independently stored page information.

## Open product decisions — user/ChatGPT adjudication required
- **Write implementation detail:** defined in [ARCHITECTURE.md](ARCHITECTURE.md) as targeted page-value spans, staged replacements and simple interrupted-operation marker; more elaborate recovery behavior is not approved.
- **Compatibility evidence:** MVP targets observed KiCad 10 format 20260306 and Python 3.11+ with standard-library runtime. Kubuntu/Windows support must be tested rather than assumed; unsupported format/migration cases fail without writing.
- **Error policy:** strict fail-closed rules and tolerated repairable page values are selected in [ARCHITECTURE.md](ARCHITECTURE.md). Unsupported or ambiguous source must not be modified.
- **Verification:** pre/post comparisons, KiCad CLI availability, exported netlist equivalence, ERC relevance, fixtures, and how to establish that a page change did not alter circuit behavior.
- **PDF/export integration:** separately deferred until requested and adjudicated.

A safe plan may investigate and recommend the above, but **must not make these durable decisions on its own**.

## Non-goals / scope boundary
There is no approval to: flatten schematic hierarchy, eliminate repeated circuit pages, edit circuit connectivity, reannotate components, create CAD design blocks, modify PCB layouts, convert old KiCad formats, publish PDFs, or automatically reorganize schematic sheets. Any such capability requires a separately reviewed design decision.

## Evidence and limitations
- The GitHub repository was initialized empty; it contains governance documents only.
- The approximately 84-page AFC case is an observed motivating example, not a frozen test fixture or a claim that its current exact page numbering has been independently revalidated here.
- No working script, plugin, parser, package, test command, or KiCad verification result yet exists.
