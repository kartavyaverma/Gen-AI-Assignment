from __future__ import annotations

import json
import re
import time

from .config import GROQ_API_KEY, GROQ_MODEL


class LLMUnavailable(RuntimeError):
    pass


_client = None


def _get_client():
    global _client
    if _client is None:
        if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_key_here":
            raise LLMUnavailable("GROQ_API_KEY is not set. Copy .env.example to .env and add your key.")
        from groq import Groq

        _client = Groq(api_key=GROQ_API_KEY)
    return _client


def _create(**kwargs):
    import groq

    client = _get_client()
    for attempt in range(4):
        try:
            return client.chat.completions.create(model=GROQ_MODEL, **kwargs)
        except (groq.RateLimitError, groq.APIConnectionError, groq.InternalServerError):
            if attempt == 3:
                raise
            time.sleep(4 * (attempt + 1))


def chat_json(system: str, user: str, temperature: float = 0.0, max_tokens: int = 1200) -> dict:
    resp = _create(
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    text = resp.choices[0].message.content or "{}"
    return json.loads(text)


def chat_text(system: str, user: str, temperature: float = 0.0, max_tokens: int = 800) -> str:
    resp = _create(
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or ""


ROUTER_PROMPT = """You are the request parser for a recipe chatbot built on the Recipe Box dataset
(~123k recipes from Allrecipes, Epicurious and Food Network). The dataset ONLY has, per recipe:
an ID, a title, an ingredient list (free text lines) and instruction text. It has NO nutrition,
calories, cooking/prep times, servings, ratings, cuisines, prices or images.

You do NOT answer the user. You output ONE JSON object describing what the program should do.
The program does all searching, counting and ranking itself.

Conversation state is given to you. Follow-ups refer to it ("I can't have dairy", "exclude eggs
too", "show me the second one", "what about with chicken instead?").

Output JSON with these keys (omit keys you don't need):
{
  "intent": one of
     "search"       - find recipes by dish name / ingredients / description
     "show_recipe"  - show ingredients/instructions of a recipe already mentioned
     "more"         - show more results for the current search
     "stats"        - counts, percentages, most common ingredients, average/median ingredient or
                      step counts, rankings by number of steps or ingredients
     "match"        - user lists ingredients they HAVE and wants recipes that use them
     "substitute"   - adapt a recipe: remove/replace an ingredient, make it X-free
     "unsupported"  - asks for info the dataset doesn't have (nutrition, calories, time, cost...)
     "reset"        - user ONLY wants to start over / clear everything, with no new request in the
                      same message ("Forget that. Find me a beef stew." is a "search" with new_search true)
     "help" | "chitchat",

  "constraints": {            // changes to the ACTIVE hard constraints. They persist across turns
                              // and apply to search, match and substitute until changed.
     "add_exclude": [],       // e.g. ["dairy"], ["peanuts"], ["eggs"], ["vegan"], ["gluten"], ["cilantro"]
     "remove_exclude": [],    // "actually I can have dairy" -> ["dairy"]
     "max_steps": null,       // integer if user sets a step limit
     "clear_max_steps": false
  },

  "search": {
     "query": "penne pasta" | null,   // null = keep the previous query (pure refinement)
     "add_include": [],               // ingredients that MUST be in the recipe
     "remove_include": [],
     "new_search": false              // true when the user starts a different search topic
  },

  "show": {"ref": "1" | "<recipe id>" | "<title words>" | "focus"},   // "focus" = the recipe being discussed

  "stats": {
     "metric": "count" | "top_ingredients" | "ingredient_count_stats" | "step_count_stats"
               | "rank_by_steps" | "rank_by_ingredients",
     "include": [],          // recipes must contain ALL of these ingredients
     "include_any": [],      // ... at least one of these
     "exclude": [],          // must contain none of these (diet words allowed: dairy, vegan, gluten...)
     "title_contains": [],   // dish words that must be in the title, e.g. ["cookie"]
     "max_steps": null, "source": null,   // source: "ar" | "epi" | "fn"
     "n": 5, "order": "asc" | "desc",     // rankings: asc = fewest first
     "group_by_source": false, "exclude_staples": false,
     "use_active_filters": false          // true only if the user refers to the current search ("how many of these...")
  },

  "match": {
     "have": null | ["eggs", "onions", ...],   // full list if the user states one; null = keep previous
     "add_have": [], "remove_have": [],
     "prefer": "max_used" | "fewest_missing" | "fewest_steps",
     "max_missing": null,            // "at most N extra ingredients"
     "must_use_all": false,          // true if the recipe has to use ALL of the user's ingredients
     "n": 5,
     "new_request": false
  },

  "substitute": {
     "recipe_ref": "focus" | "1" | "<recipe id>" | "<title words e.g. banana bread>",
     "remove": "eggs",                // the ingredient (or diet word like "dairy") to take out
     "restrictions": [],              // extra rules for the replacement, e.g. ["dairy"] for "without dairy"
     "dataset_only": false            // true if user says use only ingredients from the dataset
  },

  "unsupported": {"missing": "calories / nutrition"},
  "reply": "only for help/chitchat: one or two friendly sentences"
}

Rules:
- "I have X, Y and Z" / "I've got ..." / "what can I make with ..." is ALWAYS intent "match" (never
  "search"), with "have" = the listed ingredients and new_request true. If the user says the recipe
  must use all / all three / every one of them, set must_use_all true.
- If the last intent was "match" and the user changes the ranking ("rank by fewest steps instead",
  "fewest missing first") or adds/removes a constraint, keep intent "match" and set "prefer" or the
  constraint. Do NOT switch to "stats".
- Diet words go into add_exclude EXACTLY as the user said them: "vegan", "vegetarian",
  "gluten-free", "dairy", "nuts", "halal". Never expand them yourself (the program knows that
  vegan also means no fish, shellfish and honey).
- Quantities inside "have" are kept as typed, e.g. "3 eggs", "2 cups rice".
- "Exclude X too" during a match conversation -> intent "match" with constraints.add_exclude [X].
- "I cannot have dairy" right after a search -> intent "search", query null, constraints.add_exclude ["dairy"].
- A question like "how many recipes contain garlic and onion" is stats/count with include ["garlic","onion"].
- "which five have the fewest steps among tomato recipes" -> stats rank_by_steps, include ["tomato"], n 5, order "asc".
- Use singular, plain ingredient words ("tomato", "egg", "heavy cream").
- Copy dish and ingredient words exactly as the user spelled them in "query" (only fix obvious user typos).
- If the user asks about time/calories/nutrition/servings/cost, use "unsupported".
"""


def route(message: str, state_summary: str) -> dict:
    user = f"CONVERSATION STATE:\n{state_summary}\n\nUSER MESSAGE:\n{message}"
    return chat_json(ROUTER_PROMPT, user)


REWRITE_PROMPT = """You adapt an existing recipe after an ingredient substitution has ALREADY been chosen
from evidence. Do not choose a different substitute. Keep every other ingredient line exactly as
written unless the user's restrictions force a change. Return JSON:
{
  "ingredients": ["full updated ingredient lines"],
  "instructions": ["step 1", "step 2", ...],
  "effects": ["likely effect on taste/texture/prep - phrased as a prediction"],
  "warnings": ["anything that might not work, e.g. the original step whips the cream and the substitute can't be whipped"]
}
Rules:
- Replace the target lines with the substitute, using the amount guidance.
- If other lines also violate the user's restrictions, replace them with a reasonable alternative
  that does NOT violate the restrictions and mention it in warnings; if you can't, leave them and say so.
- Edit only the steps that mention the replaced ingredient; keep the rest word-for-word.
- Never claim the result is allergen-free or medically safe.
"""


def rewrite_recipe(row, target_lines, substitute, amount, evidence, restrictions, other_violations=()) -> dict:
    ev = "\n".join(f"- {rid} ({title}): {line}" for rid, title, line in evidence) or "- none"
    user = (
        f"RECIPE: {row['title']} ({row['id']})\n"
        f"INGREDIENTS:\n" + "\n".join(f"- {x}" for x in row["ingredients"]) + "\n"
        f"INSTRUCTIONS:\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(row["steps"], 1)) + "\n\n"
        f"LINES TO REPLACE: {target_lines}\n"
        f"CHOSEN SUBSTITUTE: {substitute}\nAMOUNT GUIDANCE: {amount}\n"
        f"USER RESTRICTIONS: {restrictions or 'none'}\n"
        f"OTHER LINES THAT ALSO VIOLATE THE RESTRICTIONS: {list(other_violations) or 'none'}\n"
        f"HOW SIMILAR DATASET RECIPES USE THE SUBSTITUTE:\n{ev}\n"
    )
    out = chat_json(REWRITE_PROMPT, user, max_tokens=1800)
    if not isinstance(out.get("ingredients"), list) or not isinstance(out.get("instructions"), list):
        raise ValueError("rewrite JSON missing ingredients/instructions")
    out["instructions"] = [re.sub(r"^\s*(?:step\s*)?\d+[.):]\s*", "", str(s), flags=re.I)
                           for s in out["instructions"]]
    eff = list(out.get("effects") or [])
    eff += [f"⚠️ {w}" for w in (out.get("warnings") or [])]
    out["effects"] = eff
    return out


def one_shot_answer(question: str) -> str:
    return chat_text(
        "You are a helpful cooking assistant. Answer the question about the Recipe Box dataset "
        "(recipes scraped from Allrecipes, Epicurious and Food Network).",
        question,
    )
