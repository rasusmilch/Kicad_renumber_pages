# Changelog

Canonical project-change history for material user-facing and maintainability effects. Maintain the **Unreleased** section cumulatively; do not log every commit, task number, or file edit. Documentation should not be mistaken for implemented behavior.

## Unreleased

- Fixed rejection of valid KiCad 10 rectangle and table drawings while preserving their source bytes and retaining strict hierarchy and unsupported-syntax checks.
- Added a read-only KiCad 10 page-numbering preview with natural parent-first ordering across all registered roots, repeated-sheet instance handling, effective root UUID resolution, strict hierarchy validation, and verified page-value byte locations. Existing project and schematic files remain unchanged; apply, backup, and recovery are not implemented.
- Established governance and selected conservative file-preservation, future backup/recovery, validation, and independent review boundaries.
