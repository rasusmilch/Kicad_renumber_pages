# KiCad hierarchical page renumbering

**Status:** The Python CLI previews numbering by default and implements explicit `--apply` with verified backups, per-file replacement, conservative rollback, and interruption detection. Python fixture and failure-injection tests pass. Independent file checks, KiCad 10.0.8 CLI exports, and actual Eeschema hierarchy inspection passed on disposable projects. The qualification evidence awaits independent review; this is not a production-readiness or live-customer-use approval.

## Purpose

Develop a safe, repeatable way to renumber KiCad hierarchical schematic **sheet instances** so each parent precedes its descendants and a complete child subtree is numbered before moving to the next sibling subtree. The motivating project has many nested and repeated channel sheets, which accumulate inconsistent page numbers after sheets are added, moved, or removed.

The preview validates root metadata, reachable sheet references, per-project parent-instance paths, and page records before producing a plan. It distinguishes reused source documents from their individual sheet instances. Ordering and architecture follow the selected [requirements](docs/REQUIREMENTS.md) and [architecture](docs/ARCHITECTURE.md).

**Current implementation:** one immutable numbering plan serves preview and apply. Apply reloads inputs and modifies only approved page-token spans. The `.kicad_pro`, UUIDs, drawing objects, symbols, connectivity, and unrelated source bytes are not rewritten.

## Decision ownership

The user supplies intended operation, constraints, and approvals. ChatGPT inspects source, challenges weak assumptions, evaluates alternatives, and explicitly adjudicates behavior and architecture with the user. Codex is the implementation and validation agent: it may inspect source, identify options and risks, implement **only an approved design**, run checks, and return a scoped receipt. Neither Codex output, implementation convenience, nor passing tests constitute approval of a new product decision. Ambiguous behavior returns to the user and ChatGPT; silence is not consent.

## Document map

- [`AGENTS.md`](AGENTS.md) — required Codex operating contract and authority router.
- [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) — current selected intent, safety boundaries, and open product decisions.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — approved KiCad 10 instance model, parser/traversal, and limited recovery architecture.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — current stage and conditional next phases.
- [`docs/TESTING_STRATEGY.md`](docs/TESTING_STRATEGY.md) — behavior-test evidence, validation expectations, and limits.
- [`docs/DECISION_LOG.md`](docs/DECISION_LOG.md) — historical decision provenance and pending recommendations; current authority remains in the documents above.
- [`CHANGELOG.md`](CHANGELOG.md) — canonical effect-oriented project change history.

These documents are project-specific governance, informed by [Codex_guide](https://github.com/rasusmilch/Codex_guide), not a copy of its full template set.

## Workflow

**Intent → read-only Plan → review and explicit adjudication → focused Execute → Validate → independent review.** Use one focused workstream with separate implementation and verification checkpoints as warranted. Each Codex task must include **Goal, Background, Changes, Tests, Commands, Acceptance criteria**, and require a final receipt identifying files changed, command results, and unverified claims. Governance instructions live in `AGENTS.md`; task prompts carry the focused delta.

**Git workflow for this project:** Codex checks the remote identity and clean state, fetches the latest approved source from GitHub, works on a feature branch, and pushes each completed, validated local commit to the corresponding remote feature branch. Codex must verify remote publication and report failures without discarding work. The user and ChatGPT retain independent review, PR approval, and merge authority. This project-specific authorization intentionally differs from Codex_guide's older prepared-local, no-network rule; see [AGENTS.md](AGENTS.md).

## Current development commands

Requires Python 3.11+ and no third-party runtime packages. From the repository directory:

```sh
python renumber_pages.py /path/to/project.kicad_pro
# Only on a disposable test copy during this review stage; close every editor first:
python renumber_pages.py /path/to/disposable/project.kicad_pro --apply
```

The explicit project registry `schematic.top_level_sheets` defines all roots. All roots and child groups are naturally sorted by case-folded name, ASCII numeric runs, original name, then instance UUID path. Traversal is depth-first, parent-first, with continuous pages starting at 1 and no synthetic root. Empty instantiated sheets count; unrelated files are excluded.

The launcher prints every instance path, display name, source, old/new page, exact page-token byte range, affected files, and totals. Default preview creates no logs, backups, import caches, or other output files. Exit status is 0 for successful preview, verified apply, or an already-correct no-op; 2 for invalid/unsupported input or a detectable editor lock; 3 for an internal failure; 4 for an application failure before source modification or with complete verified restoration; and 5 for an unresolved operation or incomplete/uncertain recovery. Read the diagnostic as well as the exit status. No JSON/CSV reports or persistent configuration are produced; apply's internal recovery marker is described below.

Only schematic version `20260306` with `generator_version "10.0"` is accepted. Non-nil registered root UUIDs govern instance paths even if different from document UUIDs; explicit nil registry UUIDs fall back to document UUIDs. Missing/malformed identities and duplicate effective roots fail. External references, symlinks, hardlinks, ambiguous/missing instance records, cycles, and unsupported structural syntax fail closed. Known top-level `rectangle` and `table` drawings are opaque: their bytes are preserved and their contents do not participate in hierarchy or page discovery. Existing page strings may be duplicated, nonnumeric, or empty. Preview and apply no-ops preserve bytes and mtimes; ordinary reads may update access times.

## Apply, backups, and failure behavior

Close **all** KiCad Schematic Editor sessions and stop other writers before apply. The CLI warns that lock detection cannot establish this. It checks `~<filename>.lck` beside the project, every reachable schematic, and the conventional project-stem schematic, before applying and between replacements. It never deletes KiCad locks. An absent lock is not proof that unsaved sessions are closed.

An unchanged plan creates no directories, backups, temporary files, or marker. An existing operation marker still blocks apply, even if the current numbering appears correct. Preview remains read-only and can inspect a marked project.

For a changed plan, apply exclusively creates `backup-renumber/YYYY-MM-DD_HH-MM-SS/` using the machine's local time, adding `-1`, `-2`, etc. on collisions. Existing backups are neither merged nor deleted. Only changed schematic files are backed up, under their project-relative paths; the project file and unchanged/unrelated files are not copied. All backup bytes and SHA-256 digests are reread and verified before the first original replacement, and checked again before success.

`backup-renumber/active-operation.json` is an exclusive operation indicator acquired before backup/staging work. It records `version`, the project filename, the associated relative `backup` path, and `files` entries with project-relative `path`, `original_sha256`, and `expected_sha256`. This internal marker blocks cooperating applies and identifies interrupted work; it is not a resumable journal. An empty or malformed marker also blocks apply. A crash during setup can leave an incomplete backup set.

Complete candidates are staged in exclusive `.<filename>.renumber-*.tmp` files beside originals. The utility verifies staged bytes and metadata, rechecks every source snapshot (including `.kicad_pro` and unchanged reachable files), then rechecks each target immediately before individual `os.replace`. It verifies installed bytes after every replacement, reparses the whole project with the same engine, checks the exact instance order and page assignments, and requires a no-change final plan. Exact candidate equality protects every non-page byte.

On a detected failure, forward replacements stop. Rollback rereads verified backups and restores only targets still matching the operation's expected new bytes, rechecking before each restoration. Unknown/third-party bytes are never overwritten. Complete restoration must be verified; otherwise the marker and backups remain and exit 5 requires manual recovery. Exit 4 retains any created backup directory, which may be partial when setup failed. The marker is removed only after verified success or verified restoration.

File data is flushed/synced; directories are synced on platforms/filesystems supporting it. Mode bits and mtime are preserved and checked; `copystat` also preserves other ordinary metadata where supported. Ownership, ACLs, platform flags, and all extended attributes are not universally guaranteed. Windows and network filesystems remain unvalidated. Per-file replacement is **not** an atomic multi-file transaction. Hash/identity rechecks do not exclude a noncooperating writer racing the final check. Process death/power loss can leave a partial file set, temporary files, or a stale marker, even after a reported success; no universal crash durability is claimed.

Source identity checks retain device, inode/file ID, mode, link count, size, and nanosecond mtime. On Windows only, deprecated `st_ctime_ns` is excluded because path-based `lstat` and handle-based `fstat` can disagree for an unchanged file; POSIX retains ctime checks. Repeated reads, content/digest checks, backup verification, and rollback guards remain in place. Metadata mismatch diagnostics name the differing fields and verification stage. Regression coverage simulates Windows stat results on real Linux temporary files; this correction has not yet been executed on native Windows.

## Manual recovery after interruption

1. Close KiCad and stop all writers. Preserve a separate copy of the entire affected project, marker, and backups. Do not clear a marker merely because numbering looks correct or preview succeeds.
2. Inspect `backup-renumber/active-operation.json`. Confirm its project and contained relative paths identify this operation. If it is truncated, malformed, or references missing backups, retain it and obtain independent recovery review; do not guess which files were replaced.
3. For every listed file, compute SHA-256 of the current file and its corresponding backup (for example `sha256sum -- <file>` on Linux, or `Get-FileHash -Algorithm SHA256 -LiteralPath <file>` in PowerShell). Each backup must match `original_sha256`. Current bytes matching `original_sha256` are original; matching `expected_sha256` are the planned new content; matching neither are unknown and must be preserved for separate review. Do not copy unknown files over originals or trust leftover temporary files as backups.
4. On a controlled copy, restore the **complete** participating original set from verified backups while preserving permissions and mtime. Independently verify the project file and unchanged referenced files against known source/version control, since they are not backed up. Run preview to reparse the complete graph. Original page numbers may still need renumbering; a no-change preview is not a recovery criterion. Verify every participating working file now matches its original digest and that no unknown source changes remain.
5. Before clearing the marker in the actual working project, perform the same full restoration/verification **there**, with all writers still closed; success on a separate copy alone is insufficient. Preserve an audit copy of the marker outside that project. From that project's directory, remove **only** the resolved marker with `python -c "from pathlib import Path; Path('backup-renumber/active-operation.json').unlink()"`. Retain timestamped backups. Review any leftover `.*.renumber-*.tmp` files individually before manually removing them; never use a wildcard deletion across source files.

No automatic crash resumption, recovery CLI, or marker-clearing option exists.

## Development checks

Set up the development environment on Linux:

```sh
python -m venv .venv
.venv/bin/python -m pip install --index-url https://pypi.org/simple -r requirements-dev.txt
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall kicad_renumber tests renumber_pages.py
git diff --check
```

On Windows, use `.venv\Scripts\python.exe` instead of `.venv/bin/python`. Windows and Python 3.11 have not been separately exercised; validation here used Python 3.12.14 on Linux. The same behavior suite also runs with `python -m unittest discover -q`. Development checks create ignored caches; the launcher suppresses incidental import-cache writes in both modes.

See [TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md) for evidence and limits. Qualification used the official KiCad 10.0.8 Lite AppImage on Debian 13 x86_64, separately from installed KiCad 9.0.2. It includes actual GUI navigation of all 15 instances across three disposable projects and CLI netlist comparisons. Coverage is limited to those fixtures and that environment; KiCad CLI 10.0.6 alone remains insufficient as a multi-root identity oracle.
