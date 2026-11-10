# Repository operating contract

## Read first
1. [README.md](README.md) — purpose, status, and navigation.
2. [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) — selected user requirements and unresolved product decisions.
3. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — approved KiCad 10 encoding, instance model and file-update boundaries.
4. [docs/ROADMAP.md](docs/ROADMAP.md) — currently authorized stage and sequencing.
5. [docs/TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md) — applicable validation expectations and actual command status.
6. [docs/DECISION_LOG.md](docs/DECISION_LOG.md) — historical provenance (not substitute current authority).
7. [CHANGELOG.md](CHANGELOG.md) — canonical merge-facing project-change history.
For substantial workflow questions consult the user's `rasusmilch/Codex_guide`, particularly `04-core-operating-rules.md`, `05-current-source-inspection-rule-for-all-prompts.md`, `09-one-draft-pr--multi-subtask-workflow.md`, `47-v4-project-bootstrap-workflow.md`, `48-v4-agents-and-anchor-contracts.md`, and `49-v4-compact-receipt-contracts.md`. The user has explicitly approved a **project-specific exception** to the guide's prepared-local/no-network/no-push model; the controlled Git preflight/publication rules below take precedence **for this repository only**. The central guide has not been amended, and its unrelated safety, planning, authority, receipt, and merge controls remain applicable.

## Authority and decision rights
- Current source establishes **what exists**; user-approved intent establishes **what ought to exist**. Neither an implementation detail nor a passing test can authorize new product behavior.
- **User** selects purpose, operator behavior, constraints, and materially consequential decisions.
- **ChatGPT** is senior engineer and architect: inspect available current source, distinguish facts/assumptions/proposals/selected choices, challenge the direction as needed, elicit and adjudicate decisions with the user, produce self-contained approved Codex tasks, and independently review receipts and evidence.
- **Codex** is the junior implementation agent. It investigates and proposes options **only when requested**, implements the explicitly approved architecture and behavior, tests, documents verified results, and reports blockers. It must **not** independently resolve conflicting requirements, select a product contract, change architectural boundaries, or make an unresolved policy choice.
- Material unresolved behavior is **Open**, not tacit permission. Stop and seek ChatGPT/user adjudication instead of guessing. A plan or receipt is a claim, not authority.

## Work stages and scope
- The repository contains a read-only preview engine and behavior tests following the independently reviewed [architecture](docs/ARCHITECTURE.md). Apply, backup, and recovery remain unimplemented. **Only** an explicitly assigned focused Codex execution task may implement a named phase; no user-project mutation is authorized by governance alone.
- For nontrivial work use **Plan (read-only) → Review / explicit user-and-ChatGPT adjudication → focused Execute → Validate → independent review**. One feature/fix workstream, ordinarily one draft PR, and independent semantic subtasks when warranted. **Codex is expressly authorized and required to refresh its GitHub checkout before work and publish completed validated commits to GitHub** under the following controlled procedure.
- The user and ChatGPT retain review, product/architecture adjudication, and merge closure. A Codex commit and push publish evidence for review; they do **not** mean the task, PR, or design has received independent GO. If a local commit or remote push fails, preserve the complete validated local state, stop short of claiming publication, and report the failure. Do not reset, clean, force-push, or discard changes.
- Do not introduce PDF output, GUI/plugin integration, project conversion, KiCad project mutations, new compatibility promises, or unrelated automation merely because they appear convenient. Compare new mechanisms with the simplest viable approved design before adding new persistent concepts.
- The planned product must be treated as potentially destructive to EDA source files. Do not run a write operation on a user's live schematic without a separately selected write policy and explicit authorization.

## Project-specific GitHub refresh and publication contract

**Applicability:** this repository only, based on explicit user authorization on 2026-11-10. Having internet access is not itself evidence of usable Git credentials; confirm access and report authentication/authorization failures. No authority to operate on other user repositories is implied.

1. **Source preflight, before substantive work:** check `git status --porcelain=v1`, the current branch, configured remote identity, and whether a previous task's local work or a feature branch exists. The expected repository is `rasusmilch/Kicad_renumber_pages`. Verify that `origin` targets this repository and run `git fetch origin`. Verify the remote's relevant tip; do not trust a previous task's stale HEAD. If the working tree is dirty, remotes are ambiguous, permissions are missing, or there is unexpected divergence, stop and report without overwriting anything.
2. **Starting a new workstream:** from a verified clean checkout, fast-forward the local baseline to the current `origin/main` (for example `git switch main` followed by `git merge --ff-only origin/main`), then create a descriptive `codex/<workstream>` feature branch. Never implement directly on `main`. Do not run `git pull` with implicit merge/rebase behavior.
3. **Continuing a workstream:** inspect the existing feature branch and its remote, fetch, and fast-forward the local branch from its same remote branch if appropriate and clean. Do not silently discard accumulated work, rebase, reset, cherry-pick, or merge a changed `main` into an active branch without an approved integration task. If the state is ambiguous, stop for review.
4. **After completing each tracked execution unit:** run all applicable agreed validation; reconcile directly affected current-state documentation; create a local commit of only the intended reviewed unit; **push that commit to the same feature branch** on GitHub using a normal non-force push. Verify that the remote branch contains the new commit (for example `git ls-remote --heads origin <branch>` or a checked fetch). Report branch, published commit, local/remote verification, changed files, checks/results, and limitations in the receipt. A read-only task or no-change task does not create a ceremonial commit or push.
5. **If publication fails:** do not report the task as published; do not rewrite history or force. Preserve the validated commit/working tree and report whether failure is due to credentials, permissions, non-fast-forward divergence, network, or another reason; request the narrow next action. Remote publication is required for completed tracked execution but never a reason to discard locally preserved work.
6. **PR and merge boundary:** push to the feature branch, not `main`. PR opening/metadata review, independent acceptance, and merging remain separate user/ChatGPT decisions. Codex may inspect hosted evidence needed for the task; it must not approve its own work or merge merely because network access exists. No history rewriting or secret-bearing output.

This replaces the earlier project's local-only/no-network/no-push rule. It does **not** change the program's approved architecture, behavior, safety boundaries, or authority over Codex's engineering choices.

## Dependency installation authorization

**Standing user authorization (2026-11-10):** Codex may install the dependencies and test tooling **reasonably necessary to implement and validate the approved tasks in this repository** without asking separately for routine setup. This explicitly includes `pytest` and its ordinary resolved dependencies. Network access for package installation is allowed; this is not permission to alter the approved product architecture or add unrelated runtime dependencies.

- **Python:** prefer an isolated virtual environment (`python3 -m venv .venv`, then `.venv/bin/python -m pip install pytest` on Linux, or the corresponding `.venv\\Scripts\\python.exe` on Windows). Use a requirements/development dependency declaration if the project needs reproducible setup. `pytest` is a development dependency; the approved program remains standard-library-only at runtime unless user/ChatGPT explicitly approves an exception. Do not use `sudo pip` or `--break-system-packages`.
- **Trusted sources:** prefer standard Python package indexes (official PyPI), the environment's official operating-system repositories, or official KiCad distributions for KiCad-specific validation. Do not execute fetched shell scripts, install packages from untrusted URLs or random Git repositories, or accept arbitrary package-install hooks beyond normal trusted package installation. No credentials should enter logs, source files, or command lines.
- **System-level tools:** Codex may install missing, narrowly required testing/build tools (for example `python3-venv` or official KiCad 10 validation tooling) **in its isolated disposable execution environment** when credentials and package-manager privileges permit. Do not alter the user's workstation, system repositories, desktop configuration, or unrelated software. Do not perform broad `apt upgrade`, distro upgrades, or change third-party package repositories without further adjudication.
- **Proportionality:** install only what the approved task actually needs; don't add optional frameworks, linters, code generators, services, or dependency-management layers merely because installation is now authorized. Tool availability does not prove tests passed.
- **Evidence:** the receipt must identify installed tools/dependencies and versions where material, the commands used, installation failures, test commands/results, and anything unverified. If installation fails or a dependency requires an unsafe/unapproved system change, stop or report the specific validation gap; do not substitute a false pass. Keep transient environments and caches out of Git (e.g. `.venv`, `.pytest_cache`).

This bounded authorization supersedes earlier task-language prohibiting package installation without permission, **for necessary development/testing dependencies only**, and applies to the current ongoing task and later approved tasks. It is not independent authorization to implement additional product features, operate on live customer projects, merge a PR, or choose new product architecture.

## Task and receipt boundaries
- Each Codex task must have **Goal, Background, Changes, Tests, Commands, Acceptance criteria**. Include protected scope, unknowns, and stop conditions where material. Consecutive task numbering and lettered follow-up tasks are specified by ChatGPT, not invented by Codex.
- For every execution task, require behavior-focused tests where applicable, the installation and execution of `pytest` or appropriate approved test tooling when needed, Python compilation checks when Python exists, and a final receipt naming material changed files, exact command results, and unverified/blocked claims. See standing dependency-install authorization above. Never claim a pass for a command not run.
- Follow the guide's compact receipt contract: one fenced `text` block, delimited by `~~~text` and `~~~`, with an `=== Receipt — … ===` board and matching ending board. Report the material delta, evidence classes and limits, checks performed, applicable documentation and changelog impact, local working-tree/durable handoff status, remote branch/commit publication status and verification when applicable, and one next action. A complete receipt is not proof of correctness.
- Apply proportional validation to credible failure modes. No fixed checklist proves KiCad file safety. Test results cannot substitute for approved design behavior.

## Documentation and historical evidence
- Current-state documents must state the selected present truth directly; do not leave stale active claims beside new ones. After semantic implementation, search directly affected documents for outdated assertions and reconcile in place before treating the unit as complete. An unresolved material authority choice blocks execution; only the guide's narrowly authorized one-hop review-stage clerical carry-forward is exceptional.
- Preserve historical decisions and their provenance in `docs/DECISION_LOG.md`. Never treat chronology, prior receipts, or the person editing a document as the authority for an unapproved decision.
- `CHANGELOG.md` is **the sole canonical changelog** for user-relevant material changes, with `Unreleased` for accumulated unmerged work. Intermediate commits need not update it mechanically. Before integration/merge readiness, reconcile its meaningful cumulative effects; do not log task numbers, filenames, PRs, or implementation ceremony.
- Do not add duplicate governance trackers, empty anchors, invented command lists, or unnecessary templates.

## Verified commands and limits
- **Run:** `python renumber_pages.py <explicit-project.kicad_pro>`; read-only preview only. `--apply` is rejected.
- **Automated tests:** `.venv/bin/python -m pytest -q` and `python -m unittest discover -q`; behavior tests exist and have run. No CI is configured.
- **Compilation:** Python compileall checks have run. See [TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md) for exact commands and evidence limits.
- **KiCad validation / netlist checks:** upstream KiCad 10 fixture bytes have been analyzed by the Python engine, but no installed KiCad 10 GUI/CLI validation or netlist comparison has run.
- **Documentation review:** `git diff --check` and `git status --short` have run; future receipts must report current results rather than inherit these claims.
- Inspect the actual current files/environment before recording any command as supported; explicitly state unavailable, unknown, unverified, or not applicable evidence.

## Safety and stop conditions
- Never rewrite KiCad sheet UUIDs, connections, or symbol contents as incidental formatting. The approved traversal, parsing and allowed page-only changes are owned by [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Stop when evidence would require a material departure from this architecture; do not invent the departure.
- Refuse to guess at shared-file instance behavior, cycles, missing pages, malformed source, or path ambiguity. Report choices and their tradeoffs to ChatGPT/user.
- If current authority becomes contradictory, materially incomplete, or untrustworthy, route to governance reconciliation / stop-and-replan rather than implementing from assumptions.
