# KiCad hierarchical page renumbering

**Status:** Governance and design discovery only. There is no implementation, packaged application, test suite, or released command in this repository.

## Purpose

Develop a safe, repeatable way to renumber KiCad hierarchical schematic **sheet instances** so each parent precedes its descendants and a complete child subtree is numbered before moving to the next sibling subtree. The motivating project has many nested and repeated channel sheets, which accumulate inconsistent page numbers after sheets are added, moved, or removed.

The user also wants **built-in checks**. A successful implementation must not silently corrupt a KiCad project or change the circuit while editing page numbering. The complete behavior, ordering policy, supported environments, and implementation architecture require a separate explicit design adjudication.

**Current authorization:** reviewed design supports a focused Codex implementation task for the read-only preview engine, followed by an independently reviewed apply/backup phase. There is still **no application code** and no authorization to mutate any user schematic.

## Decision ownership

The user supplies intended operation, constraints, and approvals. ChatGPT inspects source, challenges weak assumptions, evaluates alternatives, and explicitly adjudicates behavior and architecture with the user. Codex is the implementation and validation agent: it may inspect source, identify options and risks, implement **only an approved design**, run checks, and return a scoped receipt. Neither Codex output, implementation convenience, nor passing tests constitute approval of a new product decision. Ambiguous behavior returns to the user and ChatGPT; silence is not consent.

## Document map

- [`AGENTS.md`](AGENTS.md) — required Codex operating contract and authority router.
- [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) — current selected intent, safety boundaries, and open product decisions.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — approved KiCad 10 instance model, parser/traversal, and limited recovery architecture.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — current stage and conditional next phases.
- [`docs/TESTING_STRATEGY.md`](docs/TESTING_STRATEGY.md) — validation expectations and evidence limits; no passing tests are claimed.
- [`docs/DECISION_LOG.md`](docs/DECISION_LOG.md) — historical decision provenance and pending recommendations; current authority remains in the documents above.
- [`CHANGELOG.md`](CHANGELOG.md) — canonical effect-oriented project change history.

These documents are project-specific governance, informed by [Codex_guide](https://github.com/rasusmilch/Codex_guide), not a copy of its full template set.

## Workflow

**Intent → read-only Plan → review and explicit adjudication → focused Execute → Validate → independent review.** Use one focused workstream with separate implementation and verification checkpoints as warranted. Each Codex task must include **Goal, Background, Changes, Tests, Commands, Acceptance criteria**, and require a final receipt identifying files changed, command results, and unverified claims. Governance instructions live in `AGENTS.md`; task prompts carry the focused delta.

**Git workflow for this project:** Codex checks the remote identity and clean state, fetches the latest approved source from GitHub, works on a feature branch, and pushes each completed, validated local commit to the corresponding remote feature branch. Codex must verify remote publication and report failures without discarding work. The user and ChatGPT retain independent review, PR approval, and merge authority. This project-specific authorization intentionally differs from Codex_guide's older prepared-local, no-network rule; see [AGENTS.md](AGENTS.md).

## Current development commands

None are established. No build, test, release, or KiCad verification command has been executed for this empty codebase. Documentation can be read directly; future commands must be inspected and verified before being advertised as supported.
