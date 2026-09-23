"""Chat with the local textbook LangGraph agent."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from langchain.messages import AIMessage, HumanMessage

from textbook_agent import build_agent


def ask(question: str) -> str:
    """Run one grounded question through the agent and return its final answer."""
    result = build_agent().invoke(
        {"messages": [HumanMessage(content=question)]},
        config={"recursion_limit": 8},
    )
    final_message = result["messages"][-1]
    if not isinstance(final_message, AIMessage):
        raise TypeError("Agent did not return an AI response.")
    return str(final_message.content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="*")
    args = parser.parse_args()

    if args.question:
        print(ask(" ".join(args.question)))
        return 0

    print("Local textbook assistant. Type 'exit' to stop.")
    while True:
        try:
            question = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if question.lower() in {"exit", "quit"}:
            return 0
        if question:
            print(f"\nAssistant: {ask(question)}")


if __name__ == "__main__":
    sys.exit(main())
