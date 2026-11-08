from __future__ import annotations

import streamlit as st

from recipebot.agent import RecipeBot
from recipebot.store import load_store

st.set_page_config(page_title="RecipeBot")

EXAMPLES = [
    "Find a penne pasta recipe",
    "I cannot have dairy",
    "Show me the second one",
    "How many recipes contain both garlic and onion?",
    "Among recipes containing tomato, which five have the fewest steps?",
    "I have eggs, onions, tomatoes and rice. No peanuts, at most 6 steps.",
    "Exclude eggs too",
    "Find a banana bread recipe",
    "Remove the eggs from this recipe",
]


@st.cache_resource(show_spinner="Loading recipes...")
def get_store():
    return load_store()


def get_bot() -> RecipeBot:
    if "bot" not in st.session_state:
        st.session_state.bot = RecipeBot(store=get_store())
        st.session_state.messages = []
    return st.session_state.bot


def safe_md(text: str) -> str:
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
    with st.spinner("Searching..."):
        reply = bot.handle(prompt)
    st.session_state.messages.append(
        {"role": "assistant", "content": reply.markdown, "plan": reply.trace.get("plan")}
    )


def render_sidebar(bot: RecipeBot) -> None:
    s = bot.state
    with st.sidebar:
        st.header("RecipeBot")
        st.write(f"{len(bot.store):,} recipes loaded")

        if st.button("New chat"):
            st.session_state.pop("bot", None)
            st.session_state.messages = []
            st.rerun()

        st.subheader("Current filters")
        active = []
        if s.query:
            active.append(f"Search: {s.query}")
        if s.include:
            active.append("Must include: " + ", ".join(s.include))
        if s.exclude:
            active.append("Excluding: " + ", ".join(s.exclude))
        if s.max_steps is not None:
            active.append(f"Max steps: {s.max_steps}")
        if s.pantry:
            active.append("Ingredients you have: " + ", ".join(s.pantry))
        if s.focus:
            r = bot.store.get(s.focus)
            if r is not None:
                active.append(f"Current recipe: {r['title']}")
        st.text("\n".join(active) if active else "None")

        with st.expander("Example questions"):
            st.markdown("\n".join(f"- {e}" for e in EXAMPLES))


def main() -> None:
    bot = get_bot()
    render_sidebar(bot)

    st.title("RecipeBot")
    st.write("Ask questions about recipes in the Recipe Box dataset.")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(safe_md(msg["content"]))
            if msg.get("plan"):
                with st.expander("Parsed request"):
                    st.json(msg["plan"])

    prompt = st.chat_input("Type your question")
    if prompt:
        ask(prompt)
        st.rerun()


main()
