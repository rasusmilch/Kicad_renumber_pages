"""Real disposable preparation/replacement with a deterministic _commit model.

The injected model rejects read-only regular-file descriptors. It is not native
Windows validation; separate native tests below are skipped elsewhere.
"""

from contextlib import contextmanager
import errno
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import unittest
from unittest.mock import patch

from kicad_renumber import apply as writer, engine
from kicad_renumber.sexpr import InvalidProject
from tests import test_preview as fixtures


class SynchronizationTests(unittest.TestCase):
    setUp = fixtures.PreviewTests.setUp
    write = fixtures.PreviewTests.write
    roots = fixtures.PreviewTests.roots
    single = fixtures.PreviewTests.single
    reused = fixtures.PreviewTests.reused

    @property
    def marker(self):
        return self.base / "backup-renumber/active-operation.json"

    def sources(self):
        return {p: (p.read_bytes(), stat.S_IMODE(p.stat().st_mode), p.stat().st_mtime_ns)
                for p in self.base.iterdir() if p.suffix in (".kicad_sch", ".kicad_pro")}

    @contextmanager
    def commit_model(self):
        actual_open, actual_fdopen, actual_sync = Path.open, os.fdopen, os.fsync
        handles, events = {}, []

        def opened(path, *args, **kwargs):
            handle = actual_open(path, *args, **kwargs)
            handles[handle.fileno()] = handle
            return handle

        def fdopened(*args, **kwargs):
            handle = actual_fdopen(*args, **kwargs)
            handles[handle.fileno()] = handle
            return handle

        def commit(descriptor):
            info = os.fstat(descriptor)
            if stat.S_ISREG(info.st_mode):
                handle = handles[descriptor]
                events.append((handle.name, handle.mode, handle.writable(), info.st_size))
                if not handle.writable():
                    raise OSError(errno.EBADF, "simulated Windows _commit on read-only descriptor")
            return actual_sync(descriptor)

        with patch.object(Path, "open", opened), patch.object(writer.os, "fdopen", side_effect=fdopened), \
                patch.object(writer.os, "fsync", side_effect=commit):
            yield events

    def test_readonly_descriptor_reproduces_ebadf_but_metadata_uses_writable(self):
        source = self.single()
        snapshot = engine._read(source)
        target = self.write("prepared.tmp", snapshot.data)
        with self.commit_model() as events:
            with target.open("rb") as handle:
                with self.assertRaises(OSError) as caught:
                    os.fsync(handle.fileno())
            self.assertEqual(caught.exception.errno, errno.EBADF)
            writer._metadata(source, target, snapshot)
        self.assertEqual(events[0][1:3], ("rb", False))
        self.assertTrue(all(e[2] for e in events[1:]))
        self.assertEqual(target.read_bytes(), snapshot.data)

    def test_backup_and_stage_sync_data_then_copied_metadata(self):
        source = self.single()
        snapshot = engine._read(source)
        destination = self.base / "saved/root.kicad_sch"
        candidate = snapshot.data.replace(b'(page "9")', b'(page "1")')
        with self.commit_model() as events:
            writer._backup(snapshot, destination)
            staged = writer._stage(snapshot, candidate)
        self.assertEqual([e[1] for e in events], ["wb", "rb+", "wb", "rb+"])
        self.assertTrue(all(e[2] for e in events))
        self.assertEqual(destination.read_bytes(), snapshot.data)
        self.assertEqual(staged.read_bytes(), candidate)
        for path in (destination, staged):
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), stat.S_IMODE(snapshot.identity[2]))
            self.assertEqual(path.stat().st_mtime_ns, snapshot.identity[5])

    def test_previous_metadata_policy_fails_in_backup_before_any_replacement(self):
        self.single()
        before, reached = self.sources(), []

        def previous_metadata(source, target, snapshot):
            writer.shutil.copystat(source, target, follow_symlinks=False)
            reached.append(target)
            with target.open("rb") as handle:
                os.fsync(handle.fileno())

        with self.commit_model(), patch.object(writer, "_metadata", side_effect=previous_metadata), \
                patch.object(writer, "_replace") as replace:
            with self.assertRaises(writer.ApplyFailure) as caught:
                writer.apply_project(self.project)
        self.assertFalse(caught.exception.incomplete)
        self.assertIn("Errno 9", str(caught.exception))
        self.assertEqual(len(reached), 1)
        self.assertIn("backup-renumber", reached[0].parts)
        replace.assert_not_called()
        self.assertEqual(self.sources(), before)

    def test_readonly_source_preparation_never_opens_source_for_write(self):
        source = self.single()
        source.chmod(stat.S_IREAD)
        snapshot = engine._read(source)
        before = self.sources()
        with self.commit_model() as events:
            actual_open = Path.open

            def source_read_only(path, *args, **kwargs):
                mode = args[0] if args else kwargs.get("mode", "r")
                if path == source:
                    self.assertFalse(any(flag in mode for flag in ("w", "a", "+")))
                return actual_open(path, *args, **kwargs)

            with patch.object(Path, "open", source_read_only):
                writer._backup(snapshot, self.base / "saved/original.kicad_sch")
                staged = writer._stage(snapshot, snapshot.data)
        self.assertTrue(all(e[2] for e in events))
        self.assertEqual(self.sources(), before)
        for path in (staged, self.base / "saved/original.kicad_sch"):
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), stat.S_IMODE(snapshot.identity[2]))
            self.assertEqual(path.read_bytes(), snapshot.data)
        # Model Windows deletion rules for a verified, tool-owned read-only stage.
        with patch.object(writer.sys, "platform", "win32"):
            self.assertEqual(writer._cleanup({source: staged}, {source: snapshot.data}), [])
        self.assertFalse(staged.exists())
        self.assertEqual(self.sources(), before)

    def test_windows_readonly_changed_source_refused_before_preparation(self):
        source = self.single()
        source.chmod(stat.S_IREAD)
        before = fixtures.inventory(self.base)
        with patch.object(writer.sys, "platform", "win32"), patch.object(writer, "_replace") as replace:
            with self.assertRaisesRegex(InvalidProject, "Windows read-only source.*before preparation"):
                writer.apply_project(self.project)
        replace.assert_not_called()
        self.assertEqual(fixtures.inventory(self.base), before)
        self.assertFalse(self.marker.parent.exists())

    def test_readonly_temporary_alias_never_changes_source_attributes(self):
        source = self.single()
        source.chmod(stat.S_IREAD)
        before = (source.read_bytes(), source.stat().st_mode, source.stat().st_mtime_ns)
        for kind in ("symlink", "hardlink"):
            with self.subTest(kind=kind):
                alias = self.base / f".root.renumber-{kind}.tmp"
                try:
                    if kind == "symlink":
                        alias.symlink_to(source)
                    else:
                        os.link(source, alias)
                except OSError as exc:
                    self.skipTest(f"{kind} creation unavailable: {exc}")
                try:
                    with patch.object(writer.sys, "platform", "win32"):
                        with self.assertRaises(InvalidProject):
                            writer._unlink_temporary(alias)
                    self.assertTrue(alias.exists())
                    self.assertEqual((source.read_bytes(), source.stat().st_mode, source.stat().st_mtime_ns), before)
                finally:
                    alias.unlink()

    def test_windows_readonly_noop_and_readonly_project_need_no_write_access(self):
        source = self.single("1")
        source.chmod(stat.S_IREAD)
        self.project.chmod(stat.S_IREAD)
        before = fixtures.inventory(self.base)
        with patch.object(writer.sys, "platform", "win32"):
            self.assertIsNone(writer.apply_project(self.project).backup)
        self.assertEqual(fixtures.inventory(self.base), before)

    @unittest.skipUnless(os.name == "posix", "actual POSIX replacement permissions")
    def test_posix_readonly_source_apply_preserves_mode_and_mtime(self):
        source = self.single()
        source.chmod(0o444)
        before = source.stat()
        writer.apply_project(self.project)
        self.assertEqual(source.stat().st_mode, before.st_mode)
        self.assertEqual(source.stat().st_mtime_ns, before.st_mtime_ns)
        self.assertIn(b'(page "1")', source.read_bytes())

    def test_ebadf_in_backup_or_stage_metadata_blocks_all_replacements(self):
        for phase in ("backup", "stage"):
            with self.subTest(phase=phase):
                self.single()
                before = self.sources()
                sync = writer._sync_file

                def fail(handle, path, stage):
                    if ("backup-renumber" in path.parts) == (phase == "backup"):
                        with patch.object(writer.os, "fsync", side_effect=OSError(errno.EBADF, "injected metadata fsync failure")):
                            return sync(handle, path, stage)
                    return sync(handle, path, stage)

                with patch.object(writer, "_sync_file", side_effect=fail), patch.object(writer, "_replace") as replace:
                    with self.assertRaises(writer.ApplyFailure) as caught:
                        writer.apply_project(self.project)
                self.assertFalse(caught.exception.incomplete)
                self.assertIn("metadata preparation failed", str(caught.exception))
                self.assertIn("file synchronization failed during metadata preservation", str(caught.exception))
                self.assertIn("Errno 9", str(caught.exception))
                self.assertEqual(self.sources(), before)
                replace.assert_not_called()
                self.assertFalse(self.marker.exists())

    def test_data_sync_failure_names_marker_backup_and_stage_paths(self):
        for phase in ("operation marker preparation", "backup preparation", "staged candidate preparation"):
            with self.subTest(phase=phase):
                self.single()
                before = self.sources()
                prepared = writer._write_prepared

                def fail(handle, data, path, stage):
                    if stage == phase:
                        with patch.object(writer.os, "fsync", side_effect=OSError(errno.EBADF, "injected fsync")):
                            return prepared(handle, data, path, stage)
                    return prepared(handle, data, path, stage)

                with patch.object(writer, "_write_prepared", side_effect=fail), patch.object(writer, "_replace") as replace:
                    with self.assertRaises(writer.ApplyFailure) as caught:
                        writer.apply_project(self.project)
                self.assertIn(phase, str(caught.exception))
                self.assertIn(str(self.base), str(caught.exception))
                self.assertIn("synchronization failed", str(caught.exception))
                self.assertEqual(self.sources(), before)
                replace.assert_not_called()
                if phase == "operation marker preparation":
                    self.assertTrue(caught.exception.incomplete)
                    self.assertTrue(self.marker.exists())
                    self.marker.unlink()  # Test-only resolution of setup failure for the next scenario.
                else:
                    self.assertFalse(caught.exception.incomplete)
                    self.assertFalse(self.marker.exists())

    def test_complete_verified_backup_set_precedes_first_replace(self):
        self.reused()
        originals = self.sources()
        replace = writer._replace
        first = True

        def check(staged, path):
            nonlocal first
            if first:
                first = False
                record = json.loads(self.marker.read_bytes())
                for entry in record["files"]:
                    source = self.base / entry["path"]
                    saved = self.base / record["backup"] / entry["path"]
                    data = saved.read_bytes()
                    self.assertEqual(data, originals[source][0])
                    self.assertEqual(hashlib.sha256(data).hexdigest(), entry["original_sha256"])
                self.assertEqual(self.sources(), originals)
            replace(staged, path)

        with self.commit_model(), patch.object(writer, "_replace", side_effect=check):
            writer.apply_project(self.project)
        self.assertFalse(first)

    def test_backup_verification_failure_blocks_replacement(self):
        self.single()
        before = self.sources()
        verify = writer._verify_bytes

        def fail(path, data):
            if "backup-renumber" in path.parts and path.name != writer.MARKER_NAME:
                raise InvalidProject("injected backup verification failure")
            return verify(path, data)

        with self.commit_model(), patch.object(writer, "_verify_bytes", side_effect=fail), \
                patch.object(writer, "_replace") as replace:
            with self.assertRaises(writer.ApplyFailure) as caught:
                writer.apply_project(self.project)
        self.assertFalse(caught.exception.incomplete)
        self.assertEqual(self.sources(), before)
        replace.assert_not_called()

    def test_later_failure_rolls_back_with_writable_sync_descriptors(self):
        self.reused()
        before = self.sources()
        real_replace, calls = writer._replace, 0

        def fail(staged, path):
            nonlocal calls
            calls += 1
            real_replace(staged, path)
            if calls == 2:
                raise OSError("injected failure after second actual replacement")

        with self.commit_model(), patch.object(writer, "_replace", side_effect=fail):
            with self.assertRaises(writer.ApplyFailure) as caught:
                writer.apply_project(self.project)
        self.assertFalse(caught.exception.incomplete)
        self.assertEqual(self.sources(), before)
        self.assertFalse(self.marker.exists())

    def test_failed_rollback_sync_retains_marker(self):
        self.single()
        real_replace, real_sync = writer._replace, writer._sync_file
        restoring = False

        def fail_replace(staged, path):
            nonlocal restoring
            real_replace(staged, path)
            restoring = True
            raise OSError("injected post-replace failure")

        def fail_sync(handle, path, stage):
            if restoring:
                raise OSError(errno.EBADF, "injected rollback metadata fsync failure")
            return real_sync(handle, path, stage)

        with patch.object(writer, "_replace", side_effect=fail_replace), \
                patch.object(writer, "_sync_file", side_effect=fail_sync):
            with self.assertRaises(writer.ApplyFailure) as caught:
                writer.apply_project(self.project)
        self.assertTrue(caught.exception.incomplete)
        self.assertTrue(self.marker.exists())
        self.assertTrue(list(self.marker.parent.glob("*/root.kicad_sch")))

    def test_failed_stage_cleanup_retains_marker_and_error_context(self):
        self.single()
        before = self.sources()
        metadata = writer._metadata

        def fail(source, target, snapshot):
            if target.suffix == ".tmp":
                raise OSError(errno.EBADF, "injected staging synchronization failure")
            return metadata(source, target, snapshot)

        with patch.object(writer, "_metadata", side_effect=fail), \
                patch.object(writer, "_unlink_temporary", side_effect=PermissionError("injected cleanup failure")), \
                patch.object(writer, "_replace") as replace:
            with self.assertRaises(writer.ApplyFailure) as caught:
                writer.apply_project(self.project)
        self.assertTrue(caught.exception.incomplete)
        self.assertIn("temporary cleanup failed", str(caught.exception))
        self.assertIn("staging synchronization failure", str(caught.exception))
        self.assertTrue(self.marker.exists())
        self.assertEqual(self.sources(), before)
        replace.assert_not_called()

    def test_success_then_true_noop_under_commit_model(self):
        self.single()
        with self.commit_model():
            writer.apply_project(self.project)
            before = fixtures.inventory(self.base)
            self.assertIsNone(writer.apply_project(self.project).backup)
            self.assertEqual(fixtures.inventory(self.base), before)

    @unittest.skipUnless(sys.platform == "win32", "native Windows synchronization runner unavailable")
    def test_native_windows_apply_and_noop(self):
        self.single()
        writer.apply_project(self.project)
        before = fixtures.inventory(self.base)
        self.assertIsNone(writer.apply_project(self.project).backup)
        self.assertEqual(fixtures.inventory(self.base), before)

    @unittest.skipUnless(sys.platform == "win32", "native Windows read-only attribute runner unavailable")
    def test_native_windows_readonly_metadata_sync(self):
        source = self.single()
        source.chmod(stat.S_IREAD)
        snapshot = engine._read(source)
        writer._backup(snapshot, self.base / "saved/root.kicad_sch")
        staged = writer._stage(snapshot, snapshot.data)
        self.assertFalse(staged.stat().st_mode & stat.S_IWRITE)
        self.assertEqual(staged.stat().st_mtime_ns, snapshot.identity[5])
        self.assertEqual(staged.read_bytes(), snapshot.data)
        before = self.sources()
        with self.assertRaisesRegex(InvalidProject, "Windows read-only source"):
            writer.apply_project(self.project)
        self.assertEqual(self.sources(), before)


if __name__ == "__main__":
    unittest.main()
