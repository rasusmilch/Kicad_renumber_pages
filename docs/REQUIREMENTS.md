# Product requirements and unresolved decisions

**Status:** Design discovery; no implemented product. This document contains selected intent, engineering constraints already expressed by the user, and **Open** decisions. A proposed option is not an approved contract.

## Purpose and users
The intended utility serves KiCad schematic authors managing large hierarchical designs with repeated sheet instances. The initiating use case is an approximately 84-page AFC Interface schematic with multiple nested and repeated channels. Editing sheets causes manual page numbers to become scattered.

The user wants **correct parent-first renumbering** with **built-in safeguards**. The utility is intended to be reusable, not a one-off modification of that AFC project.

## Selected user requirements
1. **Renumber hierarchical schematic pages** so a parent is followed by all of its nested descendants before proceeding to the next sibling subtree. This expresses a depth-first, parent-before-descendants goal, not a selected sibling tie-break rule.
2. **Support nested and repeated sheet instances.** Pages belong to schematic instances; the same source `.kicad_sch` may be instantiated multiple times. Renumbering by filename alone would be incorrect.
3. **Built-in checks are required.** There must be a way to establish the intended scope and detect problems, rather than blindly rewriting files.
4. **Preserve electrical design intent.** The operation is page renumbering, not a circuit edit, component reannotation, library modification, project conversion, or sheet restructuring.
5. **Design and behavioral authority remain with the user and ChatGPT.** Codex must not invent program behavior or an architecture to resolve open choices.
6. **Keep the initial product focused on numbering.** Producing, splitting, or reorganizing PDF exports is a distinct potential workstream, not part of the approved renumbering MVP.

The following are **engineering recommendations awaiting final design adjudication**, not unconditionally selected requirements: standalone Python CLI over an in-editor plugin; use of a structured KiCad S-expression parser; a read-only preview/dry-run and explicit application; transactional updates and recoverable backups; XML/netlist comparison or equivalent semantic verification; natural numeric channel sorting; deterministic functional section order.

## Protected properties to specify before execution
A safe design should establish a precise allowable-change set and detect violations. Candidate protected properties include schematic sheet UUIDs, instance UUID paths, source file associations, component references, symbol/net connectivity, all non-page-number S-expressions, and KiCad readability. The **exact validation contract and what constitutes an acceptable KiCad automatic rewrite are Open**.

Do not silently treat editing a shared source sheet as a single instance; each instance may have independently stored page information.

## Open product decisions — user/ChatGPT adjudication required
- **Sibling ordering:** physical placement on the parent sheet, explicit user-defined order, alphabetic, natural sort by sheet name, current hierarchy navigator order, or other policy. Determine how stable ordering is defined and what to do with equal names.
- **Numbering format and start:** sequential integer page numbers beginning at 1 versus custom formats, existing number preservation, section numbering, and treatment of gaps.
- **Scope:** whole project versus a selected subtree, exclusion and inclusion rules, and any treatment of missing / unused files.
- **Interface:** standalone CLI, plugin, GUI, or combination; supported Python and KiCad versions; portability requirements and dependency policy.
- **Preview and write authorization:** behavior of dry-run, explicit apply, files allowed to change, protection of unsaved editor sessions, backups, atomicity, failure rollback, and handling an already clean project.
- **Error policy:** invalid or duplicate UUIDs, unresolved sheet references, hierarchy cycles, shared-file ambiguity, broken page mappings, malformed or newer schematic syntax, unexpected instance coverage, and conflicts with external changes.
- **Verification:** pre/post comparisons, KiCad CLI availability, exported netlist equivalence, ERC relevance, fixtures, and how to establish that a page change did not alter circuit behavior.
- **Sorting and instance nuances:** natural channel numbering, tie-break rules, hierarchy ordering stability, and use of existing page numbers as an input.
- **PDF/export integration:** separately deferred until requested and adjudicated.

A safe plan may investigate and recommend the above, but **must not make these durable decisions on its own**.

## Non-goals / scope boundary
There is no approval to: flatten schematic hierarchy, eliminate repeated circuit pages, edit circuit connectivity, reannotate components, create CAD design blocks, modify PCB layouts, convert old KiCad formats, publish PDFs, or automatically reorganize schematic sheets. Any such capability requires a separately reviewed design decision.

## Evidence and limitations
- The GitHub repository was initialized empty; it contains governance documents only.
- The approximately 84-page AFC case is an observed motivating example, not a frozen test fixture or a claim that its current exact page numbering has been independently revalidated here.
- No working script, plugin, parser, package, test command, or KiCad verification result yet exists.
