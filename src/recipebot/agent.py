from __future__ import annotations

import difflib
import json
import re
from dataclasses import dataclass, field

from . import llm
from .analytics import StatsSpec, run_stats
from .data import SOURCE_NAMES
from .matching import MatchRequest, match_recipes
from .normalize import line_categories, clean_line, resolve_restriction
from .search import CATEGORY_LABELS, Filters, apply_filters, evidence_lines, find_by_title, search, term_hits
from .store import RecipeStore, load_store
from .substitution import SubRequest, suggest_substitutes

PAGE = 5


@dataclass
class SessionState:
    query: str = ""
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    max_steps: int | None = None
    last_results: list[str] = field(default_factory=list)
    offset: int = 0
    focus: str | None = None
    pantry: list[str] | None = None
    prefer: str = "max_used"
    max_missing: int | None = None
    must_use_all: bool = False
    last_intent: str = ""
    turns: list[tuple[str, str]] = field(default_factory=list)

    def summary(self, store: RecipeStore) -> str:
        lines = [
            f"last intent: {self.last_intent or 'none'}",
            f"active search query: {self.query or 'none'}",
            f"must include: {self.include or 'none'}",
            f"active restrictions (exclude): {self.exclude or 'none'}",
            f"max steps: {self.max_steps if self.max_steps is not None else 'none'}",
            f"pantry for matching: {self.pantry or 'none'} (prefer={self.prefer})",
        ]
        if self.focus:
            r = store.get(self.focus)
            lines.append(f"recipe in focus: {self.focus} - {r['title'] if r is not None else '?'}")
        if self.last_results:
            shown = []
            for i, rid in enumerate(self.last_results[:10], 1):
                r = store.get(rid)
                shown.append(f"  {i}. {rid} - {r['title'] if r is not None else '?'}")
            lines.append("last results shown:\n" + "\n".join(shown))
        if self.turns:
            lines.append("recent turns:\n" + "\n".join(f"  user: {u}\n  bot: {b}" for u, b in self.turns[-4:]))
        return "\n".join(lines)


@dataclass
class Reply:
    markdown: str
    trace: dict


class RecipeBot:
    def __init__(self, store: RecipeStore | None = None, router=None, rewriter=None):
        self.store = store or load_store()
        self.router = router or llm.route
        self.rewriter = rewriter if rewriter is not None else llm.rewrite_recipe
        self.state = SessionState()

    def handle(self, message: str) -> Reply:
        message = (message or "").strip()
        if not message:
            return Reply("Ask me about recipes - e.g. *find a penne pasta recipe*.", {})
        try:
            self._message = message
            plan = self.router(message, self.state.summary(self.store))
        except llm.LLMUnavailable as exc:
            return Reply(f"⚠️ {exc}", {"error": str(exc)})
        except Exception as exc:
            return Reply(f"⚠️ I couldn't reach the language model ({type(exc).__name__}: {exc}). "
                         f"Please try again in a moment.", {"error": str(exc)})

        intent = (plan.get("intent") or "chitchat").lower()
        self._apply_constraints(plan.get("constraints") or {})
        handler = {
            "search": self._search, "more": self._more, "show_recipe": self._show,
            "stats": self._stats, "match": self._match, "substitute": self._substitute,
            "unsupported": self._unsupported, "reset": self._reset, "help": self._help,
        }.get(intent, self._chitchat)
        try:
            md = handler(plan)
        except Exception as exc:
            md = f"⚠️ Something went wrong while running `{intent}`: {exc}"
        self.state.last_intent = intent
        self.state.turns.append((message, md.split("\n", 1)[0][:160]))
        return Reply(md, {"plan": plan, "intent": intent, "state": self._state_dict()})

    def _apply_constraints(self, c: dict) -> None:
        s = self.state
        for x in c.get("remove_exclude") or []:
            s.exclude = [e for e in s.exclude if e.lower() != str(x).lower()]
        for x in c.get("add_exclude") or []:
            if str(x).lower() not in [e.lower() for e in s.exclude]:
                s.exclude.append(str(x))
        if c.get("clear_max_steps"):
            s.max_steps = None
        if c.get("max_steps") not in (None, ""):
            try:
                s.max_steps = int(c["max_steps"])
            except (TypeError, ValueError):
                pass

    def _state_dict(self) -> dict:
        s = self.state
        return {"query": s.query, "include": s.include, "exclude": s.exclude, "max_steps": s.max_steps,
                "pantry": s.pantry, "focus": s.focus, "last_results": s.last_results[:5]}

    def _filters(self) -> Filters:
        return Filters(include=list(self.state.include), exclude=list(self.state.exclude),
                       max_steps=self.state.max_steps)

    def constraints_line(self) -> str:
        s = self.state
        parts = []
        if s.include:
            parts.append("must include " + ", ".join(s.include))
        if s.exclude:
            parts.append("excluding " + ", ".join(s.exclude))
        if s.max_steps is not None:
            parts.append(f"≤ {s.max_steps} steps")
        return "; ".join(parts) if parts else "none"

    def _search(self, plan: dict) -> str:
        p = plan.get("search") or {}
        s = self.state
        if p.get("new_search"):
            s.query, s.include = "", []
        if p.get("query"):
            s.query = self._fix_typos(str(p["query"]))
        for x in p.get("remove_include") or []:
            s.include = [i for i in s.include if i.lower() != str(x).lower()]
        for x in p.get("add_include") or []:
            if x not in s.include:
                s.include.append(str(x))
        if not s.query and not s.include:
            return "What would you like to search for? A dish name, an ingredient, or a description works."
        s.offset = 0
        return self._run_search()

    def _fix_typos(self, query: str) -> str:
        said = re.findall(r"[a-z]+", getattr(self, "_message", "").lower())
        fixed = []
        for w in query.split():
            if w.lower() not in said:
                close = difflib.get_close_matches(w.lower(), said, n=1, cutoff=0.8)
                if close:
                    w = close[0]
            fixed.append(w)
        return " ".join(fixed)

    def _more(self, plan: dict) -> str:
        if not (self.state.query or self.state.include):
            return "There's no active search yet - tell me what you're looking for."
        self.state.offset += PAGE
        return self._run_search()

    def _run_search(self) -> str:
        s, st = self.state, self.store
        res = search(st, s.query, self._filters(), k=s.offset + PAGE)
        hits = res.hits[s.offset:]
        out = [f"**Search:** {s.query or '(by ingredients)'} · **Filters:** {self.constraints_line()}"]
        if not hits:
            if s.offset and res.hits:
                return out[0] + "\n\nThat's all the matching results."
            out.append(self._explain_no_match(res))
            s.last_results = []
            return "\n\n".join(out)
        info = res.filter_info
        if hits[0].coverage < 1.0:
            out.append(f"**No recipe matches everything in '{s.query}'** while meeting your constraints. "
                       f"The results below are only *partial* matches (each one is missing some of "
                       f"the words you asked for) — shown so you can decide, not as an answer.\n")
        else:
            out.append(f"{res.n_eligible:,} recipes pass every constraint and share words with the query. "
                       f"Showing {s.offset + 1}–{s.offset + len(hits)}:\n")
        for i, h in enumerate(hits, s.offset + 1):
            r = st.row(h.pos)
            partial = f" · ⚠️ partial match ({h.coverage:.0%} of query words)" if h.coverage < 1.0 else ""
            out.append("")
            out.append(f"**{i}. {r['title']}** — `{r['id']}` · {SOURCE_NAMES[r['source']]} · "
                       f"{_n(r['n_steps'], 'step')} · {_n(r['n_ingredients'], 'ingredient')}{partial}")
            ev = evidence_lines(st, r, info.include_families)
            for fam, lines in ev.items():
                if lines:
                    out.append(f"- contains {fam}: _{lines[0]}_")
            if info.exclude_categories or info.exclude_terms:
                checked = ", ".join([CATEGORY_LABELS.get(c, c) for c in info.exclude_categories] + info.exclude_terms)
                out.append(f"- no {checked} found in its {len(r['ingredients'])} ingredient lines: "
                           f"_{'; '.join(r['ingredients'])}_")
        s.last_results = [st.ids[h.pos] for h in res.hits]
        s.focus = s.last_results[0]
        out.append("\nSay *show 2* for the full recipe, *more* for more results, or add a restriction.")
        return "\n".join(out)

    def _explain_no_match(self, res) -> str:
        st, s = self.store, self.state
        lines = ["**No recipes match all of your constraints.** I did not relax any of them."]
        base = Filters(include=list(s.include))
        for ex in s.exclude:
            f = Filters(include=list(s.include), exclude=[e for e in s.exclude if e != ex], max_steps=s.max_steps)
            n = search(st, s.query, f, k=1).n_eligible
            if n:
                lines.append(f"- Without the *{ex}* restriction there would be {n:,} matches.")
        if s.max_steps is not None:
            f = Filters(include=list(s.include), exclude=list(s.exclude))
            n = search(st, s.query, f, k=1).n_eligible
            if n:
                lines.append(f"- Without the *≤ {s.max_steps} steps* limit there would be {n:,} matches.")
        if search(st, s.query, base, k=1).n_eligible == 0:
            what = f"'{s.query}'" if s.query else "a recipe containing all of: " + ", ".join(s.include)
            lines.append(f"- Even with no restrictions, nothing in the dataset matches {what}.")
        lines.append("Tell me if you'd like to change a constraint.")
        return "\n".join(lines)

    def _resolve(self, ref) -> tuple[str | None, str]:
        s, st = self.state, self.store
        ref = str(ref or "").strip()
        if not ref or ref.lower() in ("focus", "this", "that", "it", "this recipe", "that recipe"):
            if s.focus:
                return s.focus, ""
            if s.last_results:
                return s.last_results[0], ""
            return None, "There's no recipe in the conversation yet."
        m = re.fullmatch(r"#?(\d{1,2})", ref)
        if m:
            k = int(m.group(1))
            if 1 <= k <= len(s.last_results):
                return s.last_results[k - 1], ""
            return None, f"I only showed {len(s.last_results)} results, so there's no #{k}."
        r = st.get(ref.strip("`"))
        if r is not None:
            return r["id"], ""
        for rid in s.last_results:
            if ref.lower() in st.get(rid)["title"].lower():
                return rid, ""
        cands = find_by_title(st, ref, k=1)
        if cands:
            rid = st.ids[cands[0]]
            return rid, (f"_I used **{st.row(cands[0])['title']}** (`{rid}`), the closest title match for "
                         f"'{ref}'. Give me an ID if you meant a different one._\n\n")
        return None, f"I couldn't find a recipe matching '{ref}'."

    def _show(self, plan: dict) -> str:
        rid, note = self._resolve((plan.get("show") or {}).get("ref"))
        if rid is None:
            return note
        self.state.focus = rid
        return note + self.render_recipe(rid)

    def render_recipe(self, rid: str) -> str:
        r = self.store.get(rid)
        out = [f"### {r['title']}", f"`{r['id']}` · {SOURCE_NAMES[r['source']]} · {r['n_ingredients']} ingredients · {r['n_steps']} steps",
               "\n**Ingredients** (as in the dataset)"]
        out += [f"- {x}" for x in r["ingredients"]]
        out.append("\n**Instructions** (as in the dataset)")
        out += [f"{i}. {x}" for i, x in enumerate(r["steps"], 1)]
        warn = []
        for ex in self.state.exclude:
            cats, term = resolve_restriction(ex)
            for ln in r["ingredients"]:
                cl = clean_line(ln)
                if (set(cats) & line_categories(cl)) or (term and term_hits({"ingredients": [ln]}, term)):
                    warn.append(f"'{ln}' ({ex})")
        if warn:
            out.append("\n⚠️ Heads-up: this recipe conflicts with your active restrictions: " + "; ".join(warn))
        out.append("\n_The dataset has no nutrition, servings or total cooking time for recipes._")
        return "\n".join(out)

    def _stats(self, plan: dict) -> str:
        p = plan.get("stats") or {}
        f = Filters(
            include=list(p.get("include") or []), include_any=list(p.get("include_any") or []),
            exclude=list(p.get("exclude") or []), title_contains=list(p.get("title_contains") or []),
            max_steps=p.get("max_steps"), source=p.get("source"),
        )
        if p.get("use_active_filters"):
            f.include += [i for i in self.state.include if i not in f.include]
            f.exclude += [e for e in self.state.exclude if e not in f.exclude]
            if self.state.max_steps is not None and f.max_steps is None:
                f.max_steps = self.state.max_steps
            if self.state.query and not f.title_contains:
                f.title_contains = [w for w in self.state.query.split() if len(w) > 3][:2]
        spec = StatsSpec(
            metric=p.get("metric") or "count", filters=f, n=int(p.get("n") or 5),
            order=p.get("order") or "asc", group_by_source=bool(p.get("group_by_source")),
            exclude_staples=bool(p.get("exclude_staples")),
        )
        ans = run_stats(self.store, spec)
        if spec.metric in ("rank_by_steps", "rank_by_ingredients") and ans.data.get("ranking"):
            self.state.last_results = [x["id"] for x in ans.data["ranking"]]
        return ans.markdown

    def _match(self, plan: dict) -> str:
        p = plan.get("match") or {}
        s = self.state
        if p.get("new_request"):
            s.pantry, s.prefer, s.max_missing, s.must_use_all = None, "max_used", None, False
        if p.get("have"):
            s.pantry = [str(x) for x in p["have"]]
        if s.pantry is None:
            s.pantry = []
        for x in p.get("remove_have") or []:
            s.pantry = [h for h in s.pantry if str(x).lower() not in h.lower()]
        for x in p.get("add_have") or []:
            s.pantry.append(str(x))
        if p.get("prefer"):
            s.prefer = p["prefer"]
        if p.get("max_missing") is not None:
            s.max_missing = int(p["max_missing"])
        if p.get("must_use_all") is not None:
            s.must_use_all = bool(p["must_use_all"])
        if not s.pantry:
            return "Tell me which ingredients you have, e.g. *I have eggs, onions, tomatoes and rice*."
        req = MatchRequest(have=s.pantry, exclude=list(s.exclude), max_steps=s.max_steps,
                           max_missing=s.max_missing, must_use_all=s.must_use_all,
                           prefer=s.prefer, n=int(p.get("n") or 5))
        md, data = match_recipes(self.store, req)
        ids = [r["id"] for r in data.get("results", [])]
        if ids:
            s.last_results, s.focus = ids, ids[0]
        return md

    def _substitute(self, plan: dict) -> str:
        p = plan.get("substitute") or {}
        rid, note = self._resolve(p.get("recipe_ref") or "focus")
        if rid is None:
            return note + " Search for the recipe first, or give me its ID."
        remove = p.get("remove")
        if not remove:
            return "Which ingredient should I replace?"
        restrictions = list(dict.fromkeys(list(p.get("restrictions") or []) + self.state.exclude))
        self.state.focus = rid
        md, _ = suggest_substitutes(
            self.store,
            SubRequest(recipe_id=rid, remove=str(remove), restrictions=restrictions,
                       dataset_only=bool(p.get("dataset_only"))),
            rewriter=self.rewriter,
        )
        return note + md

    def _unsupported(self, plan: dict) -> str:
        missing = (plan.get("unsupported") or {}).get("missing") or "that information"
        out = [f"The Recipe Box dataset doesn't contain **{missing}** — each recipe only has a title, "
               f"an ingredient list and instructions. I'd rather say that than make up a number."]
        if re.search(r"time|long|minute|hour|duration", missing, re.I) and self.state.focus:
            r = self.store.get(self.state.focus)
            rx = re.compile(r"\b\d+(?:\s*(?:to|-|–)\s*\d+)?\s*(?:minutes?|mins?|hours?|hrs?)\b", re.I)
            found = [(i, m.group(0)) for i, st in enumerate(r["steps"], 1) for m in rx.finditer(st)]
            if found:
                out.append(f"\nWhat I *can* tell you: the instructions of **{r['title']}** mention these "
                           "durations (they're individual steps, not a verified total time):")
                out += [f"- step {i}: {t}" for i, t in found]
        return "\n".join(out)

    def _reset(self, plan: dict) -> str:
        self.state = SessionState()
        return "Okay, starting fresh — all searches and restrictions cleared."

    def _help(self, plan: dict) -> str:
        return HELP_TEXT

    def _chitchat(self, plan: dict) -> str:
        return plan.get("reply") or HELP_TEXT


HELP_TEXT = """I can help with the ~123k recipes in the Recipe Box dataset:

- **Search** - *find a penne pasta recipe*, then refine: *I can't have dairy*, *show 2*
- **Statistics** - *how many recipes contain garlic and onion?*, *which 5 tomato recipes have the fewest steps?*
- **Use what you have** - *I have eggs, onions, tomatoes and rice; no peanuts; max 6 steps*, then *exclude eggs too*
- **Substitutions** - *remove the eggs from this banana bread*, *replace the cream without dairy*

Everything I say about recipes comes from the dataset, with recipe IDs. The dataset has no nutrition or cooking-time data, so I won't invent those."""


def _n(k: int, word: str) -> str:
    return f"{k} {word}" + ("" if k == 1 else "s")


def plan_to_json(plan: dict) -> str:
    return json.dumps(plan, indent=2, ensure_ascii=False)
