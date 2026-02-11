"""Module entrypoint for `python -m psyker`."""

from __future__ import annotations

from .cli import create_default_cli


def main() -> int:
    cli = create_default_cli()
    return cli.run_repl()


if __name__ == "__main__":
    raise SystemExit(main())
