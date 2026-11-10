# Repository operating contract

## Read first
1. [README.md](README.md) — purpose, status, and navigation.
2. [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) — selected user requirements and unresolved product decisions.
3. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — approved KiCad 10 encoding, instance model and file-update boundaries.
4. [docs/ROADMAP.md](docs/ROADMAP.md) — currently authorized stage and sequencing.
5. [docs/TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md) — applicable validation expectations and actual command status.
6. [docs/DECISION_LOG.md](docs/DECISION_LOG.md) — historical provenance (not substitute current authority).
7. [CHANGELOG.md](CHANGELOG.md) — canonical merge-facing project-change history.
For substantial workflow questions consult the user's `rasusmilch/Codex_guide`, particularly `04-core-operating-rules.md`, `05-current-source-inspection-rule-for-all-prompts.md`, `09-one-draft-pr--multi-subtask-workflow.md`, `47-v4-project-bootstrap-workflow.md`, `48-v4-agents-and-anchor-contracts.md`, and `49-v4-compact-receipt-contracts.md`. The external guide is reference, not a required network dependency for local execution.

## Authority and decision rights
- Current source establishes **what exists**; user-approved intent establishes **what ought to exist**. Neither an implementation detail nor a passing test can authorize new product behavior.
- **User** selects purpose, operator behavior, constraints, and materially consequential decisions.
- **ChatGPT** is senior engineer and architect: inspect available current source, distinguish facts/assumptions/proposals/selected choices, challenge the direction as needed, elicit and adjudicate decisions with the user, produce self-contained approved Codex tasks, and independently review receipts and evidence.
- **Codex** is the junior implementation agent. It investigates and proposes options **only when requested**, implements the explicitly approved architecture and behavior, tests, documents verified results, and reports blockers. It must **not** independently resolve conflicting requirements, select a product contract, change architectural boundaries, or make an unresolved policy choice.
- Material unresolved behavior is **Open**, not tacit permission. Stop and seek ChatGPT/user adjudication instead of guessing. A plan or receipt is a claim, not authority.

## Work stages and scope
- The repository currently contains governance only. A read-only planning investigation was independently reviewed and the [architecture](docs/ARCHITECTURE.md) adjudicated. **Only** an explicitly assigned focused Codex execution task may implement a named phase; no user-project mutation is authorized by governance alone.
- For nontrivial work use **Plan (read-only) → Review / explicit user-and-ChatGPT adjudication → focused Execute → Validate → independent review**. One feature/fix workstream, ordinarily one draft PR, and independent semantic subtasks when warranted. Codex uses only its prepared local checkout; it must not fetch/pull/push, query GitHub, or perform hosted PR/merge operations.
- The user and ChatGPT own hosted review and merge closure. Codex may durably preserve completed validated local changes with a local commit; this does **not** establish approval or merge readiness. If a durable handoff fails, retain the working tree and report it; never discard validated work to hide a failure.
- Do not introduce PDF output, GUI/plugin integration, project conversion, KiCad project mutations, new compatibility promises, or unrelated automation merely because they appear convenient. Compare new mechanisms with the simplest viable approved design before adding new persistent concepts.
- The planned product must be treated as potentially destructive to EDA source files. Do not run a write operation on a user's live schematic without a separately selected write policy and explicit authorization.

## Task and receipt boundaries
- Each Codex task must have **Goal, Background, Changes, Tests, Commands, Acceptance criteria**. Include protected scope, unknowns, and stop conditions where material. Consecutive task numbering and lettered follow-up tasks are specified by ChatGPT, not invented by Codex.
- For every execution task, require behavior-focused tests where applicable, `pytest` or equivalent test checks **when the project has a verified test environment**, Python compilation checks **when Python exists**, and a final receipt naming material changed files, exact command results, and unverified/blocked claims. Never claim a pass for a command not run.
- Follow the guide's compact receipt contract: one fenced `text` block, delimited by `~~~text` and `~~~`, with an `=== Receipt — … ===` board and matching ending board. Report the material delta, evidence classes and limits, checks performed, applicable documentation and changelog impact, local working-tree/durable handoff status, and one next action. A complete receipt is not proof of correctness.
- Apply proportional validation to credible failure modes. No fixed checklist proves KiCad file safety. Test results cannot substitute for approved design behavior.

## Documentation and historical evidence
- Current-state documents must state the selected present truth directly; do not leave stale active claims beside new ones. After semantic implementation, search directly affected documents for outdated assertions and reconcile in place before treating the unit as complete. An unresolved material authority choice blocks execution; only the guide's narrowly authorized one-hop review-stage clerical carry-forward is exceptional.
- Preserve historical decisions and their provenance in `docs/DECISION_LOG.md`. Never treat chronology, prior receipts, or the person editing a document as the authority for an unapproved decision.
- `CHANGELOG.md` is **the sole canonical changelog** for user-relevant material changes, with `Unreleased` for accumulated unmerged work. Intermediate commits need not update it mechanically. Before integration/merge readiness, reconcile its meaningful cumulative effects; do not log task numbers, filenames, PRs, or implementation ceremony.
- Do not add duplicate governance trackers, empty anchors, invented command lists, or unnecessary templates.

## Verified commands and limits
- **Build/run:** none exists; there is currently no source code or application.
- **Automated tests:** none exists; no suite or CI has been configured or run.
- **KiCad validation / netlist checks:** no project-specific command has been established or executed.
- **Documentation review:** Markdown and Git diff inspection are applicable when a local checkout is available. `git diff --check`, `git status --short`, and manual relative-link inspection are *suggested*, not represented as executed or verified for this repository.
- When implementation arrives, inspect the actual files/environment before recording any command as supported; explicitly state unavailable, unknown, unverified, or not applicable evidence.

## Safety and stop conditions
- Never rewrite KiCad sheet UUIDs, connections, or symbol contents as incidental formatting. The approved traversal, parsing and allowed page-only changes are owned by [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Stop when evidence would require a material departure from this architecture; do not invent the departure.
- Refuse to guess at shared-file instance behavior, cycles, missing pages, malformed source, or path ambiguity. Report choices and their tradeoffs to ChatGPT/user.
- If current authority becomes contradictory, materially incomplete, or untrustworthy, route to governance reconciliation / stop-and-replan rather than implementing from assumptions.
