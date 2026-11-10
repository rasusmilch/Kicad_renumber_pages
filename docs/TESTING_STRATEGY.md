# Validation strategy

**Current evidence:** governance-only repository; no program, tests, test runner, CI, or KiCad-dependent validation commands exist or have been run. The requirements and architecture now select a testable design, but this document does **not** claim tests have passed or that KiCad 10 has been run.

## Risk to establish confidence against
Renumbering must not change circuit semantics, misnumber shared/repeated instances, silently skip sheets, partially write files, or claim safety when unsupported syntax or an ambiguous hierarchy prevents confidence.

## Proposed validation layers (subject to product/architecture adjudication)
1. **Model/traversal behavior:** single sheet; nested multiple levels; repeated source files via distinct instance paths; empty sheets; natural numeric names; ties; reordered siblings; existing duplicate/gapped page numbers; idempotent reruns. Expected order must follow the *approved* ordering policy rather than tests inventing it.
2. **Read and parse integrity:** malformed S-expressions; missing referenced source; duplicate or invalid UUID/path; cycles; unsupported/newer KiCad version; ambiguous path coverage. Exact fail-closed rules depend on approved requirements.
3. **Write safety:** dry-run does not change bytes; explicit apply modifies only allowed fields; partially failed write does not leave an invalid mix; backups and recovery work to the approved level; externally modified inputs are detected; multiple runs are deterministic.
4. **Semantic preservation:** compare the complete pre/post instance graph and all protected schematic content; review actual changed expressions and Git diffs. Netlist equivalence and headless KiCad load checks should be evaluated for their actual ability to detect unintended circuit changes; ERC alone is not proof of preservation.
5. **Integration/pilot:** run against disposable copies of realistic repeated-channel projects with independently verified page counts and intended order. Check KiCad UI reopening and PDF page order when this is an applicable part of the approved workflow.

Tests should use synthetic fixture projects plus a carefully vetted real-world fixture if authorization, confidentiality, and distribution permit. A customer schematic is not automatically a distributable fixture. Do not copy proprietary test assets into a public repository.

## Evidence rules
- Codex must report actual commands executed, exit statuses, salient failures, and tests not run. No success without execution evidence.
- When Python is introduced, use behavior-focused `pytest` tests and Python compile checks (`python -m compileall` or an approved equivalent) where available and applicable.
- Validate code at the feature level, then perform a separate integrated check before declaring general readiness.
- Tests of text format or successful parses alone cannot prove functional connectivity preservation; toolchain-independent structural checks and KiCad verification have distinct confidence limits.
- Validate source identity and provenance of any imported KiCad fixture or version-specific claim.

## Commands
**Verified implemented commands:** none.
**Build/run:** no application.
**Test runner:** not installed or configured in this repository, and no tests yet exist.
**KiCad CLI or GUI check:** not established or executed.
**Useful future candidates (unverified):** `pytest`, `python -m compileall`, `git diff --check`, `kicad-cli sch export netlist`, and schematic/PDF readback. Exact invocation and availability must be established with the chosen environment and implementation. Do not assume a particular KiCad CLI output proves connectivity equivalence.

## Evidence gap and approved fixtures (2026-11-10)
- Codex's planning environment had KiCad 9.0.2 and Python 3.12.14, with no KiCad 10 runner. KiCad 9 cannot validate KiCad 10 imports/exports.
- ChatGPT independently inspected a current KiCad 10 hierarchical schematic project and upstream KiCad 10 documentation. Use the [KiCad upstream issue23403 regression fixture](https://gitlab.com/kicad/code/kicad/-/tree/10.0.6/qa/data/eeschema/issue23403) as public reference for multiple roots sharing a subsheet; build minimal original synthetic test fixtures locally, without copying proprietary customer material.
- Independent format evidence and safety boundary are in [ARCHITECTURE.md](ARCHITECTURE.md). Fixture structure tests must prove parent instance-path lookup, multi-root numbering, reused child file expansion and exact allowed byte changes. Real KiCad 10 GUI/CLI integration remains **unverified** until run on a KiCad 10 installation.
