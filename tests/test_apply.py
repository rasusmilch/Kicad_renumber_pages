"""Actual temporary-file apply plus injected I/O failures; never customer data."""

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from unittest.mock import patch
import unittest

from kicad_renumber import apply as writer, cli, engine
from kicad_renumber.sexpr import InvalidProject
from tests import test_preview as fixtures


class ApplyTests(unittest.TestCase):
    # Share only fixture builders, not inherited test cases or product logic.
    setUp = fixtures.PreviewTests.setUp
    write = fixtures.PreviewTests.write
    roots = fixtures.PreviewTests.roots
    single = fixtures.PreviewTests.single
    reused = fixtures.PreviewTests.reused
    run_cli = fixtures.PreviewTests.run_cli

    @property
    def marker(self):
        return self.base / writer.BACKUP_DIRECTORY / writer.MARKER_NAME

    def sources(self):
        return {p: (p.read_bytes(), stat.S_IMODE(p.stat().st_mode), p.stat().st_mtime_ns)
                for p in self.base.rglob("*") if p.is_file() and writer.BACKUP_DIRECTORY not in p.parts}

    def assert_sources(self, before):
        self.assertEqual(self.sources(), before)

    def assert_clean_failure(self, operation, before):
        with self.assertRaises(writer.ApplyFailure) as caught:
            operation()
        self.assertFalse(caught.exception.incomplete, str(caught.exception))
        self.assertIn("restoration verified", str(caught.exception))
        self.assert_sources(before)
        self.assertFalse(self.marker.exists())

    def fail_replacement(self, number=2, after=False):
        original = writer._replace
        calls = 0

        def replace(staged, destination):
            nonlocal calls
            calls += 1
            if calls == number:
                if after:
                    original(staged, destination)
                raise OSError("injected replacement failure")
            original(staged, destination)

        return replace

    def test_single_root_success_and_repeat_is_full_noop(self):
        source = self.single()
        project_bytes = self.project.read_bytes()
        result = writer.apply_project(self.project)
        self.assertIsNotNone(result.backup)
        self.assertEqual(result.plan.change_count, 1)
        self.assertIn(b'(page "1")', source.read_bytes())
        self.assertIn(b'(page "9")', (result.backup / source.name).read_bytes())
        self.assertEqual(self.project.read_bytes(), project_bytes)
        self.assertFalse(self.marker.exists())
        before = fixtures.inventory(self.base)
        again = writer.apply_project(self.project)
        self.assertIsNone(again.backup)
        self.assertFalse(again.plan.edits)
        self.assertEqual(fixtures.inventory(self.base), before)

    def test_success_exact_candidates_multiroot_reuse_drawings_and_unrelated_file(self):
        self.reused()
        drawings = (fixtures.drawing_rectangle() + fixtures.drawing_table()).encode()
        for path in self.base.glob("*.kicad_sch"):
            path.write_bytes(path.read_bytes().replace(b'(paper "A4")', b'(paper "A4")' + drawings))
        unrelated = self.write("unused.kicad_sch", b"not a schematic; deliberately unrelated")
        before = self.sources()
        plan = engine.build_plan(self.project)
        candidates = dict(engine.candidate_bytes(plan))
        result = writer.apply_project(self.project)
        self.assertEqual(result.plan.items, plan.items)
        for snapshot in plan.snapshots:
            self.assertEqual(snapshot.path.read_bytes(), candidates.get(snapshot.path, snapshot.data))
            if snapshot.path.suffix == ".kicad_sch":
                self.assertIn(drawings, snapshot.path.read_bytes())
        self.assertEqual(unrelated.read_bytes(), before[unrelated][0])
        backed = {p.relative_to(result.backup) for p in result.backup.rglob("*") if p.is_file()}
        self.assertEqual(backed, {p.relative_to(self.base) for p in plan.affected_files})
        for relative in backed:
            self.assertEqual((result.backup / relative).read_bytes(), before[self.base / relative][0])
        self.assertNotIn(Path("demo.kicad_pro"), backed)
        self.assertNotIn(Path("leaf.kicad_sch"), backed)
        self.assertNotIn(Path("unused.kicad_sch"), backed)
        self.assertEqual(engine.build_plan(self.project).change_count, 0)

    def test_mismatched_root_uuid_and_nil_fallback_apply(self):
        for registered in [0, 8]:
            with self.subTest(registered=registered):
                self.roots(("root.kicad_sch", "Root", registered))
                effective = registered or 1
                child = fixtures.sheet(10, "Child", "child.kicad_sch", [(fixtures.ipath(effective), "old")])
                self.write("root.kicad_sch", fixtures.schematic(1, sheets=[child]))
                self.write("child.kicad_sch", fixtures.schematic(2, None))
                original_project = self.project.read_bytes()
                result = writer.apply_project(self.project)
                self.assertEqual(result.plan.items[1].instance_path, (fixtures.uid(effective), fixtures.uid(10)))
                self.assertEqual(engine.build_plan(self.project).change_count, 0)
                self.assertEqual(self.project.read_bytes(), original_project)
                self.assertIn(f'(uuid "{fixtures.uid(1)}")'.encode(), (self.base / "root.kicad_sch").read_bytes())

    def test_backup_relative_layout_permissions_and_mtime(self):
        self.roots(("sub/nested/root.kicad_sch", "Root", 1))
        source = self.write("sub/nested/root.kicad_sch", fixtures.schematic(1))
        source.chmod(0o640)
        os.utime(source, ns=(1_700_000_000_123456789, 1_700_000_000_123456789))
        before = source.stat()
        result = writer.apply_project(self.project)
        saved = result.backup / "sub/nested/root.kicad_sch"
        self.assertTrue(saved.is_file())
        self.assertEqual(stat.S_IMODE(source.stat().st_mode), stat.S_IMODE(before.st_mode))
        self.assertEqual(source.stat().st_mtime_ns, before.st_mtime_ns)
        self.assertEqual(stat.S_IMODE(saved.stat().st_mode), stat.S_IMODE(before.st_mode))
        self.assertEqual(saved.stat().st_mtime_ns, before.st_mtime_ns)

    def test_all_backups_verified_before_first_original_replacement(self):
        self.reused()
        plan = engine.build_plan(self.project)
        original = writer._replace
        seen = 0

        def replace(staged, destination):
            nonlocal seen
            if seen == 0:
                record = json.loads(self.marker.read_bytes())
                backup = self.base / record["backup"]
                for snapshot in plan.snapshots:
                    self.assertEqual(snapshot.path.read_bytes(), snapshot.data)
                    if snapshot.path in plan.affected_files:
                        self.assertEqual((backup / snapshot.path.relative_to(self.base)).read_bytes(), snapshot.data)
                self.assertEqual(len(record["files"]), 3)
                self.assertEqual({f["path"] for f in record["files"]},
                                 {str(p.relative_to(self.base)) for p in plan.affected_files})
                for entry in record["files"]:
                    self.assertEqual(entry["original_sha256"], writer._digest((backup / entry["path"]).read_bytes()))
                    self.assertEqual(entry["expected_sha256"], writer._digest(dict(engine.candidate_bytes(plan))[self.base / entry["path"]]))
            seen += 1
            original(staged, destination)

        with patch.object(writer, "_replace", side_effect=replace):
            writer.apply_project(self.project)
        self.assertEqual(seen, 3)

    def test_timestamp_collisions_preserve_existing_backups(self):
        self.single()
        stamp = "2026-11-10_12-34-56"
        old = self.base / writer.BACKUP_DIRECTORY / stamp
        old.mkdir(parents=True)
        (old / "sentinel").write_bytes(b"old verified backup")
        second = old.with_name(stamp + "-1")
        second.mkdir()
        (second / "sentinel").write_bytes(b"another prior backup")
        before = fixtures.inventory(old), fixtures.inventory(second)
        with patch.object(writer, "datetime") as clock:
            clock.now.return_value.strftime.return_value = stamp
            result = writer.apply_project(self.project)
        self.assertEqual(result.backup.name, stamp + "-2")
        self.assertEqual((fixtures.inventory(old), fixtures.inventory(second)), before)

    def test_preview_and_apply_noops_create_nothing(self):
        self.single("1")
        before = fixtures.inventory(self.base)
        for arguments in [(self.project,), (self.project, "--apply")]:
            result = self.run_cli(*arguments)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("already correct", result.stdout)
        self.assertEqual(fixtures.inventory(self.base), before)
        self.assertFalse((self.base / writer.BACKUP_DIRECTORY).exists())

    def test_existing_marker_blocks_even_noop_without_deletion(self):
        self.single("1")
        self.marker.parent.mkdir()
        for content in [b"", b"{broken", json.dumps({"backup": "backup-renumber/old"}).encode()]:
            with self.subTest(content=content):
                self.marker.write_bytes(content)
                before = fixtures.inventory(self.base)
                result = self.run_cli(self.project, "--apply")
                self.assertEqual(result.returncode, 5)
                self.assertIn("manual recovery", result.stderr)
                self.assertIn("original_sha256", result.stderr)
                self.assertEqual(fixtures.inventory(self.base), before)

    def test_active_marker_excludes_another_cooperating_apply(self):
        self.single()
        backup = writer._backup

        def overlap(snapshot, destination):
            before = fixtures.inventory(self.base)
            with self.assertRaises(writer.ApplyFailure) as caught:
                writer.apply_project(self.project)
            self.assertTrue(caught.exception.incomplete)
            self.assertEqual(fixtures.inventory(self.base), before)
            backup(snapshot, destination)

        with patch.object(writer, "_backup", side_effect=overlap):
            writer.apply_project(self.project)

    def test_detectable_editor_and_project_locks_block_apply(self):
        self.reused()
        for filename in ["~demo.kicad_pro.lck", "~demo.kicad_sch.lck", "~a.kicad_sch.lck",
                         "~shared.kicad_sch.lck", "~leaf.kicad_sch.lck"]:
            with self.subTest(filename=filename):
                lock = self.write(filename, b"lock contents are not an unlock authorization")
                before = fixtures.inventory(self.base)
                result = self.run_cli(self.project, "--apply")
                self.assertEqual(result.returncode, 2)
                self.assertIn("detectable KiCad", result.stderr)
                self.assertIn("cannot prove", result.stderr)
                self.assertEqual(fixtures.inventory(self.base), before)
                lock.unlink()

    def test_lock_appearing_after_staging_blocks_writes(self):
        self.single()
        before = self.sources()
        stage = writer._stage
        lock = self.base / "~root.kicad_sch.lck"

        def create_lock(*args):
            temporary = stage(*args)
            lock.write_bytes(b"editor opened")
            return temporary

        with patch.object(writer, "_stage", side_effect=create_lock):
            with self.assertRaises(writer.ApplyFailure) as caught:
                writer.apply_project(self.project)
        self.assertFalse(caught.exception.incomplete)
        lock.unlink()
        self.assert_sources(before)

    def test_source_change_after_planning_blocks_before_backup_creation(self):
        source = self.single()
        build = engine.build_plan

        def changed(path):
            plan = build(path)
            source.write_bytes(source.read_bytes() + b"\n")
            return plan

        with patch.object(engine, "build_plan", side_effect=changed):
            with self.assertRaises(InvalidProject):
                writer.apply_project(self.project)
        self.assertTrue(source.read_bytes().endswith(b"\n\n"))
        self.assertFalse(self.marker.parent.exists())

    def test_source_change_immediately_before_replace_is_never_overwritten(self):
        source = self.single()
        verify = writer._verify_bytes
        external = source.read_bytes() + b"\n"
        changed = False

        def intervene(path, expected):
            nonlocal changed
            result = verify(path, expected)
            if path.suffix == ".tmp" and not changed:
                # _stage also verifies its temporary; intervene on the next
                # verification immediately before the forward replacement.
                if getattr(intervene, "staged", False):
                    source.write_bytes(external)
                    changed = True
                intervene.staged = True
            return result

        with patch.object(writer, "_verify_bytes", side_effect=intervene), patch.object(writer, "_replace") as replace:
            with self.assertRaises(writer.ApplyFailure) as caught:
                writer.apply_project(self.project)
        self.assertTrue(caught.exception.incomplete)
        self.assertTrue(changed)
        replace.assert_not_called()
        self.assertEqual(source.read_bytes(), external)
        self.assertTrue(self.marker.exists())

    def test_project_and_unchanged_referenced_file_changes_stop_partial_apply(self):
        for filename in ["demo.kicad_pro", "leaf.kicad_sch"]:
            with self.subTest(filename=filename):
                self.reused()
                before = self.sources()
                original_replace = writer._replace
                external_path = self.base / filename
                external = external_path.read_bytes() + b"\n"
                changed = False

                def intervene(staged, destination):
                    nonlocal changed
                    original_replace(staged, destination)
                    if not changed:
                        external_path.write_bytes(external)
                        changed = True

                with patch.object(writer, "_replace", side_effect=intervene):
                    with self.assertRaises(writer.ApplyFailure) as caught:
                        writer.apply_project(self.project)
                self.assertTrue(caught.exception.incomplete)
                self.assertEqual(external_path.read_bytes(), external)
                for path, (data, _, _) in before.items():
                    if path != external_path:
                        self.assertEqual(path.read_bytes(), data)
                self.assertTrue(self.marker.exists())
                # Test-only resolution so the second disposable scenario can run.
                self.marker.unlink()

    def test_backup_creation_failure_does_not_modify_originals(self):
        self.reused()
        before = self.sources()
        real = writer._backup
        calls = 0

        def fail(snapshot, destination):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise PermissionError("injected backup creation failure")
            real(snapshot, destination)

        with patch.object(writer, "_backup", side_effect=fail), patch.object(writer, "_replace") as replace:
            self.assert_clean_failure(lambda: writer.apply_project(self.project), before)
        replace.assert_not_called()

    def test_backup_write_failure_does_not_modify_originals(self):
        self.single()
        before = self.sources()
        backup = writer._backup

        def fail(handle, data):
            handle.write(data[:10])
            raise OSError("injected partial backup write")

        def backup_failure(*args):
            with patch.object(writer, "_write", side_effect=fail):
                return backup(*args)

        with patch.object(writer, "_backup", side_effect=backup_failure):
            self.assert_clean_failure(lambda: writer.apply_project(self.project), before)

    def test_corrupted_backup_is_rejected_before_replacement(self):
        self.single()
        before = self.sources()
        real = writer._backup

        def corrupt(snapshot, destination):
            real(snapshot, destination)
            destination.write_bytes(b"corrupted after first verification")

        with patch.object(writer, "_backup", side_effect=corrupt), patch.object(writer, "_replace") as replace:
            self.assert_clean_failure(lambda: writer.apply_project(self.project), before)
        replace.assert_not_called()

    def test_temporary_file_creation_failure(self):
        self.single()
        before = self.sources()
        with patch.object(writer.tempfile, "mkstemp", side_effect=PermissionError("injected mkstemp")):
            self.assert_clean_failure(lambda: writer.apply_project(self.project), before)

    def test_temporary_file_write_and_sync_failures(self):
        for failure in ["write", "sync"]:
            with self.subTest(failure=failure):
                self.single()
                before = self.sources()
                stage = writer._stage

                def fail(*args):
                    owner, name = (writer, "_write") if failure == "write" else (writer.os, "fsync")
                    with patch.object(owner, name, side_effect=OSError("injected staging " + failure)):
                        return stage(*args)

                with patch.object(writer, "_stage", side_effect=fail):
                    self.assert_clean_failure(lambda: writer.apply_project(self.project), before)

    def test_staged_candidate_verification_failure(self):
        self.single()
        before = self.sources()
        real = writer._verify_bytes

        def fail(path, expected):
            if path.suffix == ".tmp":
                raise InvalidProject("injected staged candidate verification failure")
            return real(path, expected)

        with patch.object(writer, "_verify_bytes", side_effect=fail):
            self.assert_clean_failure(lambda: writer.apply_project(self.project), before)

    def test_replacement_failures_restore_every_original(self):
        for number, after in [(1, False), (2, False), (2, True), (3, False)]:
            with self.subTest(number=number, after=after):
                self.reused()
                before = self.sources()
                with patch.object(writer, "_replace", side_effect=self.fail_replacement(number, after)):
                    self.assert_clean_failure(lambda: writer.apply_project(self.project), before)

    def test_installed_verification_failure_rolls_back(self):
        source = self.single()
        before = self.sources()
        verify = writer._verify_bytes
        replacement_started = False
        failed = False
        real_replace = writer._replace

        def replace(staged, path):
            nonlocal replacement_started
            real_replace(staged, path)
            replacement_started = True

        def fail(path, expected):
            nonlocal failed
            if path == source and replacement_started and not failed:
                failed = True
                raise OSError("injected installed-file verification error")
            return verify(path, expected)

        with patch.object(writer, "_replace", side_effect=replace), patch.object(writer, "_verify_bytes", side_effect=fail):
            self.assert_clean_failure(lambda: writer.apply_project(self.project), before)

    def test_directory_sync_failure_after_replace_rolls_back(self):
        self.single()
        before = self.sources()
        replaced = False
        failed = False
        real_replace, sync = writer._replace, writer._sync_directory

        def replace(staged, path):
            nonlocal replaced
            real_replace(staged, path)
            replaced = True

        def fail(path):
            nonlocal failed
            if replaced and not failed:
                failed = True
                raise OSError("injected directory sync failure")
            return sync(path)

        with patch.object(writer, "_replace", side_effect=replace), patch.object(writer, "_sync_directory", side_effect=fail):
            self.assert_clean_failure(lambda: writer.apply_project(self.project), before)

    def test_final_graph_verification_failure_restores_all_files(self):
        self.reused()
        before = self.sources()
        with patch.object(writer, "_verify_final", side_effect=InvalidProject("injected final graph failure")):
            self.assert_clean_failure(lambda: writer.apply_project(self.project), before)

    def test_rollback_write_failure_retains_marker_and_backup(self):
        self.reused()
        real = writer._replace
        calls = 0

        def fail(staged, path):
            nonlocal calls
            calls += 1
            if calls >= 2:
                raise OSError("injected forward and rollback replacement failure")
            real(staged, path)

        with patch.object(writer, "_replace", side_effect=fail):
            with self.assertRaises(writer.ApplyFailure) as caught:
                writer.apply_project(self.project)
        self.assertTrue(caught.exception.incomplete)
        self.assertTrue(self.marker.exists())
        record = json.loads(self.marker.read_bytes())
        self.assertTrue((self.base / record["backup"] / "a.kicad_sch").exists())
        self.assertEqual(self.run_cli(self.project, "--apply").returncode, 5)

    def test_third_party_change_is_never_overwritten_during_rollback(self):
        self.reused()
        first = self.base / "a.kicad_sch"
        external = b"third-party unsaved design replacement"
        real = writer._replace
        calls = 0

        def intervene(staged, path):
            nonlocal calls
            calls += 1
            if calls == 2:
                first.write_bytes(external)
                raise OSError("injected second replace failure with third-party edit")
            real(staged, path)

        with patch.object(writer, "_replace", side_effect=intervene):
            with self.assertRaises(writer.ApplyFailure) as caught:
                writer.apply_project(self.project)
        self.assertTrue(caught.exception.incomplete)
        self.assertIn("refusing rollback overwrite", str(caught.exception))
        self.assertEqual(first.read_bytes(), external)
        self.assertTrue(self.marker.exists())

    def test_corrupted_backup_prevents_unsafe_rollback(self):
        self.reused()
        real = writer._replace
        calls = 0

        def intervene(staged, path):
            nonlocal calls
            calls += 1
            if calls == 2:
                record = json.loads(self.marker.read_bytes())
                (self.base / record["backup"] / "a.kicad_sch").write_bytes(b"corrupt saved bytes")
                raise OSError("injected failure after backup corruption")
            real(staged, path)

        with patch.object(writer, "_replace", side_effect=intervene):
            with self.assertRaises(writer.ApplyFailure) as caught:
                writer.apply_project(self.project)
        self.assertTrue(caught.exception.incomplete)
        self.assertTrue(self.marker.exists())

    def test_marker_creation_write_failure_preserves_evidence_and_originals(self):
        self.single()
        before = self.sources()
        with patch.object(writer, "_write", side_effect=OSError("injected marker write failure")):
            with self.assertRaises(writer.ApplyFailure) as caught:
                writer.apply_project(self.project)
        self.assertTrue(caught.exception.incomplete)
        self.assert_sources(before)
        self.assertTrue(self.marker.exists())

    def test_backup_root_symlink_is_rejected(self):
        self.single()
        destination = self.base / "other"
        destination.mkdir()
        try:
            self.marker.parent.symlink_to(destination, target_is_directory=True)
        except OSError:
            self.skipTest("symlink creation unavailable")
        before = fixtures.inventory(destination)
        with self.assertRaises(InvalidProject):
            writer.apply_project(self.project)
        self.assertEqual(fixtures.inventory(destination), before)

    def test_cli_success_and_failure_statuses(self):
        self.single()
        result = self.run_cli(self.project, "--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Applied and verified", result.stdout)
        self.assertIn("Verified backups retained", result.stdout)
        self.assertIn("cannot prove", result.stderr)
        self.single()
        out, err = io.StringIO(), io.StringIO()
        with patch.object(writer, "_replace", side_effect=OSError("injected CLI failure")), redirect_stdout(out), redirect_stderr(err):
            self.assertEqual(cli.main([str(self.project), "--apply"]), 4)
        self.assertIn("Application failed", err.getvalue())
        self.assertIn("restoration verified", err.getvalue())
        self.assertEqual(out.getvalue(), "")

    def test_process_death_between_replacements_blocks_future_apply(self):
        self.reused()
        before = self.sources()
        script = '''
import os,sys
from kicad_renumber import apply as writer
original=writer._replace
def interrupted(staged,path):
    original(staged,path)
    os._exit(73)
writer._replace=interrupted
writer.apply_project(sys.argv[1])
'''
        result = subprocess.run([sys.executable, "-B", "-c", script, str(self.project)],
                                cwd=fixtures.LAUNCHER.parent, capture_output=True, text=True)
        self.assertEqual(result.returncode, 73, result.stderr)
        self.assertTrue(self.marker.exists())
        record = json.loads(self.marker.read_bytes())
        after_count = 0
        for entry in record["files"]:
            path = self.base / entry["path"]
            digest = writer._digest(path.read_bytes())
            self.assertIn(digest, [entry["original_sha256"], entry["expected_sha256"]])
            after_count += digest == entry["expected_sha256"]
            self.assertEqual((self.base / record["backup"] / entry["path"]).read_bytes(), before[path][0])
        self.assertEqual(after_count, 1)
        interrupted_state = fixtures.inventory(self.base)
        blocked = self.run_cli(self.project, "--apply")
        self.assertEqual(blocked.returncode, 5)
        self.assertIn(str(self.base / record["backup"]), blocked.stderr)
        self.assertEqual(fixtures.inventory(self.base), interrupted_state)

    def test_backup_directory_creation_failure_leaves_sources_untouched(self):
        self.single()
        before = self.sources()
        with patch.object(writer, "_backup_directory", side_effect=PermissionError("injected backup mkdir failure")):
            with self.assertRaises(writer.ApplyFailure) as caught:
                writer.apply_project(self.project)
        self.assertFalse(caught.exception.incomplete)
        self.assertIn("before original modification", str(caught.exception))
        self.assert_sources(before)
        self.assertFalse(self.marker.exists())

    def test_permissions_changed_on_staging_file_are_rejected(self):
        self.single()
        before = self.sources()
        stage = writer._stage

        def changed(*args):
            temporary = stage(*args)
            temporary.chmod(0o700)
            return temporary

        with patch.object(writer, "_stage", side_effect=changed), patch.object(writer, "_replace") as replace:
            self.assert_clean_failure(lambda: writer.apply_project(self.project), before)
        replace.assert_not_called()

    def test_backup_corrupted_during_forward_apply_prevents_success(self):
        self.reused()
        real = writer._replace
        corrupted = False

        def changed(staged, path):
            nonlocal corrupted
            real(staged, path)
            if not corrupted:
                record = json.loads(self.marker.read_bytes())
                (self.base / record["backup"] / "a.kicad_sch").write_bytes(b"third-party backup corruption")
                corrupted = True

        with patch.object(writer, "_replace", side_effect=changed):
            with self.assertRaises(writer.ApplyFailure) as caught:
                writer.apply_project(self.project)
        self.assertTrue(caught.exception.incomplete)
        self.assertTrue(self.marker.exists())

    def test_marker_removal_failure_never_reports_success(self):
        self.single()
        before = self.sources()
        unlink = Path.unlink

        def fail(path, *args, **kwargs):
            if path == self.marker:
                raise PermissionError("injected marker removal failure")
            return unlink(path, *args, **kwargs)

        with patch.object(Path, "unlink", fail):
            with self.assertRaises(writer.ApplyFailure) as caught:
                writer.apply_project(self.project)
        self.assertTrue(caught.exception.incomplete)
        self.assert_sources(before)
        self.assertTrue(self.marker.exists())

    def test_unknown_staging_contents_are_not_removed(self):
        source = self.single()
        original = source.read_bytes()
        stage = writer._stage
        external_temporary = None

        def changed(*args):
            nonlocal external_temporary
            external_temporary = stage(*args)
            external_temporary.write_bytes(b"third-party staging contents")
            return external_temporary

        with patch.object(writer, "_stage", side_effect=changed):
            with self.assertRaises(writer.ApplyFailure) as caught:
                writer.apply_project(self.project)
        self.assertTrue(caught.exception.incomplete)
        self.assertEqual(source.read_bytes(), original)
        self.assertEqual(external_temporary.read_bytes(), b"third-party staging contents")
        self.assertTrue(self.marker.exists())

    def test_ambiguous_or_duplicate_physical_input_identities_fail_before_backup(self):
        self.reused()
        plan = engine.build_plan(self.project)
        before = fixtures.inventory(self.base)
        for physical in [plan.snapshots[0].identity[:2], (0, 0)]:
            with self.subTest(physical=physical):
                snapshots = list(plan.snapshots)
                snapshots[1] = replace(snapshots[1], identity=physical + snapshots[1].identity[2:])
                ambiguous = replace(plan, snapshots=tuple(snapshots))
                with patch.object(engine, "build_plan", return_value=ambiguous):
                    with self.assertRaisesRegex(InvalidProject, "physical source identity"):
                        writer.apply_project(self.project)
                self.assertEqual(fixtures.inventory(self.base), before)


if __name__ == "__main__":
    unittest.main()
