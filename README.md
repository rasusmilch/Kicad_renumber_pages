# KiCad hierarchical page renumbering

**Status:** A tested, read-only Python CLI discovers KiCad 10 sheet instances and previews whole-project page numbering. Apply, backup, and recovery are not implemented. There is no release or KiCad 10 application-based integration validation yet.

## Purpose

Develop a safe, repeatable way to renumber KiCad hierarchical schematic **sheet instances** so each parent precedes its descendants and a complete child subtree is numbered before moving to the next sibling subtree. The motivating project has many nested and repeated channel sheets, which accumulate inconsistent page numbers after sheets are added, moved, or removed.

The preview validates root metadata, reachable sheet references, per-project parent-instance paths, and page records before producing a plan. It distinguishes reused source documents from their individual sheet instances. Ordering and architecture follow the selected [requirements](docs/REQUIREMENTS.md) and [architecture](docs/ARCHITECTURE.md).

**Current implementation:** read-only preview, including in-memory verification of proposed page-only edits. `--apply` is explicitly rejected. No user schematic mutation is authorized by this implementation.

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
```

The explicit project registry `schematic.top_level_sheets` defines all roots. All roots and child groups are naturally sorted by case-folded name, ASCII numeric runs, original name, then instance UUID path. Traversal is depth-first, parent-first, with continuous pages starting at 1 and no synthetic root. Empty instantiated sheets count; unrelated files are excluded.

The launcher prints every instance path, display name, source, old/new page, exact page-token byte range, affected files, and totals. It creates no logs, backups, import caches, or other output files. Exit status is 0 for either successful outcome (changes needed or already correct), 2 for invalid/unsupported input or CLI usage, and 3 for an internal failure. `--apply` returns an unsupported-operation error, even when the plan would be a no-op.

Only schematic version `20260306` with `generator_version "10.0"` is accepted. Non-nil registered root UUIDs govern instance paths even if different from document UUIDs; explicit nil registry UUIDs fall back to document UUIDs. Missing/malformed identities and duplicate effective roots fail. External references, symlinks, hardlinks, ambiguous/missing instance records, cycles, and unsupported structural syntax fail closed. Existing page strings may be duplicated, nonnumeric, or empty. File bytes and modification times remain unchanged; ordinary filesystem reads may update access times.

Set up the development environment on Linux:

```sh
python -m venv .venv
.venv/bin/python -m pip install --index-url https://pypi.org/simple -r requirements-dev.txt
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall kicad_renumber tests renumber_pages.py
git diff --check
```

On Windows, use `.venv\Scripts\python.exe` instead of `.venv/bin/python`. Windows and Python 3.11 have not been separately exercised; validation here used Python 3.12.14 on Linux. The same behavior suite also runs with `python -m unittest discover -q`. Development checks create ignored caches; the preview launcher suppresses import-cache writes.

See [TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md) for evidence and limits. Reading upstream KiCad 10 fixtures is format evidence, not Eeschema GUI or KiCad CLI integration validation. In particular, KiCad CLI 10.0.6 alone is not a multi-root identity oracle.
