"""CLI launcher; suppress incidental import caches in both operating modes."""

import sys

sys.dont_write_bytecode = True

from kicad_renumber.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
