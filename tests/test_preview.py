"""Behavior tests runnable by pytest or the standard-library unittest runner."""

from contextlib import redirect_stderr
from dataclasses import FrozenInstanceError
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import UUID

from kicad_renumber import cli, engine
from kicad_renumber.engine import build_plan, candidate_bytes
from kicad_renumber.sexpr import InvalidProject, parse


LAUNCHER = Path(__file__).resolve().parents[1] / "renumber_pages.py"


def uid(n):
    return str(UUID(int=n))


def ipath(*parts):
    return "/" + "/".join(uid(p) for p in parts)


def quote(value):
    return json.dumps(str(value), ensure_ascii=False)


def sheet(n, name, filename, records, foreign=""):
    paths = " ".join(f"(path {quote(parent)} (page {quote(page)}))" for parent, page in records)
    return (f"(sheet (uuid {quote(uid(n))}) (property \"Sheetname\" {quote(name)}) "
            f"(property \"Sheetfile\" {quote(filename)}) "
            f"(instances (project \"demo\" {paths}) {foreign}))")


def schematic(n, page="9", sheets=(), extra="", version="20260306", generator="10.0"):
    root_page = "" if page is None else f'(sheet_instances (path "/" (page {quote(page)})))'
    return (f'(kicad_sch (version {version}) (generator "eeschema") '
            f'(generator_version {quote(generator)}) (uuid {quote(uid(n))}) '
            f'(paper "A4") (lib_symbols) {extra}\n'
            + "\n".join(sheets) + f"\n{root_page} (embedded_fonts no))\n").encode("utf-8")


def inventory(directory):
    return tuple((str(p.relative_to(directory)), p.is_dir(),
                  None if p.is_dir() else p.read_bytes(), p.stat().st_mtime_ns)
                 for p in sorted(directory.rglob("*")))


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.project = self.base / "demo.kicad_pro"

    def write(self, filename, data):
        path = self.base / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def roots(self, *roots):
        data = {"schematic": {"top_level_sheets": [
            {"filename": filename, "name": name, "uuid": uid(n)}
            for filename, name, n in roots]}, "sheets": [[uid(999), "Decoy"]]}
        self.project.write_text(json.dumps(data), encoding="utf-8")

    def single(self, page="9", extra=""):
        self.roots(("root.kicad_sch", "Root", 1))
        return self.write("root.kicad_sch", schematic(1, page, extra=extra))

    def reused(self, multiple_roots=True):
        if multiple_roots:
            self.roots(("b.kicad_sch", "Root 10", 2), ("a.kicad_sch", "Root 2", 1))
            self.write("a.kicad_sch", schematic(1, sheets=[
                sheet(10, "Shared", "shared.kicad_sch", [(ipath(1), "15")])]))
            self.write("b.kicad_sch", schematic(2, sheets=[
                sheet(11, "Shared", "shared.kicad_sch", [(ipath(2), "16")])]))
            parents = [ipath(1, 10), ipath(2, 11)]
        else:
            self.roots(("a.kicad_sch", "Root", 1))
            self.write("a.kicad_sch", schematic(1, sheets=[
                sheet(11, "Channel 10", "shared.kicad_sch", [(ipath(1), "15")]),
                sheet(10, "Channel 2", "shared.kicad_sch", [(ipath(1), "16")])]))
            parents = [ipath(1, 10), ipath(1, 11)]
        self.write("shared.kicad_sch", schematic(3, None, sheets=[
            sheet(12, "Leaf", "leaf.kicad_sch", [(p, "20") for p in parents])]))
        self.write("leaf.kicad_sch", schematic(4, None))

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(LAUNCHER), *map(str, args)],
                              cwd=self.base, capture_output=True, text=True, check=False)

    def test_single_root_and_exact_page_location(self):
        path = self.single()
        plan = build_plan(self.project)
        self.assertEqual(len(plan.items), 1)
        item = plan.items[0]
        self.assertEqual((item.instance_path, item.old_page, item.new_page), ((uid(1),), "9", "1"))
        self.assertEqual(item.source_file, path)
        self.assertEqual(path.read_bytes()[item.location.start:item.location.end], b'"9"')
        self.assertEqual(plan.affected_files, (path,))

    def test_multiple_roots_depth_first_shared_descendants(self):
        self.reused()
        plan = build_plan(self.project)
        self.assertEqual([i.display_name for i in plan.items],
                         ["Root 2", "Shared", "Leaf", "Root 10", "Shared", "Leaf"])
        self.assertEqual([i.new_page for i in plan.items], list(map(str, range(1, 7))))
        self.assertEqual(plan.items[2].instance_path, (uid(1), uid(10), uid(12)))
        self.assertEqual(plan.items[5].instance_path, (uid(2), uid(11), uid(12)))
        self.assertEqual(plan.items[2].source_file, plan.items[5].source_file)
        self.assertNotEqual(plan.items[2].location, plan.items[5].location)
        self.assertEqual(plan.items[2].location.file.name, "shared.kicad_sch")
        self.assertEqual(len(plan.snapshots), 5)  # project + four documents, each read once in graph

    def test_repeated_file_and_descendants_under_one_root(self):
        self.reused(False)
        plan = build_plan(self.project)
        self.assertEqual([i.display_name for i in plan.items],
                         ["Root", "Channel 2", "Leaf", "Channel 10", "Leaf"])
        self.assertEqual(len({i.instance_path for i in plan.items}), 5)

    def test_natural_casefold_and_original_name_ties(self):
        self.roots(("z.kicad_sch", "channel 2", 3), ("b.kicad_sch", "Channel 10", 2),
                   ("a.kicad_sch", "Channel 2", 1), ("zero.kicad_sch", "Channel 02", 4))
        for filename, n in [("z.kicad_sch", 3), ("b.kicad_sch", 2),
                            ("a.kicad_sch", 1), ("zero.kicad_sch", 4)]:
            self.write(filename, schematic(n))
        self.assertEqual([i.display_name for i in build_plan(self.project).items],
                         ["Channel 02", "Channel 2", "channel 2", "Channel 10"])

    def test_equal_names_use_instance_identity_not_file_order(self):
        self.roots(("root.kicad_sch", "Root", 1))
        self.write("root.kicad_sch", schematic(1, sheets=[
            sheet(11, "Same", "empty.kicad_sch", [(ipath(1), "8")]),
            sheet(10, "Same", "empty.kicad_sch", [(ipath(1), "7")])]))
        self.write("empty.kicad_sch", schematic(2, None))
        self.assertEqual([i.instance_path[-1] for i in build_plan(self.project).items],
                         [uid(1), uid(10), uid(11)])

    def test_equal_root_names_use_uuid(self):
        self.roots(("b.kicad_sch", "Same", 2), ("a.kicad_sch", "Same", 1))
        self.write("a.kicad_sch", schematic(1))
        self.write("b.kicad_sch", schematic(2))
        self.assertEqual([i.instance_path[0] for i in build_plan(self.project).items], [uid(1), uid(2)])

    def test_long_numeric_names_and_ascii_digit_policy(self):
        self.roots(("a.kicad_sch", "Channel " + "9" * 5000, 1),
                   ("b.kicad_sch", "Channel 2", 2))
        self.write("a.kicad_sch", schematic(1))
        self.write("b.kicad_sch", schematic(2))
        self.assertEqual(build_plan(self.project).items[0].instance_path, (uid(2),))
        self.assertEqual(engine.natural_key("Channel 02", ()),
                         (engine.natural_key("Channel 2", ())[0], "Channel 02", ()))

    def test_empty_instantiated_sheet_counts(self):
        self.reused(False)
        plan = build_plan(self.project)
        self.assertEqual(sum(i.source_file.name == "leaf.kicad_sch" for i in plan.items), 2)

    def test_issue23403_mismatched_registered_and_document_root_uuid(self):
        # Original synthetic counterpart of upstream 10.0.6 issue23403:
        # two registered roots share a subsheet; the second document header
        # differs from its registered instance UUID, and descendants use the latter.
        self.reused()
        path = self.base / "b.kicad_sch"
        path.write_bytes(path.read_bytes().replace(quote(uid(2)).encode(), quote(uid(99)).encode(), 1))
        before = inventory(self.base)
        plan = build_plan(self.project)
        self.assertEqual(plan.items[3].instance_path, (uid(2),))
        self.assertEqual(plan.items[4].instance_path, (uid(2), uid(11)))
        self.assertEqual(plan.items[5].instance_path, (uid(2), uid(11), uid(12)))
        self.assertEqual(len(plan.items), 6)
        self.assertIn(f'(uuid "{uid(99)}")'.encode(), path.read_bytes())
        self.assertEqual(inventory(self.base), before)
        proposed = dict(candidate_bytes(plan))[path]
        self.assertIn(f'(uuid "{uid(99)}")'.encode(), proposed)
        self.assertIn(f'(path "{ipath(2)}"'.encode(), proposed)

    def test_mismatched_root_does_not_use_document_uuid_in_child_paths(self):
        self.reused()
        path = self.base / "b.kicad_sch"
        path.write_bytes(path.read_bytes().replace(quote(uid(2)).encode(), quote(uid(99)).encode(), 1)
                         .replace(quote(ipath(2)).encode(), quote(ipath(99)).encode()))
        with self.assertRaisesRegex(InvalidProject, "missing page record"):
            build_plan(self.project)

    def test_explicit_nil_registry_falls_back_to_document_uuid(self):
        self.reused(False)
        self.roots(("a.kicad_sch", "Root", 0))
        before = inventory(self.base)
        plan = build_plan(self.project)
        self.assertEqual(plan.items[0].instance_path, (uid(1),))
        self.assertEqual(plan.items[2].instance_path, (uid(1), uid(10), uid(12)))
        self.assertEqual(inventory(self.base), before)

    def test_missing_or_malformed_registry_uuid_is_not_nil_fallback(self):
        self.single()
        data = json.loads(self.project.read_text())
        for value in [None, "", "malformed", 3]:
            with self.subTest(value=value):
                entry = data["schematic"]["top_level_sheets"][0]
                entry["uuid"] = value
                self.project.write_text(json.dumps(data))
                with self.assertRaisesRegex(InvalidProject, "UUID"):
                    build_plan(self.project)
        del entry["uuid"]
        self.project.write_text(json.dumps(data))
        with self.assertRaisesRegex(InvalidProject, "UUID"):
            build_plan(self.project)

    def test_duplicate_effective_roots_after_nil_fallback(self):
        self.roots(("a.kicad_sch", "Root 1", 1), ("b.kicad_sch", "Root 2", 0))
        self.write("a.kicad_sch", schematic(8))
        self.write("b.kicad_sch", schematic(1))
        with self.assertRaisesRegex(InvalidProject, "duplicate effective"):
            build_plan(self.project)

    def test_distinct_nil_registrations_can_resolve_distinct_roots(self):
        self.roots(("a.kicad_sch", "Root 1", 0), ("b.kicad_sch", "Root 2", 0))
        self.write("a.kicad_sch", schematic(1))
        self.write("b.kicad_sch", schematic(2))
        self.assertEqual([i.instance_path for i in build_plan(self.project).items], [(uid(1),), (uid(2),)])

    def test_malformed_document_uuid_remains_invalid(self):
        path = self.single()
        path.write_bytes(path.read_bytes().replace(quote(uid(1)).encode(), b'"malformed"', 1))
        with self.assertRaisesRegex(InvalidProject, "invalid UUID"):
            build_plan(self.project)

    def test_stored_path_must_address_parent(self):
        self.roots(("root.kicad_sch", "Root", 1))
        self.write("root.kicad_sch", schematic(1, sheets=[
            sheet(10, "Child", "child.kicad_sch", [(ipath(1, 10), "2")])]))
        self.write("child.kicad_sch", schematic(2, None))
        with self.assertRaisesRegex(InvalidProject, "missing page record"):
            build_plan(self.project)

    def test_missing_child(self):
        self.reused()
        (self.base / "leaf.kicad_sch").unlink()
        with self.assertRaisesRegex(InvalidProject, "cannot resolve referenced sheet"):
            build_plan(self.project)

    def test_missing_child_page(self):
        self.roots(("root.kicad_sch", "Root", 1))
        self.write("root.kicad_sch", schematic(1, sheets=[
            sheet(10, "Child", "child.kicad_sch", [])]))
        with self.assertRaisesRegex(InvalidProject, "missing page record"):
            build_plan(self.project)

    def test_missing_root_page(self):
        self.single(None)
        with self.assertRaisesRegex(InvalidProject, "missing root page"):
            build_plan(self.project)

    def test_duplicate_parent_instance_record(self):
        self.roots(("root.kicad_sch", "Root", 1))
        self.write("root.kicad_sch", schematic(1, sheets=[
            sheet(10, "Child", "child.kicad_sch", [(ipath(1), "2"), (ipath(1), "2")])]))
        with self.assertRaisesRegex(InvalidProject, "duplicate parent"):
            build_plan(self.project)

    def test_orphan_current_project_path(self):
        self.reused()
        path = self.base / "shared.kicad_sch"
        text = path.read_text().replace('(project "demo"',
                                       f'(project "demo" (path "{ipath(999)}" (page "8"))', 1)
        path.write_text(text)
        with self.assertRaisesRegex(InvalidProject, "reachable graph"):
            build_plan(self.project)

    def test_duplicate_project_group(self):
        self.reused()
        path = self.base / "a.kicad_sch"
        path.write_bytes(path.read_bytes().replace(b'(instances ', b'(instances (project "demo") ', 1))
        with self.assertRaisesRegex(InvalidProject, "duplicate current-project"):
            build_plan(self.project)

    def test_foreign_project_information_is_opaque_and_unchanged(self):
        self.roots(("root.kicad_sch", "Root", 1))
        foreign = '(project "another-project" (path "/foreign" (page "do not touch")))'
        self.write("root.kicad_sch", schematic(1, sheets=[
            sheet(10, "Child", "child.kicad_sch", [(ipath(1), "8")], foreign)]))
        self.write("child.kicad_sch", schematic(2, None))
        plan = build_plan(self.project)
        proposed = dict(candidate_bytes(plan))[self.base / "root.kicad_sch"]
        self.assertIn(foreign.encode(), proposed)
        self.assertEqual(len(plan.items), 2)

    def test_foreign_project_group_cannot_supply_current_page(self):
        self.reused()
        path = self.base / "a.kicad_sch"
        path.write_bytes(path.read_bytes().replace(b'(project "demo"', b'(project "other"'))
        with self.assertRaisesRegex(InvalidProject, "missing page record"):
            build_plan(self.project)

    def test_duplicate_gapped_and_nonnumeric_values_are_repairable(self):
        self.reused()
        path = self.base / "b.kicad_sch"
        path.write_bytes(path.read_bytes().replace(b'(page "9")', b'(page "intro")'))
        plan = build_plan(self.project)
        self.assertEqual([i.new_page for i in plan.items], list(map(str, range(1, 7))))
        self.assertEqual(plan.change_count, 6)
        self.assertEqual(plan.items[3].old_page, "intro")

    def test_empty_page_value_is_repairable(self):
        self.single("")
        self.assertEqual(build_plan(self.project).items[0].new_page, "1")

    def test_already_correct_is_noop(self):
        self.single("1")
        before = inventory(self.base)
        plan = build_plan(self.project)
        result = self.run_cli(self.project)
        self.assertFalse(plan.edits)
        self.assertFalse(candidate_bytes(plan))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("already correct", result.stdout)
        self.assertEqual(inventory(self.base), before)

    def test_unrelated_files_not_parsed_and_sheets_listing_not_used(self):
        self.single()
        self.write("unrelated.kicad_sch", b"malformed unrelated file")
        self.assertEqual(len(build_plan(self.project).snapshots), 2)

    def test_root_registry_required_no_basename_fallback(self):
        self.project.write_text('{"sheets": [["root", "Root"]]}')
        self.write("demo.kicad_sch", schematic(1))
        with self.assertRaisesRegex(InvalidProject, "top_level_sheets"):
            build_plan(self.project)

    def test_duplicate_root_metadata(self):
        self.roots(("a.kicad_sch", "Root", 1), ("a.kicad_sch", "Root", 1))
        self.write("a.kicad_sch", schematic(1))
        with self.assertRaisesRegex(InvalidProject, "same top-level source"):
            build_plan(self.project)

    def test_distinct_instances_not_conflated_by_document_uuid(self):
        self.roots(("a.kicad_sch", "Root 1", 1), ("b.kicad_sch", "Root 2", 2))
        self.write("a.kicad_sch", schematic(1))
        self.write("b.kicad_sch", schematic(1))
        self.assertEqual([i.instance_path for i in build_plan(self.project).items], [(uid(1),), (uid(2),)])

    def test_duplicate_effective_non_nil_roots(self):
        self.roots(("a.kicad_sch", "Root 1", 1), ("b.kicad_sch", "Root 2", 1))
        self.write("a.kicad_sch", schematic(8))
        self.write("b.kicad_sch", schematic(9))
        with self.assertRaisesRegex(InvalidProject, "duplicate effective"):
            build_plan(self.project)

    def test_duplicate_json_key_rejected(self):
        self.project.write_text('{"schematic": {}, "schematic": {}}')
        with self.assertRaisesRegex(InvalidProject, "duplicate project JSON key"):
            build_plan(self.project)

    def test_duplicate_root_page_record(self):
        path = self.single()
        path.write_bytes(path.read_bytes().replace(b'(page "9")', b'(page "9") (page "9")'))
        with self.assertRaises(InvalidProject):
            build_plan(self.project)

    def test_unquoted_page_rejected(self):
        path = self.single()
        path.write_bytes(path.read_bytes().replace(b'(page "9")', b'(page 9)'))
        with self.assertRaisesRegex(InvalidProject, "encoding"):
            build_plan(self.project)

    def test_malformed_sexpression(self):
        path = self.single()
        path.write_bytes(path.read_bytes()[:-2])
        with self.assertRaisesRegex(InvalidProject, "unclosed"):
            build_plan(self.project)

    def test_unsupported_schematic_version(self):
        path = self.single()
        path.write_bytes(schematic(1, version="20250114"))
        with self.assertRaisesRegex(InvalidProject, "unsupported schematic version"):
            build_plan(self.project)

    def test_unsupported_generator_and_top_level_syntax(self):
        path = self.single()
        for data in [schematic(1, generator="11.0"), schematic(1, extra="(future_hierarchy)")]:
            with self.subTest(data=data):
                path.write_bytes(data)
                with self.assertRaisesRegex(InvalidProject, "unsupported"):
                    build_plan(self.project)

    def test_unsupported_sheet_symbol_syntax(self):
        self.reused()
        path = self.base / "a.kicad_sch"
        path.write_bytes(path.read_bytes().replace(b"(sheet ", b"(sheet (future_hierarchy) ", 1))
        with self.assertRaisesRegex(InvalidProject, "unsupported sheet-symbol syntax"):
            build_plan(self.project)

    def test_cycle(self):
        self.roots(("root.kicad_sch", "Root", 1))
        self.write("root.kicad_sch", schematic(1, sheets=[
            sheet(10, "Loop", "root.kicad_sch", [(ipath(1), "2")])]))
        with self.assertRaisesRegex(InvalidProject, "cycle"):
            build_plan(self.project)

    def test_duplicate_sheet_uuid(self):
        self.roots(("root.kicad_sch", "Root", 1))
        child = sheet(10, "Child", "child.kicad_sch", [(ipath(1), "2")])
        self.write("root.kicad_sch", schematic(1, sheets=[child, child]))
        with self.assertRaisesRegex(InvalidProject, "duplicate sheet-symbol"):
            build_plan(self.project)

    def test_invalid_uuid_and_parent_paths(self):
        self.reused()
        path = self.base / "a.kicad_sch"
        original = path.read_bytes()
        for value in ["not-a-uuid", "/", ipath(1) + "/", ipath(1) + "//" + uid(10)]:
            with self.subTest(value=value):
                path.write_bytes(original.replace(quote(ipath(1)).encode(), quote(value).encode()))
                with self.assertRaises(InvalidProject):
                    build_plan(self.project)

    def test_preview_determinism_and_full_filesystem_noop(self):
        self.reused()
        before = inventory(self.base)
        package = LAUNCHER.parent / "kicad_renumber"
        package_before = inventory(package)
        first, second = self.run_cli(self.project), self.run_cli(self.project)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(first.stderr, "")
        self.assertIn("6 sheets, 6 page changes, 3 affected files", first.stdout)
        self.assertEqual(first.stdout.count("Instance:"), 6)
        self.assertEqual(inventory(self.base), before)
        self.assertEqual(inventory(package), package_before)

    def test_apply_rejected_without_reading_or_writing(self):
        self.single()
        before = inventory(self.base)
        result = self.run_cli(self.project, "--apply")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unsupported operation", result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(inventory(self.base), before)

    def test_cold_launcher_creates_no_import_caches_or_project_outputs(self):
        self.single()
        installation = self.base / "installation"
        installation.mkdir()
        shutil.copyfile(LAUNCHER, installation / LAUNCHER.name)
        shutil.copytree(LAUNCHER.parent / "kicad_renumber", installation / "kicad_renumber",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        before = inventory(self.base)
        result = subprocess.run([sys.executable, str(installation / LAUNCHER.name), str(self.project)],
                                cwd=self.base, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(inventory(self.base), before)

    def test_missing_explicit_project_and_invalid_input_diagnostic(self):
        self.assertEqual(self.run_cli().returncode, 2)
        result = self.run_cli("missing.kicad_pro")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Invalid or unsupported project", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_internal_failure_has_distinct_status(self):
        error = io.StringIO()
        with patch.object(cli, "build_plan", side_effect=RuntimeError("test failure")), redirect_stderr(error):
            self.assertEqual(cli.main([str(self.project)]), 3)
        self.assertIn("Internal failure (RuntimeError)", error.getvalue())

    def test_plan_is_immutable(self):
        self.single()
        plan = build_plan(self.project)
        with self.assertRaises(FrozenInstanceError):
            plan.items[0].new_page = "99"
        with self.assertRaises(FrozenInstanceError):
            plan.edits = ()

    def test_candidate_preserves_all_nonpage_bytes_and_is_idempotent(self):
        self.single('old "quoted" \\ page', extra='(text "é (page \\"8\\")" (at 0 0 0))')
        plan = build_plan(self.project)
        source = self.base / "root.kicad_sch"
        edit = plan.edits[0]
        original = source.read_bytes()
        proposed = dict(candidate_bytes(plan))[source]
        self.assertEqual(proposed, original[:edit.location.start] + b'"1"' + original[edit.location.end:])
        self.assertEqual(original[edit.location.start:edit.location.end], edit.original)
        # Only the test writes a disposable fixture to verify a second analysis.
        source.write_bytes(proposed)
        self.assertEqual(build_plan(self.project).change_count, 0)

    def test_relative_child_resolution_is_from_parent_directory(self):
        self.roots(("sub/root.kicad_sch", "Root", 1))
        self.write("sub/root.kicad_sch", schematic(1, sheets=[
            sheet(10, "Child", "../child.kicad_sch", [(ipath(1), "2")])]))
        self.write("child.kicad_sch", schematic(2, None))
        self.assertEqual(len(build_plan(self.project).items), 2)

    def test_outside_project_reference_rejected(self):
        self.single()
        self.roots((str(self.base.parent / "outside.kicad_sch"), "Root", 1))
        with self.assertRaisesRegex(InvalidProject, "unsupported schematic reference"):
            build_plan(self.project)

    def test_symlink_rejected(self):
        path = self.single()
        alias = self.base / "alias.kicad_sch"
        try:
            alias.symlink_to(path)
        except OSError:
            self.skipTest("symlink creation unavailable")
        self.roots(("alias.kicad_sch", "Root", 1))
        with self.assertRaisesRegex(InvalidProject, "symlink"):
            build_plan(self.project)

    def test_hardlink_rejected(self):
        path = self.single()
        try:
            os.link(path, self.base / "alias.kicad_sch")
        except OSError:
            self.skipTest("hardlink creation unavailable")
        with self.assertRaisesRegex(InvalidProject, "unaliased regular"):
            build_plan(self.project)

    def test_concurrent_source_change_detected(self):
        source = self.single()
        read = engine._read
        calls = 0

        def changed(path):
            nonlocal calls
            if path == source:
                calls += 1
                if calls == 2:
                    source.write_bytes(source.read_bytes() + b"\n")
            return read(path)

        with patch.object(engine, "_read", side_effect=changed):
            with self.assertRaisesRegex(InvalidProject, "source changed during analysis"):
                build_plan(self.project)


class ParserTests(unittest.TestCase):
    def test_utf8_byte_offsets_and_escapes(self):
        data = '(x "é" "a\\"b\\\\c\\n\\t\\r")'.encode()
        tree = parse(data)
        self.assertEqual(data[tree.items[1].start:tree.items[1].end], '"é"'.encode())
        self.assertEqual(tree.items[2].value, 'a"b\\c\n\t\r')

    def test_malformed_and_unsupported_lexical_input(self):
        for data in [b"", b")", b"(x", b'(x "oops)', b'(x "a\\q")',
                     b'(x "a"b)', b"(x) (y)", b'(x "\xff")', b"(x \0)", b"atom"]:
            with self.subTest(data=data), self.assertRaises(InvalidProject):
                parse(data)

    def test_excessive_nesting_is_input_error(self):
        with self.assertRaisesRegex(InvalidProject, "nesting"):
            parse(b"(" * 513 + b")" * 513)


if __name__ == "__main__":
    unittest.main()
