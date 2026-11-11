"""Independent fixed-fixture oracles, using the actual command-line program.

No engine/parser/plan/candidate implementation is imported. Expected order and
page-record ownership are declared in tables before the utility is invoked.
The small byte matcher below is deliberately limited to these known fixtures;
it is not an alternate application parser or numbering implementation.
"""

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
import xml.etree.ElementTree as ET


LAUNCHER = Path(__file__).resolve().parents[1] / "renumber_pages.py"
NIL = "00000000-0000-0000-0000-000000000000"
R2 = "22222222-2222-4222-8222-222222222222"
R10 = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
DOC10 = "11111111-1111-4111-8111-111111111111"
SHARED = "33333333-3333-4333-8333-333333333333"
EMPTY = "44444444-4444-4444-8444-444444444444"
C2 = "a0000000-0000-4000-8000-000000000002"
C10 = "a0000000-0000-4000-8000-000000000010"
E10 = "e0000000-0000-4000-8000-000000000010"
LEAF = "e0000000-0000-4000-8000-000000000002"
PAGE = re.compile(rb'\(path\s+("(?:[^"\\]|\\.)*")\s*\(page\s+("(?:[^"\\]|\\.)*")\s*\)\s*\)')


@dataclass(frozen=True)
class Expected:
    names: tuple[str, ...]
    path: tuple[str, ...]
    source: str
    owner: str
    slot: int
    old: str


@dataclass(frozen=True)
class Case:
    project: Path
    main: str
    rows: tuple[Expected, ...]
    # filename, display name, registered UUID, document UUID
    roots: tuple[tuple[str, str, str, str], ...]


def q(value):
    return json.dumps(value, ensure_ascii=False)


def path_of(*ids):
    return "/" + "/".join(ids)


def drawings():
    # Original geometry, following KiCad 10 saveShape/saveTable/saveTextBox.
    return '''
(rectangle (start 15 15) (end 45 25) (stroke (width 0.254) (type default))
 (fill (type none)) (uuid "d0000000-0000-4000-8000-000000000001"))
(table (column_count 1)
 (border (external yes) (header yes) (stroke (width 0.254) (type default)))
 (separators (rows yes) (cols yes) (stroke (width 0.254) (type default)))
 (column_widths 90) (row_heights 12) (uuid "d0000000-0000-4000-8000-000000000002")
 (cells (table_cell "Drawing only: (page \\"999\\") and (sheet \\"not hierarchy\\")"
 (exclude_from_sim no) (at 15 30 0) (size 90 12) (margins 1 1 1 1) (span 1 1)
 (fill (type none)) (effects (font (size 1.27 1.27)))
 (uuid "d0000000-0000-4000-8000-000000000003"))))
'''


def sheet(symbol, name, filename, pages, at=(60, 70)):
    x, y = at
    records = "\n".join(f'(path {q(parent)} (page {q(number)}))' for parent, number in pages)
    return f'''(sheet (at {x} {y}) (size 45 20)
 (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) (fields_autoplaced yes)
 (stroke (width 0.1524) (type default)) (fill (color 0 0 0 0)) (uuid {q(symbol)})
 (property "Sheetname" {q(name)} (at {x} {y-1} 0) (effects (font (size 1.27 1.27)) (justify left bottom)))
 (property "Sheetfile" {q(filename)} (at {x} {y+21} 0) (effects (font (size 1.27 1.27)) (justify left top)))
 (instances (project "forest" {records})))'''


def document(uuid, body="", page=None):
    root = f'(sheet_instances (path "/" (page {q(page)})))' if page is not None else ""
    return f'''(kicad_sch (version 20260306) (generator "eeschema") (generator_version "10.0")
 (uuid {q(uuid)}) (paper "A4") (lib_symbols)
 {body}
 {root} (embedded_fonts no))
'''.encode()


def registry(base, name, roots):
    project = base / f"{name}.kicad_pro"
    project.write_text(json.dumps({"meta": {"filename": project.name, "version": 3},
        "schematic": {"top_level_sheets": [dict(filename=f, name=n, uuid=u) for f,n,u,d in roots]},
        "sheets": [], "text_variables": {}}, indent=2), encoding="utf-8")
    (base / "unrelated.kicad_sch").write_bytes(b"Unreferenced sentinel; not a schematic.\n")
    return project


def make_forest(base):
    base.mkdir(parents=True, exist_ok=True)
    roots = (("forest.kicad_sch", "Block 10", R10, DOC10),
             ("top2.kicad_sch", "Block 2", R2, R2))
    project = registry(base, "forest", roots)
    (base / "forest.kicad_sch").write_bytes(document(DOC10,
        sheet(C2, "Channel 2", "shared.kicad_sch", [(path_of(R10), "22")]), "88"))
    (base / "top2.kicad_sch").write_bytes(document(R2,
        sheet(C10, "Channel 10", "shared.kicad_sch", [(path_of(R2), "22")], (20, 70)) +
        sheet(E10, "Empty 10", "empty.kicad_sch", [(path_of(R2), "44")], (140, 70)) +
        sheet(C2, "Channel 2", "shared.kicad_sch", [(path_of(R2), "22")], (80, 70)), "88"))
    (base / "shared.kicad_sch").write_bytes(document(SHARED, drawings() + sheet(
        LEAF, "Empty 2", "empty.kicad_sch", [
            (path_of(R10, C2), "90"), (path_of(R2, C10), "90"), (path_of(R2, C2), "90")], (60, 70))))
    (base / "empty.kicad_sch").write_bytes(document(EMPTY))
    # Explicit oracle: no call to the program derives this ordering or ownership.
    rows = (
        Expected(("Block 2",), (R2,), "top2.kicad_sch", "top2.kicad_sch", 3, "88"),
        Expected(("Block 2", "Channel 2"), (R2,C2), "shared.kicad_sch", "top2.kicad_sch", 2, "22"),
        Expected(("Block 2", "Channel 2", "Empty 2"), (R2,C2,LEAF), "empty.kicad_sch", "shared.kicad_sch", 2, "90"),
        Expected(("Block 2", "Channel 10"), (R2,C10), "shared.kicad_sch", "top2.kicad_sch", 0, "22"),
        Expected(("Block 2", "Channel 10", "Empty 2"), (R2,C10,LEAF), "empty.kicad_sch", "shared.kicad_sch", 1, "90"),
        Expected(("Block 2", "Empty 10"), (R2,E10), "empty.kicad_sch", "top2.kicad_sch", 1, "44"),
        Expected(("Block 10",), (R10,), "forest.kicad_sch", "forest.kicad_sch", 1, "88"),
        Expected(("Block 10", "Channel 2"), (R10,C2), "shared.kicad_sch", "forest.kicad_sch", 0, "22"),
        Expected(("Block 10", "Channel 2", "Empty 2"), (R10,C2,LEAF), "empty.kicad_sch", "shared.kicad_sch", 0, "90"),
    )
    return Case(project, "forest.kicad_sch", rows, roots)


def make_single(base):
    base.mkdir(parents=True, exist_ok=True)
    roots = (("single.kicad_sch", "Single", NIL, DOC10),)
    project = registry(base, "single", roots)
    child = sheet(C2, "Empty", "empty.kicad_sch", [(path_of(DOC10), "7")]).replace('project "forest"', 'project "single"')
    (base / "single.kicad_sch").write_bytes(document(DOC10, drawings() + child, "88"))
    (base / "empty.kicad_sch").write_bytes(document(EMPTY))
    return Case(project, "single.kicad_sch", (
        Expected(("Single",), (DOC10,), "single.kicad_sch", "single.kicad_sch", 1, "88"),
        Expected(("Single", "Empty"), (DOC10,C2), "empty.kicad_sch", "single.kicad_sch", 0, "7")), roots)


UPSTREAM_BLOBS = {
    "issue23403.kicad_pro": "8ebd996e7ba94ffd55b115d41d98de985458af7a",
    "issue23403.kicad_sch": "45763377bebb91b1be7e4e648f4b73ac429beb1b",
    "top_level_sheet_1.kicad_sch": "3585d91e25b74e56e24e3f59523f2328c7a3b8ab",
    "shared1.kicad_sch": "8e37d5ec63c908b9e474310a06bfd6ac3bfcc862",
}


def slots(data):
    return [(json.loads(m[1]), json.loads(m[2]), m.start(2), m.end(2)) for m in PAGE.finditer(data)]


def put_values(data, values):
    matches = slots(data)
    assert len(matches) == len(values)
    for (_, _, start, end), value in reversed(list(zip(matches, values))):
        data = data[:start] + q(value).encode() + data[end:]
    return data


def make_upstream(base, source):
    base.mkdir(parents=True, exist_ok=True)
    for name, expected in UPSTREAM_BLOBS.items():
        data = (source / name).read_bytes()
        actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        assert actual == expected, (name, actual)
        (base / name).write_bytes(data)
    for name, values in [("issue23403.kicad_sch", ["40", "9"]),
                         ("top_level_sheet_1.kicad_sch", ["90", "9"])]:
        path = base / name
        path.write_bytes(put_values(path.read_bytes(), values))
    a = "da308afe-918c-407a-88a0-b7c2f2b6b630"
    b = "ccc7e5dc-77b6-4792-b9b6-8eaa039374d5"
    sa = "d5de9e0c-cb83-4933-8ad3-c56de7399421"
    sb = "721e2e69-2870-4f3f-9d5a-3b28fa2c5f6b"
    return Case(base / "issue23403.kicad_pro", "issue23403.kicad_sch", (
        Expected(("Root",), (a,), "issue23403.kicad_sch", "issue23403.kicad_sch", 1, "9"),
        Expected(("Root", "shared1"), (a,sa), "shared1.kicad_sch", "issue23403.kicad_sch", 0, "40"),
        Expected(("top_level_sheet_1",), (b,), "top_level_sheet_1.kicad_sch", "top_level_sheet_1.kicad_sch", 1, "9"),
        Expected(("top_level_sheet_1", "shared1"), (b,sb), "shared1.kicad_sch", "top_level_sheet_1.kicad_sch", 0, "90")),
        (("issue23403.kicad_sch", "Root", a, a),
         ("top_level_sheet_1.kicad_sch", "top_level_sheet_1", b, "574f9438-bf45-4364-93f8-a7864ab0aeac")))


def snapshot(base):
    return {p.relative_to(base).as_posix(): (p.is_dir(), None if p.is_dir() else p.read_bytes(),
                                           p.stat().st_mode, p.stat().st_mtime_ns)
            for p in base.rglob("*")}


def expected_files(case, originals):
    result = dict(originals)
    for filename in {row.owner for row in case.rows}:
        page_records = slots(originals[filename])
        values = [None] * len(page_records)
        for number, row in enumerate(case.rows, 1):
            if row.owner == filename:
                assert values[row.slot] is None
                values[row.slot] = str(number)
                stored_parent, old, _, _ = page_records[row.slot]
                assert old == row.old
                assert stored_parent == (path_of(*row.path[:-1]) if len(row.path) > 1 else "/")
        assert None not in values
        result[filename] = put_values(originals[filename], values)
    return result


class IndependentQualificationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)

    def run_cli(self, project, *args):
        return subprocess.run([sys.executable, str(LAUNCHER), str(project), *args],
                              cwd=self.base, capture_output=True, text=True)

    def qualify(self, case):
        base = case.project.parent
        original = {p.name: p.read_bytes() for p in base.iterdir() if p.is_file()}
        expected = expected_files(case, original)  # Oracle fixed before invoking the utility.
        registry_data = json.loads(original[case.project.name])["schematic"]["top_level_sheets"]
        self.assertEqual([(r["filename"],r["name"],r["uuid"]) for r in registry_data], [r[:3] for r in case.roots])
        for filename, name, registered, document_uuid in case.roots:
            self.assertEqual(re.search(rb'\(uuid\s+"([^"]+)"\)', original[filename])[1].decode(), document_uuid)
            effective = document_uuid if registered == NIL else registered
            self.assertIn((effective,), [row.path for row in case.rows])
        before = snapshot(base)
        preview = self.run_cli(case.project)
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertEqual(snapshot(base), before)
        self.assertEqual(re.findall(r"Instance: (.+)", preview.stdout), [path_of(*r.path) for r in case.rows])
        self.assertEqual(re.findall(r"Source: (.+)", preview.stdout), [r.source for r in case.rows])
        for number, row in enumerate(case.rows, 1):
            self.assertIn(f"{number}. {' / '.join(repr(n) for n in row.names)}", preview.stdout)
            self.assertIn(f"Page: {row.old!r} -> {str(number)!r}", preview.stdout)
        changed = sorted(name for name in original if original[name] != expected[name])
        affected = preview.stdout.split("Affected source files:\n", 1)[1].split("Successfully", 1)[0]
        self.assertEqual([line.strip() for line in affected.splitlines()], changed)
        applied = self.run_cli(case.project, "--apply")
        self.assertEqual(applied.returncode, 0, applied.stderr)
        for name, data in expected.items():
            self.assertEqual((base / name).read_bytes(), data, name)
            self.assertEqual((base / name).stat().st_mtime_ns, before[name][3])
        backups = list((base / "backup-renumber").iterdir())
        self.assertEqual(len(backups), 1)
        self.assertTrue(backups[0].is_dir())
        saved = {p.relative_to(backups[0]).as_posix(): p.read_bytes() for p in backups[0].rglob("*") if p.is_file()}
        self.assertEqual(set(saved), set(changed))
        for name, data in saved.items():
            self.assertEqual(data, original[name])
            self.assertEqual(hashlib.sha256(data).digest(), hashlib.sha256(original[name]).digest())
        after = snapshot(base)
        again = self.run_cli(case.project, "--apply")
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertIn("already correct", again.stdout)
        self.assertEqual(snapshot(base), after)

    def test_independent_forest(self):
        self.qualify(make_forest(self.base / "forest"))

    def test_independent_nil_fallback(self):
        self.qualify(make_single(self.base / "single"))

    @unittest.skipUnless(os.environ.get("KICAD_ISSUE23403_FIXTURE"), "authentic upstream fixture path not supplied")
    def test_independent_upstream_issue23403(self):
        self.qualify(make_upstream(self.base / "upstream", Path(os.environ["KICAD_ISSUE23403_FIXTURE"])))

    @unittest.skipUnless(os.environ.get("KICAD10_APPRUN") and os.environ.get("KICAD_ISSUE23403_FIXTURE"),
                         "official KiCad 10 AppRun and authentic upstream fixture paths not supplied")
    def test_kicad10_netlist_equivalence(self):
        app = str(Path(os.environ["KICAD10_APPRUN"]).resolve())
        env = dict(os.environ)
        for kind in ("CACHE", "CONFIG", "DATA"):
            env[f"XDG_{kind}_HOME"] = str(self.base / "xdg" / kind.lower())

        def command(*args):
            result = subprocess.run([app, "kicad-cli", *args], env=env,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return result.stdout

        version = command("version").strip()
        self.assertRegex(version, r"^10\.")  # Never silently substitute system KiCad 9.
        cases = [make_forest(self.base / "forest"), make_single(self.base / "single"),
                 make_upstream(self.base / "upstream", Path(os.environ["KICAD_ISSUE23403_FIXTURE"]))]
        help_text = command("sch", "export", "netlist", "--help", str(cases[0].project.parent / cases[0].main))
        self.assertIn("kicadxml", help_text)

        def canonical(element):
            # Sort children as a multiset: repeated component references must not collapse.
            return (element.tag, tuple(sorted(element.attrib.items())),
                    (element.text or "").strip(), tuple(sorted(canonical(c) for c in element)))

        def electrical(root):
            sections = tuple(canonical(root.find(tag)) for tag in ("components", "libparts", "libraries"))
            # Net codes/order are export metadata; retain net names and every node/property.
            nets = tuple(sorted((net.get("name"), tuple(sorted(canonical(c) for c in net)))
                                for net in root.find("nets")))
            return sections, nets

        for case in cases:
            with self.subTest(project=case.project.name, kicad=version):
                exports = []
                for phase in ("before", "after"):
                    if phase == "after":
                        self.qualify(case)
                    before = snapshot(case.project.parent)
                    output = self.base / f"{case.project.stem}-{phase}.xml"
                    command("sch", "export", "netlist", "--format", "kicadxml", "--output",
                            str(output), str(case.project.parent / case.main))
                    after = snapshot(case.project.parent)
                    # KiCad itself can create/update its project-local session sidecar.
                    # The utility's stricter whole-tree no-write checks are in qualify().
                    sidecar = case.project.with_suffix(".kicad_prl").name
                    self.assertEqual({k:v for k,v in after.items() if k != sidecar},
                                     {k:v for k,v in before.items() if k != sidecar})
                    root = ET.parse(output).getroot()
                    # KiCad XML omits the display-name prefix for a single root.
                    names = [row.names if len(case.roots) > 1 else row.names[1:] for row in case.rows]
                    self.assertEqual(sorted(s.get("name") for s in root.findall("design/sheet")),
                                     sorted("/" + "/".join(parts) + ("/" if parts else "") for parts in names))
                    exports.append(root)
                self.assertEqual(electrical(exports[0]), electrical(exports[1]))

    def test_independent_interruption_and_manual_recovery(self):
        case = make_forest(self.base / "interrupted")
        base = case.project.parent
        originals = {p.name: p.read_bytes() for p in base.iterdir() if p.is_file()}
        expected = expected_files(case, originals)
        code = '''
import os,sys
from kicad_renumber import apply as writer
actual=writer._replace
def interrupted(staged,path):
 actual(staged,path)
 os._exit(73)
writer._replace=interrupted
writer.apply_project(sys.argv[1])
'''
        interrupted = subprocess.run([sys.executable,"-B","-c",code,str(case.project)], cwd=LAUNCHER.parent)
        self.assertEqual(interrupted.returncode, 73)
        marker = base / "backup-renumber/active-operation.json"
        record = json.loads(marker.read_bytes())
        backup = base / record["backup"]
        states = []
        for entry in record["files"]:
            name = entry["path"]
            old = hashlib.sha256(originals[name]).hexdigest()
            new = hashlib.sha256(expected[name]).hexdigest()
            self.assertEqual((old,new), (entry["original_sha256"],entry["expected_sha256"]))
            self.assertEqual((backup / name).read_bytes(), originals[name])
            current = hashlib.sha256((base / name).read_bytes()).hexdigest()
            states.append("original" if current == old else "expected-new" if current == new else "unknown")
        self.assertEqual(states.count("expected-new"), 1)
        self.assertEqual(states.count("unknown"), 0)
        state = snapshot(base)
        self.assertEqual(self.run_cli(case.project,"--apply").returncode, 5)
        self.assertEqual(snapshot(base), state)
        audit = self.base / "marker-audit.json"
        audit.write_bytes(marker.read_bytes())
        # Also exercise the manual procedure's unknown-content classification.
        changed = record["files"][0]
        unknown = (base / changed["path"]).read_bytes() + b"\n; unrelated external edit\n"
        (base / changed["path"]).write_bytes(unknown)
        digest = hashlib.sha256(unknown).hexdigest()
        self.assertNotIn(digest, (changed["original_sha256"], changed["expected_sha256"]))
        preserved_unknown = self.base / "unknown-content-audit.kicad_sch"
        preserved_unknown.write_bytes(unknown)
        state = snapshot(base)
        self.assertEqual(self.run_cli(case.project,"--apply").returncode, 5)
        self.assertEqual(snapshot(base), state)
        for entry in record["files"]:
            shutil.copy2(backup / entry["path"], base / entry["path"])
        for name,data in originals.items():
            self.assertEqual((base / name).read_bytes(), data)
        self.assertTrue(marker.exists())  # Evidence remains until all original checks complete.
        self.assertEqual(self.run_cli(case.project).returncode, 0)
        marker.unlink()  # Explicit test-only completion of the documented manual procedure.
        self.assertTrue(backup.is_dir())
        self.assertTrue(audit.exists())
        self.assertEqual(preserved_unknown.read_bytes(), unknown)


if __name__ == "__main__":
    unittest.main()
