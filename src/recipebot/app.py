"""Gradio web UI.  Run with:  uv run recipebot-ui   (then open http://127.0.0.1:7860)

Each browser tab gets its own RecipeBot (its own conversation state); the big
recipe store is loaded once and shared.
"""

from __future__ import annotations

import gradio as gr

from .agent import RecipeBot, plan_to_json
from .store import load_store

EXAMPLES = [
    "Find a penne pasta recipe",
    "I cannot have dairy",
    "How many recipes contain both garlic and onion? What percentage of the dataset is that?",
    "Among recipes containing tomato, which five have the fewest instruction steps?",
    "I have eggs, onions, tomatoes and rice. Suggest five recipes using as many as possible, no peanuts, at most six steps, fewest extra ingredients.",
    "Exclude eggs too",
    "Find a banana bread recipe",
    "Take this banana bread recipe and remove the eggs. Use only ingredients that appear in the dataset.",
    "How many calories does it have?",
]


def _constraints_md(bot: RecipeBot | None) -> str:
    if bot is None:
        return "_No active constraints yet._"
    s = bot.state
    lines = ["**Active state**",
             f"- Search: {s.query or '–'}",
             f"- Must include: {', '.join(s.include) or '–'}",
             f"- Restrictions: {', '.join(s.exclude) or '–'}",
             f"- Max steps: {s.max_steps if s.max_steps is not None else '–'}",
             f"- Pantry: {', '.join(s.pantry) if s.pantry else '–'}",
             f"- Recipe in focus: `{s.focus}`" if s.focus else "- Recipe in focus: –"]
    return "\n".join(lines)


def respond(message, history, bot):
    if bot is None:
        bot = RecipeBot(store=load_store())
    reply = bot.handle(message)
    history = (history or []) + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": reply.markdown},
    ]
    trace = plan_to_json(reply.trace.get("plan", reply.trace))
    return "", history, bot, _constraints_md(bot), trace


def reset(bot):
    return [], None, _constraints_md(None), ""


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="RecipeBot") as demo:
        gr.Markdown(
            "# 🍳 RecipeBot\n"
            "Search, analyse, match and adapt ~123k recipes from the Recipe Box dataset. "
            "Every recipe fact comes from the data (with IDs); every number is computed, not guessed."
        )
        bot_state = gr.State(None)
        with gr.Row():
            with gr.Column(scale=3):
                chat = gr.Chatbot(height=620, label="Conversation", buttons=["copy"])
                with gr.Row():
                    box = gr.Textbox(placeholder="e.g. Find a penne pasta recipe", scale=5, show_label=False)
                    send = gr.Button("Send", variant="primary", scale=1)
                gr.Examples(EXAMPLES, inputs=box, label="Try these (in order for the multi-turn demo)")
            with gr.Column(scale=1):
                state_md = gr.Markdown(_constraints_md(None))
                clear = gr.Button("🔄 New conversation")
                with gr.Accordion("How I understood your last message (router JSON)", open=False):
                    trace = gr.Code(language="json", label="LLM plan")
                gr.Markdown(
                    "**Notes**\n- Restrictions stick until you change them.\n"
                    "- Say *show 2* to open a result.\n"
                    "- The dataset has no nutrition or cooking times."
                )

        outputs = [box, chat, bot_state, state_md, trace]
        box.submit(respond, [box, chat, bot_state], outputs)
        send.click(respond, [box, chat, bot_state], outputs)
        clear.click(reset, [bot_state], [chat, bot_state, state_md, trace])
    return demo


def main() -> None:
    print("Loading recipes (first run builds the index, ~2 min)...")
    load_store()
    build_ui().launch(server_name="127.0.0.1", server_port=7860)


if __name__ == "__main__":
    main()
