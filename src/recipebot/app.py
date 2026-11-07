"""Streamlit web UI.

Start it with:   uv run recipebot-ui      (opens http://localhost:8501)
or directly:     uv run streamlit run src/recipebot/app.py

Each browser session gets its own RecipeBot (its own conversation state);
the big recipe store is loaded once per server and shared.
"""

from __future__ import annotations

import streamlit as st

from recipebot.agent import RecipeBot
from recipebot.data import SOURCE_NAMES
from recipebot.store import load_store

st.set_page_config(page_title="RecipeBot", page_icon="🍳", layout="wide")

EXAMPLES = [
    ("🔎 Search", "Find a penne pasta recipe"),
    ("🚫 Refine", "I cannot have dairy"),
    ("📖 Open a result", "Show me the second one"),
    ("📊 Count", "How many recipes contain both garlic and onion? What percentage of the dataset is that?"),
    ("📊 Rank", "Among recipes containing tomato, which five have the fewest instruction steps?"),
    ("🥕 Pantry", "I have eggs, onions, tomatoes and rice. Suggest five recipes using as many as possible, "
                 "no peanuts, at most six steps, fewest extra ingredients."),
    ("🥕 Follow-up", "Exclude eggs too"),
    ("🔁 Substitute", "Find a banana bread recipe"),
    ("🔁 Remove eggs", "Take this banana bread recipe and remove the eggs. Use only ingredients that appear in the dataset."),
    ("❓ Unsupported", "How many calories does it have?"),
]


@st.cache_resource(show_spinner="Loading 123k recipes (first start builds the index, ~2 min)…")
def get_store():
    return load_store()


def get_bot() -> RecipeBot:
    if "bot" not in st.session_state:
        st.session_state.bot = RecipeBot(store=get_store())
        st.session_state.messages = []
    return st.session_state.bot


def safe_md(text: str) -> str:
    """Make the bot's markdown render the way it's written.

    * Streamlit renders $...$ as LaTeX - recipe text should stay literal.
    * Markdown joins single line breaks into one paragraph; the answers use one
      line per result/fact, so turn those into hard breaks (except table rows,
      which must stay untouched).
    """
    text = text.replace("$", "\\$")
    out = []
    for line in text.split("\n"):
        if line.strip() and not line.lstrip().startswith("|"):
            line = line.rstrip() + "  "
        out.append(line)
    return "\n".join(out)


def ask(prompt: str) -> None:
    bot = get_bot()
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.spinner("Thinking…"):
        reply = bot.handle(prompt)
    st.session_state.messages.append(
        {"role": "assistant", "content": reply.markdown, "plan": reply.trace.get("plan")}
    )


def render_sidebar(bot: RecipeBot) -> None:
    s = bot.state
    with st.sidebar:
        st.markdown("### 🍳 RecipeBot")
        st.caption(f"{len(bot.store):,} recipes from {', '.join(SOURCE_NAMES.values())}")

        if st.button("🔄 New conversation", width="stretch"):
            st.session_state.pop("bot", None)
            st.session_state.messages = []
            st.rerun()

        st.markdown("#### Active state")
        rows = {
            "Search": s.query or "–",
            "Must include": ", ".join(s.include) or "–",
            "Restrictions": ", ".join(s.exclude) or "–",
            "Max steps": s.max_steps if s.max_steps is not None else "–",
            "Pantry": ", ".join(s.pantry) if s.pantry else "–",
        }
        for k, v in rows.items():
            st.markdown(f"**{k}:** {v}")
        if s.focus:
            r = bot.store.get(s.focus)
            st.markdown(f"**In focus:** {r['title'] if r is not None else ''}  \n`{s.focus}`")
        st.caption("Restrictions stay on for later searches, matches and substitutions until you change them.")

        st.markdown("#### Try these (in order)")
        for label, prompt in EXAMPLES:
            if st.button(label, help=prompt, key=f"ex_{label}", width="stretch"):
                st.session_state.pending = prompt
                st.rerun()

        st.divider()
        st.caption("Every recipe fact comes from the dataset (with IDs) and every number is computed in code, "
                   "not by the LLM. The dataset has no nutrition or cooking-time data.")


def render_welcome() -> None:
    st.markdown(
        """
#### What I can do
| | Example |
|---|---|
| **Search** recipes by dish, ingredient or description | *Find a penne pasta recipe* → *I cannot have dairy* |
| **Statistics** over the whole dataset | *How many recipes contain garlic and onion?* |
| **Match** what's in your kitchen | *I have eggs, onions, tomatoes and rice…* → *Exclude eggs too* |
| **Adapt** a recipe with evidence | *Remove the eggs from this banana bread* |

Pick an example from the sidebar or type below.
"""
    )


def main() -> None:
    bot = get_bot()
    render_sidebar(bot)

    st.title("RecipeBot")
    st.caption("Search, analyse, match and adapt recipes — grounded in the Recipe Box dataset.")

    if not st.session_state.messages:
        render_welcome()

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "🍳"):
            st.markdown(safe_md(msg["content"]))
            if msg.get("plan"):
                with st.expander("🔍 How I understood this (router JSON)"):
                    st.json(msg["plan"])

    prompt = st.chat_input("Ask about recipes…")
    pending = st.session_state.pop("pending", None)
    if prompt or pending:
        ask(prompt or pending)
        st.rerun()


main()
