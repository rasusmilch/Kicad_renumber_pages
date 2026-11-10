"""Supported KiCad 10 extraction, instance expansion, and immutable planning.

There are no filesystem write operations in this module. Candidate edits are
constructed and reparsed in memory solely to verify the future edit locations.
"""

from dataclasses import dataclass, replace
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import stat
from uuid import UUID

from .sexpr import Atom, Expr, InvalidProject, atom, children, only, parse, scalar


@dataclass(frozen=True)
class Snapshot:
    path: Path
    data: bytes
    digest: str
    identity: tuple[int, ...]


@dataclass(frozen=True)
class PageLocation:
    file: Path
    start: int
    end: int


@dataclass(frozen=True)
class PlannedItem:
    instance_path: tuple[str, ...]
    hierarchy: tuple[str, ...]
    display_name: str
    source_file: Path
    old_page: str
    new_page: str
    location: PageLocation

    @property
    def changed(self) -> bool:
        return self.old_page != self.new_page


@dataclass(frozen=True)
class PageEdit:
    location: PageLocation
    original: bytes
    replacement: bytes


@dataclass(frozen=True)
class NumberingPlan:
    project: Path
    roots: tuple[str, ...]
    snapshots: tuple[Snapshot, ...]
    items: tuple[PlannedItem, ...]
    edits: tuple[PageEdit, ...]

    @property
    def change_count(self) -> int:
        return len(self.edits)

    @property
    def affected_files(self) -> tuple[Path, ...]:
        return tuple(sorted({e.location.file for e in self.edits}))


@dataclass(frozen=True)
class Sheet:
    uuid: str
    name: str
    filename: str
    # The stored path is the PARENT instance path, not the child's identity.
    pages: tuple[tuple[tuple[str, ...], Atom], ...]


@dataclass(frozen=True)
class Document:
    path: Path
    uuid: str
    root_page: Atom | None
    sheets: tuple[Sheet, ...]


def _uuid(value: object, *, allow_nil: bool = False) -> str:
    if not isinstance(value, str):
        raise InvalidProject("UUID must be a string")
    try:
        parsed = UUID(value)
    except ValueError as exc:
        raise InvalidProject(f"invalid UUID: {value!r}") from exc
    if str(parsed) != value.lower() or (not parsed.int and not allow_nil):
        raise InvalidProject(f"unsupported UUID spelling: {value!r}")
    return str(parsed)


def _instance_path(value: str) -> tuple[str, ...]:
    if not value.startswith("/") or value.endswith("/"):
        raise InvalidProject(f"invalid parent instance path: {value!r}")
    return tuple(_uuid(part) for part in value[1:].split("/"))


def natural_key(name: str, identity: tuple[str, ...]) -> tuple:
    # Length + lexical digits compares arbitrary-size nonnegative integers
    # without Python's decimal-to-int digit limit on untrusted sheet names.
    chunks = tuple(
        (1, len(part.lstrip("0")), part.lstrip("0"))
        if part.isascii() and part.isdigit() else (0, part)
        for part in re.split(r"([0-9]+)", name.casefold())
    )
    return chunks, name, identity


def _identity(info: os.stat_result) -> tuple[int, ...]:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _check_components(path: Path) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink():
            raise InvalidProject(f"symlink source path is unsupported: {current}")


def _read(path: Path) -> Snapshot:
    try:
        _check_components(path)
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise InvalidProject(f"expected an unaliased regular file: {path}")
        with path.open("rb") as handle:
            opened = handle.fileno()
            if _identity(os.fstat(opened)) != _identity(before):
                raise InvalidProject(f"source changed while opening: {path}")
            data = handle.read()
            if _identity(os.fstat(opened)) != _identity(before):
                raise InvalidProject(f"source changed while reading: {path}")
        if _identity(path.lstat()) != _identity(before):
            raise InvalidProject(f"source replaced while reading: {path}")
        return Snapshot(path, data, hashlib.sha256(data).hexdigest(), _identity(before))
    except OSError as exc:
        raise InvalidProject(f"cannot read {path}: {exc.strerror}") from exc


def _reference(base: Path, value: object, project_dir: Path) -> Path:
    if not isinstance(value, str) or not value or "\0" in value:
        raise InvalidProject("missing or invalid schematic filename")
    windows = PureWindowsPath(value)
    if Path(value).is_absolute() or windows.drive or windows.root or "${" in value:
        raise InvalidProject(f"unsupported schematic reference: {value!r}")
    candidate = base / value.replace("\\", "/")
    try:
        _check_components(candidate)
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise InvalidProject(f"cannot resolve referenced sheet {value!r}: {exc.strerror}") from exc
    if not resolved.is_relative_to(project_dir):
        raise InvalidProject(f"reference outside project directory: {value!r}")
    if resolved.suffix != ".kicad_sch":
        raise InvalidProject(f"expected .kicad_sch reference: {value!r}")
    return resolved


def _json_pairs(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise InvalidProject(f"duplicate project JSON key: {key}")
        result[key] = value
    return result


def _bad_constant(value: str) -> None:
    raise InvalidProject(f"invalid JSON constant: {value}")


def _project_roots(snapshot: Snapshot) -> tuple[tuple[str, str, str], ...]:
    try:
        project = json.loads(snapshot.data, object_pairs_hook=_json_pairs,
                             parse_constant=_bad_constant)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise InvalidProject(f"invalid project JSON: {exc}") from exc
    schematic = project.get("schematic") if isinstance(project, dict) else None
    roots = schematic.get("top_level_sheets") if isinstance(schematic, dict) else None
    if not isinstance(roots, list) or not roots:
        raise InvalidProject("schematic.top_level_sheets must be a nonempty array")
    result = []
    for root in roots:
        if not isinstance(root, dict):
            raise InvalidProject("top-level sheet must be an object")
        filename, name = root.get("filename"), root.get("name")
        if not isinstance(filename, str) or not filename or not isinstance(name, str) or not name:
            raise InvalidProject("top-level sheet requires filename and name strings")
        result.append((filename, name, _uuid(root.get("uuid"), allow_nil=True)))
    return tuple(result)


def _page(path: Expr) -> Atom:
    if len(path.items) != 3:
        raise InvalidProject("malformed page path record")
    return scalar(only(path, "page"))


def _property(sheet: Expr, name: str) -> str:
    matches = [p for p in children(sheet, "property") if atom(p).value == name]
    if len(matches) != 1:
        raise InvalidProject(f"expected exactly one sheet property {name}")
    value = atom(matches[0], 2).value
    if not value:
        raise InvalidProject(f"empty sheet property {name}")
    return value


def _sheet(node: Expr, project_name: str) -> Sheet:
    allowed = {"at", "size", "exclude_from_sim", "in_bom", "on_board", "dnp",
               "fields_autoplaced", "stroke", "fill", "uuid", "property", "pin", "instances"}
    if any(not isinstance(x, Expr) or x.head not in allowed for x in node.items[1:]):
        raise InvalidProject("unsupported sheet-symbol syntax")
    uuid = _uuid(scalar(only(node, "uuid")).value)
    name, filename = _property(node, "Sheetname"), _property(node, "Sheetfile")
    groups = only(node, "instances")
    matching = []
    for group in groups.items[1:]:
        if not isinstance(group, Expr) or group.head != "project":
            raise InvalidProject("unsupported sheet instance group")
        if atom(group).value == project_name:
            matching.append(group)
    if len(matching) > 1:
        raise InvalidProject("duplicate current-project instance group")
    pages = []
    seen = set()
    for record in matching[0].items[2:] if matching else ():
        if not isinstance(record, Expr) or record.head != "path":
            raise InvalidProject("unsupported current-project sheet instance record")
        parent = _instance_path(atom(record).value)
        if parent in seen:
            raise InvalidProject("duplicate parent instance path record")
        seen.add(parent)
        pages.append((parent, _page(record)))
    return Sheet(uuid, name, filename, tuple(pages))


# Non-hierarchy content, including known drawing objects, is parsed losslessly
# and left opaque. Unknown document-level constructs still fail closed.
_DOCUMENT_HEADS = frozenset("""
version generator generator_version uuid paper title_block lib_symbols
junction no_connect bus_entry wire bus polyline text text_box label global_label
hierarchical_label netclass_flag sheet symbol image bus_alias sheet_instances
embedded_fonts embedded_files rule_area rectangle table
""".split())


def _document(snapshot: Snapshot, project_name: str) -> Document:
    try:
        tree = parse(snapshot.data)
        if tree.head != "kicad_sch":
            raise InvalidProject("expected kicad_sch document")
        for node in tree.items[1:]:
            if not isinstance(node, Expr) or node.head not in _DOCUMENT_HEADS:
                raise InvalidProject("unsupported schematic top-level syntax")
        if scalar(only(tree, "version"), quoted=False).value != "20260306":
            raise InvalidProject("unsupported schematic version; expected 20260306")
        if scalar(only(tree, "generator_version")).value != "10.0":
            raise InvalidProject('unsupported generator_version; expected "10.0"')
        uuid = _uuid(scalar(only(tree, "uuid")).value)
        root_page = None
        root_groups = children(tree, "sheet_instances")
        if len(root_groups) > 1:
            raise InvalidProject("duplicate root sheet_instances record")
        if root_groups:
            paths = children(root_groups[0], "path")
            if len(root_groups[0].items) != 2 or len(paths) != 1 or atom(paths[0]).value != "/":
                raise InvalidProject("ambiguous root page record")
            root_page = _page(paths[0])
        sheets = tuple(_sheet(s, project_name) for s in children(tree, "sheet"))
        if len({s.uuid for s in sheets}) != len(sheets):
            raise InvalidProject("duplicate sheet-symbol UUID in source document")
        return Document(snapshot.path, uuid, root_page, sheets)
    except InvalidProject as exc:
        raise InvalidProject(f"{snapshot.path}: {exc}") from exc


def _discover(project: Path, supplied: dict[Path, Snapshot] | None = None) -> NumberingPlan:
    snapshots: dict[Path, Snapshot] = {}
    documents: dict[Path, Document] = {}

    def load(path: Path) -> Snapshot:
        if path not in snapshots:
            if supplied is not None:
                if path not in supplied:
                    raise InvalidProject("candidate graph references a new source file")
                snapshots[path] = supplied[path]
            else:
                snapshots[path] = _read(path)
        return snapshots[path]

    def document(path: Path) -> Document:
        if path not in documents:
            doc = _document(load(path), project.stem)
            documents[path] = doc
        return documents[path]

    roots = []
    for filename, name, registered_uuid in _project_roots(load(project)):
        path = _reference(project.parent, filename, project.parent)
        if path in {r[0] for r in roots}:
            raise InvalidProject("same top-level source listed repeatedly")
        doc = document(path)
        # Registry UUID is the sheet INSTANCE identity, not the document UUID.
        # Only an explicit nil registry UUID falls back to the document UUID.
        effective_uuid = registered_uuid if UUID(registered_uuid).int else doc.uuid
        if effective_uuid in {r[2] for r in roots}:
            raise InvalidProject("duplicate effective top-level sheet UUID")
        if doc.root_page is None:
            raise InvalidProject(f"missing root page record: {path}")
        roots.append((path, name, effective_uuid))
    roots.sort(key=lambda r: natural_key(r[1], (r[2],)))
    items: list[PlannedItem] = []
    seen_paths: set[tuple[str, ...]] = set()
    locations: set[PageLocation] = set()
    consumed: set[tuple[Path, str, tuple[str, ...]]] = set()

    def visit(path: Path, identity: tuple[str, ...], names: tuple[str, ...],
              page: Atom, owner: Path, ancestry: tuple[Path, ...]) -> None:
        if path in ancestry:
            raise InvalidProject(f"schematic include cycle: {path}")
        if len(ancestry) >= 200:
            raise InvalidProject("unsupported hierarchy depth beyond 200 levels")
        if identity in seen_paths:
            raise InvalidProject("duplicate full sheet-instance identity")
        seen_paths.add(identity)
        location = PageLocation(owner, page.start, page.end)
        if location in locations:
            raise InvalidProject("page token is shared by distinct sheet instances")
        locations.add(location)
        doc = document(path)
        items.append(PlannedItem(identity, names, names[-1], path, page.value,
                                 str(len(items) + 1), location))
        for sheet in sorted(doc.sheets, key=lambda s: natural_key(s.name, identity + (s.uuid,))):
            pages = dict(sheet.pages)
            if identity not in pages:
                raise InvalidProject(f"missing page record for {sheet.name!r} at /{'/'.join(identity)}")
            consumed.add((path, sheet.uuid, identity))
            child = _reference(path.parent, sheet.filename, project.parent)
            visit(child, identity + (sheet.uuid,), names + (sheet.name,),
                  pages[identity], path, ancestry + (path,))

    for path, name, uuid in roots:
        page = documents[path].root_page
        assert page is not None
        visit(path, (uuid,), (name,), page, path, ())
    expected = {(doc.path, sheet.uuid, parent)
                for doc in documents.values() for sheet in doc.sheets for parent, _ in sheet.pages}
    if expected != consumed:
        raise InvalidProject("current-project instance records do not match reachable graph")
    edits = []
    for item in items:
        if item.changed:
            loc = item.location
            original = snapshots[loc.file].data[loc.start:loc.end]
            edits.append(PageEdit(loc, original, b'"' + item.new_page.encode("ascii") + b'"'))
    return NumberingPlan(project, tuple(r[1] for r in roots),
                         tuple(snapshots[p] for p in sorted(snapshots)), tuple(items), tuple(edits))


def candidate_bytes(plan: NumberingPlan) -> tuple[tuple[Path, bytes], ...]:
    """Materialize targeted replacements in memory, never on disk."""
    result = []
    for snapshot in plan.snapshots:
        edits = sorted((e for e in plan.edits if e.location.file == snapshot.path),
                       key=lambda e: e.location.start)
        if not edits:
            continue
        cursor = 0
        parts = []
        for edit in edits:
            loc = edit.location
            if loc.start < cursor or loc.end <= loc.start or loc.end > len(snapshot.data):
                raise InvalidProject("overlapping or invalid page-value byte spans")
            if snapshot.data[loc.start:loc.end] != edit.original:
                raise InvalidProject("page span does not match original snapshot")
            parts.extend((snapshot.data[cursor:loc.start], edit.replacement))
            cursor = loc.end
        parts.append(snapshot.data[cursor:])
        result.append((snapshot.path, b"".join(parts)))
    return tuple(result)


def build_plan(project_path: str | Path) -> NumberingPlan:
    """Analyze a supported project and verify its proposed page-only edits."""
    supplied_path = Path(project_path)
    if not supplied_path.is_absolute():
        supplied_path = Path.cwd() / supplied_path
    _check_components(supplied_path)
    project = Path(os.path.abspath(supplied_path))
    if project.suffix != ".kicad_pro":
        raise InvalidProject("an explicit .kicad_pro path is required")
    plan = _discover(project)
    candidates = dict(candidate_bytes(plan))
    supplied = {s.path: replace(s, data=candidates.get(s.path, s.data)) for s in plan.snapshots}
    verified = _discover(project, supplied)
    expected = tuple((i.instance_path, i.hierarchy, i.source_file, i.new_page) for i in plan.items)
    actual = tuple((i.instance_path, i.hierarchy, i.source_file, i.old_page) for i in verified.items)
    if actual != expected or verified.edits or set(supplied) != {s.path for s in verified.snapshots}:
        raise InvalidProject("candidate instance graph or numbering verification failed")
    for snapshot in plan.snapshots:
        current = _read(snapshot.path)
        if current.identity != snapshot.identity or current.data != snapshot.data:
            raise InvalidProject(f"source changed during analysis: {snapshot.path}")
    return plan
