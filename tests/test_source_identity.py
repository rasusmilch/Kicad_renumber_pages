"""Windows identity policy simulated on real temporary files; no customer inputs."""

from contextlib import contextmanager, redirect_stdout
from dataclasses import replace
import hashlib
import io
import os
from pathlib import Path
import stat
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from kicad_renumber import apply as writer, cli, engine
from kicad_renumber.sexpr import InvalidProject
from tests import test_preview as fixtures


# Independent field names, not derived from the implementation under test.
FIELDS = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")


def changed_stat(info, **changes):
    return SimpleNamespace(**({name: getattr(info, name) for name in FIELDS} | changes))


class SourceIdentityTests(unittest.TestCase):
    setUp = fixtures.PreviewTests.setUp
    write = fixtures.PreviewTests.write
    roots = fixtures.PreviewTests.roots
    single = fixtures.PreviewTests.single

    def windows_handle_stats(self):
        actual = os.fstat

        def mismatched(descriptor):
            info = actual(descriptor)
            return changed_stat(info, st_ctime_ns=info.st_ctime_ns + 1000000000)

        return patch.object(engine.os, "fstat", side_effect=mismatched)

    def test_windows_path_handle_ctime_mismatch_accepts_stable_bytes(self):
        source = self.single()
        before = source.lstat()
        with patch.object(engine.sys, "platform", "win32"), self.windows_handle_stats():
            snapshot = engine._read(source)
            other = changed_stat(before, st_ctime_ns=before.st_ctime_ns + 2)
            self.assertEqual(snapshot.identity, engine._identity(other))
        self.assertEqual(snapshot.data, source.read_bytes())
        self.assertEqual(snapshot.digest, hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertEqual(snapshot.identity, tuple(getattr(before, f) for f in FIELDS[:-1]) + (0,))
        after = source.lstat()
        self.assertEqual(tuple(getattr(before, f) for f in FIELDS), tuple(getattr(after, f) for f in FIELDS))

    def test_retained_fields_detected_while_opening_on_both_platforms(self):
        source = self.single()
        before = source.lstat()
        for platform in ("win32", "linux"):
            for field in FIELDS[:-1]:
                with self.subTest(platform=platform, field=field):
                    fake = changed_stat(before, **{field: getattr(before, field) + 1})
                    with patch.object(engine.sys, "platform", platform), \
                            patch.object(engine.os, "fstat", return_value=fake):
                        with self.assertRaisesRegex(InvalidProject, f"while opening:.*{field}"):
                            engine._read(source)

    def test_diagnostic_identifies_reading_stage_and_multiple_fields(self):
        source = self.single()
        before = source.lstat()
        opening = changed_stat(before, st_ctime_ns=before.st_ctime_ns + 1)
        reading = changed_stat(opening, st_size=before.st_size + 1, st_mtime_ns=before.st_mtime_ns + 1)
        with patch.object(engine.sys, "platform", "win32"), \
                patch.object(engine.os, "fstat", side_effect=[opening, reading]):
            with self.assertRaisesRegex(InvalidProject, "while reading:.*st_size.*st_mtime_ns"):
                engine._read(source)

    def test_post_close_path_replacement_detected_on_windows_policy(self):
        source = self.single()
        replacement = self.write("replacement.tmp", source.read_bytes())
        original = source.lstat()
        os.utime(replacement, ns=(original.st_atime_ns, original.st_mtime_ns))
        replacement.chmod(stat.S_IMODE(original.st_mode))
        actual_open = Path.open

        @contextmanager
        def replace_after_close(path, *args, **kwargs):
            with actual_open(path, *args, **kwargs) as handle:
                yield handle
            if path == source:
                os.replace(replacement, source)

        with patch.object(engine.sys, "platform", "win32"), \
                patch.object(Path, "open", replace_after_close):
            with self.assertRaisesRegex(InvalidProject, "post-close path check.*st_ino"):
                engine._read(source)

    def test_posix_ctime_only_mismatch_still_rejected(self):
        source = self.single()
        with patch.object(engine.sys, "platform", "linux"), self.windows_handle_stats():
            with self.assertRaisesRegex(InvalidProject, "while opening:.*st_ctime_ns"):
                engine._read(source)

    @unittest.skipUnless(os.name == "posix", "requires actual POSIX change-time semantics")
    def test_actual_posix_ctime_only_change_detected_between_snapshots(self):
        source = self.single()
        plan = engine.build_plan(self.project)
        before = source.stat()
        # Restore permissions and retain contents/mtime; change-time must still protect this read.
        source.chmod(stat.S_IMODE(before.st_mode) ^ stat.S_IXUSR)
        source.chmod(stat.S_IMODE(before.st_mode))
        if source.stat().st_ctime_ns == before.st_ctime_ns:
            self.skipTest("filesystem did not expose a distinct ctime for chmod")
        with self.assertRaisesRegex(InvalidProject, "apply source verification:.*st_ctime_ns"):
            writer._verify_sources(plan, {})

    def test_windows_snapshot_rechecks_retain_every_other_field(self):
        source = self.single()
        with patch.object(engine.sys, "platform", "win32"):
            plan = engine.build_plan(self.project)
            before = source.lstat()
            for field in FIELDS[:-1]:
                with self.subTest(field=field):
                    actual_read = engine._read

                    def changed(path):
                        snapshot = actual_read(path)
                        if path == source:
                            info = changed_stat(before, **{field: getattr(before, field) + 1})
                            return replace(snapshot, identity=engine._identity(info))
                        return snapshot

                    with patch.object(engine, "_read", side_effect=changed):
                        with self.assertRaisesRegex(InvalidProject, f"apply source verification:.*{field}"):
                            writer._verify_sources(plan, {})

    def test_windows_snapshot_recheck_accepts_changed_path_ctime_only(self):
        self.single()
        actual_lstat = Path.lstat

        def changed_ctime(path, *args, **kwargs):
            info = actual_lstat(path, *args, **kwargs)
            return changed_stat(info, st_ctime_ns=info.st_ctime_ns + 1000000000)

        with patch.object(engine.sys, "platform", "win32"):
            plan = engine.build_plan(self.project)
            with patch.object(Path, "lstat", changed_ctime):
                writer._verify_sources(plan, {})

    def test_real_size_and_mtime_changes_detected_on_windows_policy(self):
        for field in ("st_size", "st_mtime_ns"):
            with self.subTest(field=field), patch.object(engine.sys, "platform", "win32"):
                source = self.single()
                plan = engine.build_plan(self.project)
                before = source.stat()
                if field == "st_size":
                    source.write_bytes(source.read_bytes() + b"\n")
                    os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns))
                else:
                    os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns + 1000000000))
                # Metadata is checked before content here, independently of the digest guard.
                with self.assertRaisesRegex(InvalidProject, f"real source recheck:.*{field}"):
                    engine._verify_identity(next(s.identity for s in plan.snapshots if s.path == source),
                                            engine._read(source).identity, path=source, stage="real source recheck")

    def rewrite_with_preserved_size_mtime(self, source):
        before = source.stat()
        data = source.read_bytes()
        changed = data.replace(b'(page "9")', b'(page "8")')
        self.assertNotEqual(data, changed)
        self.assertEqual(len(data), len(changed))
        source.write_bytes(changed)
        os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns))

    def test_real_same_size_same_mtime_content_change_detected_by_apply(self):
        source = self.single()
        with patch.object(engine.sys, "platform", "win32"):
            plan = engine.build_plan(self.project)
            self.rewrite_with_preserved_size_mtime(source)
            with self.assertRaisesRegex(InvalidProject, "content/digest verification failed"):
                writer._verify_sources(plan, {})

    def test_real_same_size_same_mtime_content_change_detected_during_analysis(self):
        source = self.single()
        candidates = engine.candidate_bytes

        def edit_after_plan(plan):
            result = candidates(plan)
            self.rewrite_with_preserved_size_mtime(source)
            return result

        with patch.object(engine.sys, "platform", "win32"), \
                patch.object(engine, "candidate_bytes", side_effect=edit_after_plan):
            with self.assertRaisesRegex(InvalidProject, "during analysis:.*content bytes differ"):
                engine.build_plan(self.project)

    def test_preview_under_windows_ctime_mismatch_is_read_only(self):
        self.single()
        before = fixtures.inventory(self.base)
        output = io.StringIO()
        with patch.object(engine.sys, "platform", "win32"), self.windows_handle_stats(), redirect_stdout(output):
            self.assertEqual(cli.main([str(self.project)]), 0)
        self.assertIn("1 sheets, 1 page changes, 1 affected files", output.getvalue())
        self.assertEqual(fixtures.inventory(self.base), before)

    def test_apply_backups_and_noop_under_windows_ctime_mismatch(self):
        source = self.single()
        original = source.read_bytes()
        project = self.project.read_bytes()
        with patch.object(engine.sys, "platform", "win32"), self.windows_handle_stats():
            result = writer.apply_project(self.project)
            self.assertEqual((result.backup / source.name).read_bytes(), original)
            self.assertEqual(self.project.read_bytes(), project)
            self.assertIn(b'(page "1")', source.read_bytes())
            before = fixtures.inventory(self.base)
            self.assertIsNone(writer.apply_project(self.project).backup)
            self.assertEqual(fixtures.inventory(self.base), before)

    def test_rollback_under_windows_ctime_mismatch(self):
        source = self.single()
        original = source.read_bytes()
        actual = writer._replace
        calls = 0

        def interrupted(staged, path):
            nonlocal calls
            calls += 1
            actual(staged, path)
            if calls == 1:
                raise OSError("injected failure after real replacement")

        with patch.object(engine.sys, "platform", "win32"), self.windows_handle_stats(), \
                patch.object(writer, "_replace", side_effect=interrupted):
            with self.assertRaises(writer.ApplyFailure) as caught:
                writer.apply_project(self.project)
        self.assertFalse(caught.exception.incomplete)
        self.assertIn("restoration verified", str(caught.exception))
        self.assertEqual(source.read_bytes(), original)
        self.assertEqual(calls, 2)
        self.assertFalse((self.base / "backup-renumber/active-operation.json").exists())
        saved = list((self.base / "backup-renumber").rglob(source.name))
        self.assertEqual([p.read_bytes() for p in saved], [original])

    @unittest.skipUnless(sys.platform == "win32", "genuine Windows runner unavailable")
    def test_native_windows_lstat_fstat_read(self):
        source = self.single()
        before = source.lstat()
        with source.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            data = handle.read()
            after_read = os.fstat(handle.fileno())
        self.assertEqual(engine._identity(before), engine._identity(opened))
        self.assertEqual(engine._identity(opened), engine._identity(after_read))
        self.assertEqual(engine._identity(before), engine._identity(source.lstat()))
        self.assertEqual(engine._read(source).data, data)


if __name__ == "__main__":
    unittest.main()
