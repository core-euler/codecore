"""Executable entrypoint for CodeCore."""

from __future__ import annotations

import argparse

from .app import main as interactive_main
from .split import create_split_app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="codecore")
    parser.add_argument("--split", action="store_true", help="Run architect/executor split mode")
    parser.add_argument("--mode", choices=("incremental", "rebuild"), default="incremental", help="Execution mode for split sessions")
    args = parser.parse_args(argv)
    if args.split:
        return create_split_app(mode=args.mode).run()
    return interactive_main()


if __name__ == "__main__":
    raise SystemExit(main())
