"""Command-line interface for the JARVIS v7 runtime."""

from __future__ import annotations

import argparse
import json

from jarvis.app.launcher import JARVISLauncher


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jarvis", description="JARVIS v7 unified runtime")
    parser.add_argument("--query", default="Explain quantum-classical hybrid transformer architecture")
    parser.add_argument("--domain", default=None)
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--interactive", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    launcher = JARVISLauncher()
    if args.status:
        print(json.dumps(launcher.status(), indent=2, default=str))
        return
    if args.interactive:
        while True:
            try:
                query = input("JARVIS> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if query.lower() in {"exit", "quit", "q"}:
                break
            if query:
                print(launcher.run(query, domain=args.domain))
        return
    print(launcher.run(args.query, domain=args.domain))


if __name__ == "__main__":
    main()
