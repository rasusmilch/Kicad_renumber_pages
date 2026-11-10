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
- **Page assignment:** root schematic is page `1`, then consecutively assign `2..N` without gaps or preserving old assignments. Empty but instantiated sheets count as pages.
- **Traversal:** depth-first pre-order; process each entire descendant subtree before the next sibling subtree.
- **Scope:** renumber the complete hierarchy of the selected project, not an individual subtree. Ignore unreferenced `.kicad_sch` files outside the hierarchy; fail rather than quietly omit missing required referenced files. Shared source sheets are represented by each distinct instance path, not by source filename.
- **Still Open:** the precise error/write/integrity guarantees and KiCad/Python version baselines. These must not be inferred from the selected sorting policy.

## Selected architecture and workflow — Round 2 (2026-11-10)
- **Interface:** standalone Python command-line utility, without KiCad GUI/plugin integration for the MVP.
- **Project entry point:** require the user to supply a specific existing `.kicad_pro` file. Read the project's schematic metadata to identify the schematic; do not search the directory and choose a root by guesswork. This project file is read-only for page renumbering.
- **Root admissibility:** accept exactly one positively identified top-level schematic root. KiCad 10 supports multiple independent top-level sheets; projects declaring multiple roots are valid KiCad projects but **unsupported by this MVP**. Missing, conflicting, or ambiguous metadata also blocks mutation rather than triggering silent selection. Actual version-specific encoding remains for the read-only plan to confirm.
- **Execution:** the default command only discovers, validates, calculates, and prints a proposed numbering plan; it performs no writes. Only an explicit `--apply` can authorize writes, subject to the separate safety policy still to be selected.
- **Plan reuse:** preview and apply use one deterministic numbering-plan computation. Apply re-reads and validates the current source; apply must not act on a stale in-memory result. Controls for source changes between separate preview and apply invocations remain Round 3.
- **Reporting:** human-readable terminal output showing project/root, complete intended ordering, old-to-new page numbers, affected files, change/no-op summary, and actionable diagnostic errors. No JSON, CSV, or additional persistent reporting format for MVP.
- **Portability direction:** intended for Kubuntu and Windows; exact Python/KiCad version support and platform-specific validations remain Round 4.

The following are **engineering recommendations awaiting adjudication**, not approved implementation policy: structured KiCad S-expression parsing, transactional updates, recoverable backups, and semantic preservation verification using netlist or equivalent checks.

## Protected properties to specify before execution
A safe design should establish a precise allowable-change set and detect violations. Candidate protected properties include schematic sheet UUIDs, instance UUID paths, source file associations, component references, symbol/net connectivity, all non-page-number S-expressions, and KiCad readability. The **exact validation contract and what constitutes an acceptable KiCad automatic rewrite are Open**.

Do not silently treat editing a shared source sheet as a single instance; each instance may have independently stored page information.

## Open product decisions — user/ChatGPT adjudication required
- **Write protection and preview/apply integrity:** files allowed to change, detection of unsaved editor sessions, source changes after preview, backup/restore requirements, atomicity limits, failure recovery, and handling an already clean project.
- **Compatibility:** exact Python and KiCad version baseline, dependency policy, and platform-specific behavior for Kubuntu/Windows.
- **Error policy:** invalid or duplicate UUIDs, unresolved sheet references, hierarchy cycles, shared-file ambiguity, broken page mappings, malformed or newer schematic syntax, unexpected instance coverage, and conflicts with external changes.
- **Verification:** pre/post comparisons, KiCad CLI availability, exported netlist equivalence, ERC relevance, fixtures, and how to establish that a page change did not alter circuit behavior.
- **PDF/export integration:** separately deferred until requested and adjudicated.

A safe plan may investigate and recommend the above, but **must not make these durable decisions on its own**.

## Non-goals / scope boundary
There is no approval to: flatten schematic hierarchy, eliminate repeated circuit pages, edit circuit connectivity, reannotate components, create CAD design blocks, modify PCB layouts, convert old KiCad formats, publish PDFs, or automatically reorganize schematic sheets. Any such capability requires a separately reviewed design decision.

## Evidence and limitations
- The GitHub repository was initialized empty; it contains governance documents only.
- The approximately 84-page AFC case is an observed motivating example, not a frozen test fixture or a claim that its current exact page numbering has been independently revalidated here.
- No working script, plugin, parser, package, test command, or KiCad verification result yet exists.
