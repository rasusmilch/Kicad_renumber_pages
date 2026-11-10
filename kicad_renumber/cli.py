"""Human-readable preview only; no apply, output file, or logging facility."""

import argparse
from pathlib import Path
import sys

from .engine import NumberingPlan, build_plan
from .sexpr import InvalidProject


def render(plan: NumberingPlan) -> str:
    base = plan.project.parent
    lines = [f"Project: {plan.project}", "Read-only preview (no files written)",
             f"Top-level sheets: {len(plan.roots)}", "Proposed sheet order:"]
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
    lines.append(f"Successfully analyzed; {state}: {len(plan.items)} sheets, "
                 f"{plan.change_count} page changes, {len(plan.affected_files)} affected files.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Preview KiCad 10 whole-project page numbering.")
    parser.add_argument("project", type=Path, help="explicit .kicad_pro file")
    parser.add_argument("--apply", action="store_true", help="unsupported: writes are not implemented")
    args = parser.parse_args(argv)
    if args.apply:
        parser.error("unsupported operation: --apply is not implemented; preview only, no files written")
    try:
        plan = build_plan(args.project)
        print(render(plan))
        return 0
    except InvalidProject as exc:
        print(f"Invalid or unsupported project: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Internal failure ({type(exc).__name__}): {exc}", file=sys.stderr)
        return 3
