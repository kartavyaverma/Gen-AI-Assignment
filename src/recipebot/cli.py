"""Terminal version of the chatbot:  uv run recipebot-cli

Type 'quit' to exit, 'reset' to start over, 'debug' to toggle printing the router's JSON plan.
"""

from __future__ import annotations

import sys

from .agent import RecipeBot, plan_to_json


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print("Loading recipes...")
    bot = RecipeBot()
    debug = False
    print("RecipeBot ready. Ask me something (or 'quit').\n")
    while True:
        try:
            msg = input("you > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if msg.lower() in ("quit", "exit", "q"):
            break
        if msg.lower() == "debug":
            debug = not debug
            print(f"(debug {'on' if debug else 'off'})")
            continue
        reply = bot.handle(msg)
        if debug:
            print(plan_to_json(reply.trace.get("plan", {})))
        print("\nbot >\n" + reply.markdown + "\n")


if __name__ == "__main__":
    main()
