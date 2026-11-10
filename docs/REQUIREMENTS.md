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
- **Still Open:** how the project is selected, treatment of KiCad 10 multi-top-level projects, and the precise error/write/integrity guarantees. These must not be inferred from the selected sorting policy.

The following are **engineering recommendations awaiting final design adjudication**, not unconditionally selected requirements: standalone Python CLI over an in-editor plugin; use of a structured KiCad S-expression parser; a read-only preview/dry-run and explicit application; transactional updates and recoverable backups; XML/netlist comparison or equivalent semantic verification.

## Protected properties to specify before execution
A safe design should establish a precise allowable-change set and detect violations. Candidate protected properties include schematic sheet UUIDs, instance UUID paths, source file associations, component references, symbol/net connectivity, all non-page-number S-expressions, and KiCad readability. The **exact validation contract and what constitutes an acceptable KiCad automatic rewrite are Open**.

Do not silently treat editing a shared source sheet as a single instance; each instance may have independently stored page information.

## Open product decisions — user/ChatGPT adjudication required
- **Project selection / multi-top-level case:** what path identifies the selected project and how KiCad 10 projects with independent top-level schematic sheets are admitted or rejected.
- **Interface:** standalone CLI, plugin, GUI, or combination; supported Python and KiCad versions; portability requirements and dependency policy.
- **Preview and write authorization:** behavior of dry-run, explicit apply, files allowed to change, protection of unsaved editor sessions, backups, atomicity, failure rollback, and handling an already clean project.
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
