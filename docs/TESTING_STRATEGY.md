# Validation strategy

**Current evidence:** the read-only parser, graph, immutable plan, and terminal CLI have passing Python behavior tests. A project-local virtual environment contains pytest. Direct analysis of upstream KiCad 10.0.6 fixture bytes succeeds; no installed KiCad 10 Eeschema GUI/CLI validation or netlist comparison has run. Apply/backup/recovery remain unimplemented and untested; no CI exists.

## Risk to establish confidence against
Renumbering must not change circuit semantics, misnumber shared/repeated instances, silently skip sheets, partially write files, or claim safety when unsupported syntax or an ambiguous hierarchy prevents confidence.

## Validation layers and current coverage
1. **Model/traversal behavior:** single sheet; nested multiple levels; repeated source files via distinct instance paths; empty sheets; natural numeric names; ties; reordered siblings; existing duplicate/gapped page numbers; idempotent reruns. Expected order must follow the *approved* ordering policy rather than tests inventing it.
2. **Read and parse integrity:** covered by tests for malformed S-expressions, missing referenced sources, duplicate/invalid UUIDs and paths, cycles, unsupported versions/syntax, orphan current-project paths, foreign-project records, missing pages, JSON duplicates, symlinks/hardlinks, and external references. Registry and document UUID equality is not required; effective-root rules below govern path validation.
3. **Read-only safety:** tests compare file contents, mtimes, and directory entries before/after previews and no-ops, including a cold launcher with no import caches. `--apply` is rejected without writes. Source changes during analysis fail. **Future write safety:** staged replacement, backups, rollback, crash recovery, and apply-time changes require a separate implementation and fault-injection suite.
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
**Executed setup:** `python -m venv .venv` and `.venv/bin/python -m pip install --index-url https://pypi.org/simple pytest`. Installation succeeded from PyPI: pytest 9.2.0, iniconfig 2.3.1, packaging 26.3, pluggy 1.7.0, and pygments 2.21.0. Pip disabled its unwritable home cache; no system packages were changed. `requirements-dev.txt` pins the test runner for repeatable setup.

**Executed checks:** Python 3.12.14 on Linux; `.venv/bin/python -m pytest -q`, `python -m unittest discover -q`, `python -m compileall .`, and `git diff --check` have succeeded. The tests are unittest-compatible and discovered by pytest; they generate original, small synthetic KiCad 10 projects in temporary directories. Test fixtures are not live customer projects, and the suite does not require network access or KiCad. The task receipt records the final suite count and command results.

**Preview:** `python renumber_pages.py <explicit-project.kicad_pro>`. Direct preview of the public issue23403 fixture reports two roots, four instances, and already-correct pages 1–4, including the mismatched registered/document UUID case. Public files were inspected in scratch space and are not copied into this repository.

**Unverified:** Python 3.11 execution, Windows, network filesystems, installed KiCad 10 GUI/CLI loading, and netlist equivalence. The existing KiCad 9 installation cannot establish KiCad 10 compatibility. Any future KiCad export command must be verified for its exact version and whole-forest coverage; CLI success alone is insufficient.

## Evidence gap and approved fixtures (2026-11-10)
- Codex's planning environment had KiCad 9.0.2 and Python 3.12.14, with no KiCad 10 runner. KiCad 9 cannot validate KiCad 10 imports/exports.
- ChatGPT independently inspected a current KiCad 10 hierarchical schematic project and upstream KiCad 10 documentation. Use the [KiCad upstream issue23403 regression fixture](https://gitlab.com/kicad/code/kicad/-/tree/10.0.6/qa/data/eeschema/issue23403) as public reference for multiple roots sharing a subsheet; build minimal original synthetic test fixtures locally, without copying proprietary customer material.
- Independent format evidence and safety boundary are in [ARCHITECTURE.md](ARCHITECTURE.md). Fixture structure tests must prove parent instance-path lookup, multi-root numbering, reused child file expansion and exact allowed byte changes. Include a fixture with a non-nil project-registered root UUID **different** from the document header UUID (as in KiCad upstream issue23403); assert acceptance and child paths keyed to the registered UUID. Include equality and explicit nil-registry-UUID fallback cases; reject absent/malformed registry UUIDs and duplicate effective root UUIDs, and verify neither identity is changed. KiCad CLI 10.0.6 can differ from Eeschema about this override; validate GUI and CLI versions separately rather than accepting CLI-only proof. Real KiCad 10 GUI/CLI integration remains **unverified** until run on a KiCad 10 installation.


## Test environment setup authorization (2026-11-10)

The user explicitly permits Codex to install reasonably necessary development/test packages in its isolated execution environment. For Python tests, use a virtual environment and install `pytest` from a trusted package index; installing official distribution `python3-venv` or official KiCad 10 tooling for actually needed integration validation is authorized when safe and supported. Do not alter an end user's host system or install unrelated packages. Runtime remains standard-library-only unless a separate architecture decision is approved.

The setup authorization is distinct from test evidence; executed setup and checks are recorded above. Future receipts must state actual commands, versions where relevant, results, and skipped/unavailable integration tests. Refer to [AGENTS.md](../AGENTS.md) for the authoritative safety conditions.
