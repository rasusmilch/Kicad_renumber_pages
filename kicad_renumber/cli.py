"""Human-readable preview and explicit controlled apply; no reporting files."""

import argparse
from pathlib import Path
import sys

from .engine import NumberingPlan, build_plan
from .apply import ApplyFailure, EDITOR_WARNING, apply_project
from .sexpr import InvalidProject


def render(plan: NumberingPlan, *, applied: bool = False) -> str:
    base = plan.project.parent
    mode = "Read-only preview (no files written)"
    if applied:
        mode = "Applied and verified" if plan.edits else "Apply no-op (no files written)"
    lines = [f"Project: {plan.project}", mode,
             f"Top-level sheets: {len(plan.roots)}",
             "Verified sheet order:" if applied else "Proposed sheet order:"]
    for index, item in enumerate(plan.items, 1):
        location = item.location
        status = "change" if item.changed else "unchanged"
        lines.extend([
            f"  {index}. {' / '.join(repr(n) for n in item.hierarchy)}",
            f"     Instance: /{'/'.join(item.instance_path)}",
            f"     Source: {item.source_file.relative_to(base)}",
            f"     Page: {item.old_page!r} -> {item.new_page!r} [{status}]",
            f"     Page token: {location.file.relative_to(base)} bytes [{location.start}, {location.end})",
        ])
    lines.append("Affected source files:")
    lines.extend(f"  {p.relative_to(base)}" for p in plan.affected_files)
    if not plan.affected_files:
        lines.append("  (none)")
    state = "changes required" if plan.change_count else "already correct"
    outcome = "Successfully applied and verified" if applied and plan.edits else f"Successfully analyzed; {state}"
    lines.append(f"{outcome}: {len(plan.items)} sheets, "
                 f"{plan.change_count} page changes, {len(plan.affected_files)} affected files.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Preview or explicitly apply KiCad 10 whole-project page numbering.")
    parser.add_argument("project", type=Path, help="explicit .kicad_pro file")
    parser.add_argument("--apply", action="store_true", help="apply page changes with mandatory verified backups; close KiCad first")
    args = parser.parse_args(argv)
    try:
        if args.apply:
            print(f"Warning: {EDITOR_WARNING}", file=sys.stderr)
            result = apply_project(args.project)
            print(render(result.plan, applied=True))
            if result.backup is not None:
                print(f"Verified backups retained: {result.backup}")
            return 0
        print(render(build_plan(args.project)))
        return 0
    except ApplyFailure as exc:
        label = "Application incomplete; manual recovery required" if exc.incomplete else "Application failed"
        print(f"{label}: {exc}", file=sys.stderr)
        return 5 if exc.incomplete else 4
    except InvalidProject as exc:
        print(f"Invalid or unsupported project: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Internal failure ({type(exc).__name__}): {exc}", file=sys.stderr)
        return 3
