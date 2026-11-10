"""Conservative per-file apply; not an atomic multi-file transaction.

One exclusive marker records the backup and before/after digests. There is no
journal or automatic crash resumption. All numbering comes from engine.build_plan.
"""

from dataclasses import dataclass
from datetime import datetime
import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile

from . import engine
from .engine import NumberingPlan, Snapshot
from .sexpr import InvalidProject


BACKUP_DIRECTORY = "backup-renumber"
MARKER_NAME = "active-operation.json"
EDITOR_WARNING = ("Close every KiCad Schematic Editor before apply. Lock checks cannot "
                  "prove that all unsaved sessions or other writers are closed.")


class ApplyFailure(Exception):
    """A failed application, distinguished from invalid input and internal errors."""

    def __init__(self, message: str, *, incomplete: bool = False):
        super().__init__(message)
        self.incomplete = incomplete


@dataclass(frozen=True)
class ApplyResult:
    plan: NumberingPlan
    backup: Path | None


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _present(path: Path) -> bool:
    # Include dangling symlinks and non-file indicators; never silently ignore them.
    return os.path.lexists(path)


def _recovery_message(marker: Path, backup: Path | None = None) -> str:
    if backup is None:
        try:
            record = json.loads(engine._read(marker).data)
            relative = record.get("backup")
            if isinstance(relative, str):
                parts = Path(relative).parts
                if len(parts) == 2 and parts[0] == BACKUP_DIRECTORY and parts[1] not in (".", ".."):
                    backup = marker.parent.parent / relative
        except (OSError, InvalidProject, ValueError, AttributeError):
            pass
    associated = str(backup) if backup else "unknown (inspect timestamp directories; marker may be incomplete)"
    return (f"Unresolved operation marker: {marker}. Associated backup: {associated}. "
            "Close KiCad, preserve the marker/backups, and compare SHA-256 of every participating "
            "file with its original_sha256 and expected_sha256 in the marker. Unknown bytes must "
            "not be overwritten. Verify/restore the complete original project on a controlled copy "
            "before manually clearing the resolved marker; see README recovery procedure. "
            "No automatic resumption or marker deletion was performed.")


def _check_operation(project: Path) -> Path:
    root = project.parent / BACKUP_DIRECTORY
    engine._check_components(root)
    if _present(root) and not root.is_dir():
        raise InvalidProject(f"backup path is not a directory: {root}")
    marker = root / MARKER_NAME
    if _present(marker):
        raise ApplyFailure(_recovery_message(marker), incomplete=True)
    return marker


def _check_locks(plan: NumberingPlan) -> None:
    # KiCad 10 include/lockfile.h and common/wildcards_and_files_ext.cpp:
    # prefix '~', original extension followed by '.lck'. Check every source,
    # the project, and the conventional entry schematic even in a multi-root project.
    paths = {s.path for s in plan.snapshots} | {plan.project.with_suffix(".kicad_sch")}
    for path in sorted(paths):
        indicator = path.with_name("~" + path.name + ".lck")
        if _present(indicator):
            raise InvalidProject(f"detectable KiCad editor/project lock: {indicator}; close KiCad, "
                                 "then investigate the lock; do not automatically remove it")


def _check_physical_inputs(plan: NumberingPlan) -> None:
    seen = {}
    for snapshot in plan.snapshots:
        physical = snapshot.identity[:2]
        if not physical[1] or physical in seen:
            raise InvalidProject(f"ambiguous or duplicated physical source identity: {snapshot.path}")
        seen[physical] = snapshot.path


def _sync_directory(directory: Path) -> None:
    if os.name == "nt":
        return  # No portable Windows directory fsync; file fsync is still required.
    try:
        descriptor = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError as exc:
        if exc.errno not in {errno.EINVAL, errno.ENOTSUP, errno.ENOSYS}:
            raise


def _write(handle, data: bytes) -> None:
    if handle.write(data) != len(data):
        raise OSError("short file write")
    handle.flush()
    os.fsync(handle.fileno())


def _exclusive_file(path: Path):
    # Avoid exposing private schematic bytes with default umask-derived modes
    # while the backup is being written, before its original metadata is copied.
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
    return os.fdopen(descriptor, "wb")


def _verify_bytes(path: Path, expected: bytes) -> Snapshot:
    current = engine._read(path)
    if current.data != expected or current.digest != _digest(expected):
        raise InvalidProject(f"content/digest verification failed: {path}")
    return current


def _verify_sources(plan: NumberingPlan, installed: dict[Path, Snapshot]) -> None:
    for original in plan.snapshots:
        expected = installed.get(original.path, original)
        current = _verify_bytes(original.path, expected.data)
        if current.identity != expected.identity:
            raise InvalidProject(f"source identity or metadata changed: {original.path}")


def _owned_marker(marker: Path, owned: Snapshot) -> None:
    current = _verify_bytes(marker, owned.data)
    if current.identity != owned.identity:
        raise InvalidProject("operation marker identity changed; retaining recovery evidence")


def _backup_directory(root: Path) -> Path:
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    suffix = 0
    while True:
        path = root / (stamp if suffix == 0 else f"{stamp}-{suffix}")
        try:
            path.mkdir()  # Exclusive: never merge with or overwrite an existing backup.
            _sync_directory(root)
            return path
        except FileExistsError:
            suffix += 1


def _metadata(source: Path, target: Path, snapshot: Snapshot) -> None:
    shutil.copystat(source, target, follow_symlinks=False)
    current = target.stat()
    if (stat.S_IMODE(current.st_mode) != stat.S_IMODE(snapshot.identity[2])
            or current.st_mtime_ns != snapshot.identity[5]):
        raise InvalidProject(f"permission/mtime preservation failed: {target}")
    with target.open("rb") as handle:
        os.fsync(handle.fileno())


def _verify_metadata(current: Snapshot, original: Snapshot) -> None:
    if (stat.S_IMODE(current.identity[2]) != stat.S_IMODE(original.identity[2])
            or current.identity[5] != original.identity[5]):
        raise InvalidProject(f"source permissions or mtime changed: {current.path}")


def _backup(snapshot: Snapshot, destination: Path) -> None:
    engine._check_components(destination.parent)
    destination.parent.mkdir(parents=True, exist_ok=True)
    engine._check_components(destination.parent)
    with _exclusive_file(destination) as handle:
        _write(handle, snapshot.data)
    _metadata(snapshot.path, destination, snapshot)
    _verify_bytes(destination, snapshot.data)
    _sync_directory(destination.parent)


def _stage(snapshot: Snapshot, data: bytes, metadata_source: Path | None = None) -> Path:
    engine._check_components(snapshot.path.parent)
    descriptor, name = tempfile.mkstemp(prefix=f".{snapshot.path.name}.renumber-", suffix=".tmp",
                                        dir=snapshot.path.parent)
    path = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            _write(handle, data)
        _metadata(metadata_source or snapshot.path, path, snapshot)
        _verify_bytes(path, data)
        return path
    except Exception:
        path.unlink(missing_ok=True)
        raise


def _replace(staged: Path, original: Path) -> None:
    os.replace(staged, original)


def _verify_final(plan: NumberingPlan, candidates: dict[Path, bytes],
                  installed: dict[Path, Snapshot]) -> None:
    final = engine.build_plan(plan.project)  # The same graph and numbering implementation.
    expected = [(i.instance_path, i.hierarchy, i.source_file, i.new_page) for i in plan.items]
    actual = [(i.instance_path, i.hierarchy, i.source_file, i.old_page) for i in final.items]
    if final.edits or expected != actual or {s.path for s in final.snapshots} != {s.path for s in plan.snapshots}:
        raise InvalidProject("final instance graph/numbering verification failed")
    for original in plan.snapshots:
        # Exact candidate equality proves all non-page spans are unchanged;
        # unchanged sources (including .kicad_pro) must equal their original bytes.
        current = _verify_bytes(original.path, candidates.get(original.path, original.data))
        _verify_metadata(current, original)
    _verify_sources(plan, installed)


def _cleanup(staged: dict[Path, Path], candidates: dict[Path, bytes]) -> list[str]:
    failures = []
    for original, path in staged.items():
        try:
            if _present(path):
                _verify_bytes(path, candidates[original])
            path.unlink(missing_ok=True)
        except Exception as exc:
            failures.append(f"temporary-file cleanup failed ({path}): {exc}")
    return failures


def _rollback(plan: NumberingPlan, candidates: dict[Path, bytes], attempted: list[Path],
              backup: Path) -> list[str]:
    failures = []
    originals = {s.path: s for s in plan.snapshots}
    restored: dict[Path, Snapshot] = {}
    for path in reversed(attempted):
        temporary = None
        try:
            snapshot = originals[path]
            current = engine._read(path)
            if current.data == snapshot.data:
                _verify_metadata(current, snapshot)
                restored[path] = current  # A replacement that failed before changing this file.
                continue
            if current.data != candidates[path] or current.digest != _digest(candidates[path]):
                raise InvalidProject(f"third-party/unknown contents; refusing rollback overwrite: {path}")
            saved = backup / path.relative_to(plan.project.parent)
            _verify_bytes(saved, snapshot.data)
            temporary = _stage(snapshot, snapshot.data, saved)
            # Staging is not exclusion: recheck again immediately before restore.
            latest = _verify_bytes(path, candidates[path])
            if latest.identity != current.identity:
                raise InvalidProject(f"source changed during rollback: {path}")
            _replace(temporary, path)
            restored[path] = _verify_bytes(path, snapshot.data)
            _verify_metadata(restored[path], snapshot)
            _sync_directory(path.parent)
        except Exception as exc:
            failures.append(str(exc))
        finally:
            if temporary is not None:
                try:
                    if _present(temporary):
                        _verify_bytes(temporary, originals[path].data)
                    temporary.unlink(missing_ok=True)
                except Exception as exc:
                    failures.append(f"rollback staging cleanup failed: {exc}")
    try:
        _verify_sources(plan, restored)
    except Exception as exc:
        failures.append(f"complete original-source verification failed: {exc}")
    return failures


def apply_project(project_path: str | Path) -> ApplyResult:
    """Reload/recompute a plan and apply it. Caller must close all editors first.

    No stale plan can be supplied. BaseException/process death deliberately leaves
    the marker for manual inspection; ordinary detected failures attempt rollback.
    """
    project = engine.project_file_path(project_path)
    marker = _check_operation(project)  # Also blocks apparently correct interrupted projects.
    plan = engine.build_plan(project)
    _check_physical_inputs(plan)
    _check_locks(plan)
    _check_operation(project)
    if not plan.edits:
        return ApplyResult(plan, None)  # No mkdir, marker, staging, or backup on no-op.
    candidates = dict(engine.candidate_bytes(plan))
    if set(candidates) != set(plan.affected_files) or project in candidates:
        raise InvalidProject("candidate change set does not match approved page plan")
    _verify_sources(plan, {})
    root = marker.parent
    backup = None
    try:
        root.mkdir(exist_ok=True)
        engine._check_components(root)
        _sync_directory(project.parent)
        backup = _backup_directory(root)
        payload = json.dumps({
            "version": 1, "project": project.name,
            "backup": str(backup.relative_to(project.parent)),
            "files": [{"path": str(path.relative_to(project.parent)),
                       "original_sha256": next(s.digest for s in plan.snapshots if s.path == path),
                       "expected_sha256": _digest(candidates[path])} for path in sorted(candidates)]
        }, indent=2).encode("utf-8") + b"\n"
        # Acquire exclusion before backup/staging work. Partial writes also block
        # later applies; no other process may infer that an empty marker is safe.
        with _exclusive_file(marker) as handle:
            _write(handle, payload)
        owned = _verify_bytes(marker, payload)
        _sync_directory(root)
    except Exception as exc:
        if _present(marker):
            raise ApplyFailure(f"Operation setup failed: {exc}. " + _recovery_message(marker),
                               incomplete=True) from exc
        raise ApplyFailure(f"Operation setup failed before original modification: {exc}; "
                           f"backup location: {backup}") from exc

    staged: dict[Path, Path] = {}
    installed: dict[Path, Snapshot] = {}
    attempted: list[Path] = []
    try:
        originals = {s.path: s for s in plan.snapshots}
        for path in sorted(candidates):
            _backup(originals[path], backup / path.relative_to(project.parent))
        for path in sorted(candidates):
            staged[path] = _stage(originals[path], candidates[path])
        # Reopen the complete backup set after staging and before any replacement.
        backup_parents = {backup}
        for path in sorted(candidates):
            _verify_bytes(backup / path.relative_to(project.parent), originals[path].data)
            parent = (backup / path.relative_to(project.parent)).parent
            while parent != backup:
                backup_parents.add(parent)
                parent = parent.parent
        for parent in sorted(backup_parents, key=lambda p: len(p.parts), reverse=True):
            _sync_directory(parent)
        _verify_sources(plan, {})
        for path in sorted(candidates):
            _owned_marker(marker, owned)
            _check_locks(plan)
            _verify_sources(plan, installed)  # Includes project and unchanged reachable files.
            prepared = _verify_bytes(staged[path], candidates[path])
            _verify_metadata(prepared, originals[path])
            current = _verify_bytes(path, originals[path].data)
            if current.identity != originals[path].identity:
                raise InvalidProject(f"source changed immediately before replacement: {path}")
            attempted.append(path)  # Covers a replace that succeeds then raises/fails verification.
            _replace(staged[path], path)
            installed[path] = _verify_bytes(path, candidates[path])
            _verify_metadata(installed[path], originals[path])
            _sync_directory(path.parent)
        _verify_final(plan, candidates, installed)
        for path in sorted(candidates):
            _verify_bytes(backup / path.relative_to(project.parent), originals[path].data)
        _check_locks(plan)
        failures = _cleanup(staged, candidates)
        if failures:
            raise OSError("; ".join(failures))
        _owned_marker(marker, owned)
        marker.unlink()  # Last step, only after full verification. A crash may leave a stale marker.
        return ApplyResult(plan, backup)
    except Exception as exc:
        failures = _rollback(plan, candidates, attempted, backup)
        failures.extend(_cleanup(staged, candidates))
        if not failures:
            try:
                _owned_marker(marker, owned)
                marker.unlink()
            except Exception as cleanup_error:
                failures.append(f"marker cleanup failed: {cleanup_error}")
        if failures:
            raise ApplyFailure(f"Apply failed: {exc}. Restoration incomplete or uncertain: "
                               + "; ".join(failures) + ". " + _recovery_message(marker, backup),
                               incomplete=True) from exc
        raise ApplyFailure(f"Apply failed: {exc}. Complete original-source restoration verified; "
                           f"no further writes performed. Backup retained: {backup}") from exc
