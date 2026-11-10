"""Read-only launcher; suppress import caches as well as project writes."""

import sys

sys.dont_write_bytecode = True

from kicad_renumber.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
