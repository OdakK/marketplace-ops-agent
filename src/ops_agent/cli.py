"""Command line: ask one question, or start an interactive session.

    ops-agent "Which contractors take the longest to answer new leads?"
    ops-agent            # interactive
"""

from __future__ import annotations

import argparse
import asyncio

from . import tracing
from .agent import DEFAULT_MODEL, ask, load_model, open_agent


async def run(question: str | None, model: str, verbose: bool) -> None:
    async with open_agent(load_model(model)) as graph:
        questions = [question] if question else None
        while True:
            q = questions.pop() if questions else input("\nyou> ").strip()
            if not q or q in {"exit", "quit"}:
                return
            result = await ask(graph, q, callbacks=tracing.callbacks())
            if verbose:
                for call in result["tool_calls"]:
                    print(f"  [tool] {call['name']}({call['args']})")
            print(f"\nagent> {result['answer']}")
            if question:
                return


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("question", nargs="?")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="provider:model, e.g. openai:gpt-4.1-mini")
    parser.add_argument("-v", "--verbose", action="store_true", help="print tool calls")
    args = parser.parse_args()
    asyncio.run(run(args.question, args.model, args.verbose))


if __name__ == "__main__":
    main()
