"""Module entrypoint for `python -m psyker`."""

from __future__ import annotations

from .entry import run


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
