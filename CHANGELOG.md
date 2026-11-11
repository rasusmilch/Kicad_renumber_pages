# Changelog

Canonical project-change history for material user-facing and maintainability effects. Maintain the **Unreleased** section cumulatively; do not log every commit, task number, or file edit. Documentation should not be mistaken for implemented behavior.

## Unreleased

- Fixed rejection of valid KiCad 10 rectangle and table drawings while preserving their source bytes and retaining strict hierarchy and unsupported-syntax checks.
- Added KiCad 10 whole-project page numbering with read-only preview by default, natural parent-first ordering across all registered roots, repeated-sheet instance handling, effective root UUID resolution, strict hierarchy validation, and verified page-value byte locations.
- Added explicit apply with mandatory verified timestamped backups, source/lock checks, staged per-file replacement, final whole-project verification, conservative rollback, and interruption markers with manual recovery guidance. The project file and all non-page source bytes remain protected; disposable-project integration checks now include official KiCad 10.0.8 Eeschema and CLI, independent page-only byte comparisons, and manual recovery. Production readiness remains unapproved.
- Established governance and conservative file-preservation, validation, and independent review boundaries.
