"""Command-line interface for the core and agentic runtimes."""
from __future__ import annotations
import argparse
import json
from jarvis.agentic.copilot import CopilotAgent
from jarvis.agentic.wingman import WingmanAgent
from jarvis.app.launcher import JARVISLauncher
from jarvis.benchmarks.runner import benchmark_agentic_runtime


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jarvis")
    parser.add_argument("--query", default="Explain quantum-classical hybrid transformer architecture")
    parser.add_argument("--domain", default=None)
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--wingman", action="store_true")
    parser.add_argument("--approve", action="store_true")
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--audit", default=None)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.benchmark:
        print(json.dumps(benchmark_agentic_runtime(), indent=2)); return
    if args.wingman:
        agent = WingmanAgent(); result = agent.execute(args.query, domain=args.domain or "agentic", approve=args.approve)
        if args.audit: agent.audit.export(args.audit)
        print(json.dumps(result, indent=2, default=str)); return
    launcher = JARVISLauncher()
    if args.status: print(json.dumps(launcher.status(), indent=2, default=str)); return
    if args.interactive:
        while True:
            try: query = input("JARVIS> ").strip()
            except (EOFError, KeyboardInterrupt): break
            if query.casefold() in {"exit", "quit", "q"}: break
            if query: print(launcher.run(query, domain=args.domain))
        return
    print(launcher.run(args.query, domain=args.domain))


if __name__ == "__main__":
    main()
