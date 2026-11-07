"""Evidence-based ingredient substitution (Task 3).

Order of evidence, strongest first:

1. DIRECT  - recipes similar to this one (by title) that don't use the target
             ingredient but do use the candidate substitute. We cite their IDs
             and quote the exact ingredient line, so amounts come from real recipes.
2. INDIRECT - the candidate is used without the target ingredient somewhere in
             the dataset, but not in recipes that look like this dish.
3. GENERAL COOKING KNOWLEDGE - the role table below (e.g. "~1/4 cup applesauce
             per egg"). This is NOT from the dataset and is always labelled as such.

We never claim a swap is medically safe; we only check that the new ingredient
list doesn't trip the user's restriction filters, and say that clearly.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

import numpy as np

from .normalize import clean_line, line_categories, normalize_user_ingredient, resolve_restriction, term_regex
from .search import CATEGORY_LABELS, broad_mask, category_hits, line_matches_family, term_hits
from .store import RecipeStore

# --------------------------------------------------------------------------- #
# General cooking knowledge (labelled as such whenever it is shown)
# --------------------------------------------------------------------------- #
# target -> (role of the ingredient, [(candidate, search regex term, amount guidance, expected effect)])
SUB_TABLE: dict[str, tuple[str, list[tuple[str, str, str, str]]]] = {
    "egg": (
        "binding (holds the crumb together), some lift/structure, and moisture",
        [
            ("applesauce", "applesauce", "about 1/4 cup unsweetened applesauce per egg",
             "moister and a little denser, slightly less rise; flavour barely changes"),
            ("banana", "banana", "about 1/4 cup mashed ripe banana per egg",
             "denser, very moist crumb; adds banana flavour (fine in banana bread)"),
            ("yogurt", "yogurt", "about 1/4 cup plain yogurt per egg",
             "tender and moist with a slight tang"),
            ("buttermilk", "buttermilk", "about 1/4 cup buttermilk per egg",
             "tender crumb, mild tang, weaker binding"),
            ("ground flaxseed", "flax|flaxseed|flaxseeds", "1 tbsp ground flaxseed + 3 tbsp water per egg, rested 5 minutes",
             "binds well; slightly nutty, can be a little gummy"),
            ("silken tofu", "silken tofu", "about 1/4 cup blended silken tofu per egg",
             "moist and dense; neutral flavour"),
            ("extra baking powder", "baking powder", "about 1 tsp extra baking powder per egg removed (for lift only)",
             "helps rise but adds no binding - combine with one of the above"),
        ],
    ),
    "cream": (
        "richness (fat), body, and a smooth sauce that coats the food",
        [
            ("coconut milk", "coconut milk", "same volume of full-fat coconut milk",
             "similar richness and body; noticeable coconut flavour"),
            ("coconut cream", "coconut cream", "same volume of coconut cream",
             "very rich, thick; coconut flavour"),
            ("cashews (blended)", "cashew|cashews", "soak ~1/2 cup raw cashews, blend with ~3/4 cup water per cup of cream",
             "creamy and neutral; slightly nutty; needs a blender"),
            ("olive oil + pasta water", "olive oil", "a few tbsp olive oil emulsified with starchy pasta water",
             "lighter, glossy sauce rather than a creamy one"),
            ("broth thickened with cornstarch", "broth|stock", "same volume of broth + 1 tbsp cornstarch slurry per cup",
             "much lighter; savoury; less rich mouthfeel"),
            ("soy milk", "soy milk|soymilk", "same volume, thicken with a little cornstarch",
             "thinner and less rich unless reduced/thickened"),
            ("almond milk", "almond milk", "same volume, thicken with a little cornstarch",
             "thinner, slightly nutty"),
        ],
    ),
    "butter": (
        "fat for flavour, tenderness and browning",
        [
            ("olive oil", "olive oil", "about 3/4 the amount of butter",
             "fruitier flavour; less browning; fine for savoury dishes"),
            ("vegetable oil", "vegetable oil|canola oil", "about 3/4 the amount of butter",
             "neutral flavour; moister but less rich baked goods"),
            ("coconut oil", "coconut oil", "same amount (solid for baking)",
             "similar texture in baking; faint coconut flavour"),
            ("vegetable shortening", "shortening", "same amount",
             "tender/flaky but no butter flavour"),
        ],
    ),
    "milk": (
        "liquid/moisture and mild richness",
        [
            ("soy milk", "soy milk|soymilk", "same volume", "very close in most recipes"),
            ("almond milk", "almond milk", "same volume", "thinner, slightly nutty"),
            ("oat milk", "oat milk", "same volume", "close; slightly sweet"),
            ("coconut milk", "coconut milk", "same volume (or half coconut milk, half water)", "richer; coconut flavour"),
            ("water", "water", "same volume", "works for moisture but loses richness"),
        ],
    ),
    "sour cream": (
        "moisture, tang and tenderness",
        [
            ("yogurt", "yogurt", "same amount of plain/Greek yogurt", "very close; slightly tangier"),
            ("coconut cream", "coconut cream", "same amount + squeeze of lemon", "rich; coconut flavour"),
            ("cashews (blended)", "cashew|cashews", "blended soaked cashews + lemon juice", "creamy, neutral"),
        ],
    ),
    "cheese": (
        "salty/savoury flavour, meltiness and body",
        [
            ("nutritional yeast", "nutritional yeast", "2-3 tbsp per 1/2 cup grated cheese", "cheesy/umami flavour, no melt"),
            ("breadcrumbs (toasted)", "breadcrumb|bread crumbs|panko", "toasted, for topping", "crunch instead of melt"),
            ("avocado", "avocado", "sliced or mashed", "creaminess instead of cheese"),
        ],
    ),
    "flour": (
        "structure (gluten) or thickening",
        [
            ("almond flour", "almond flour", "not 1:1 - usually needs extra egg/binder", "denser, moister, nutty"),
            ("rice flour", "rice flour", "roughly 1:1 for thickening", "slightly gritty in baking"),
            ("cornstarch", "cornstarch", "half the amount, for thickening only", "glossier sauce"),
            ("oat flour", "oat flour", "about 1 1/3x by volume in baking", "denser, nutty"),
        ],
    ),
}

# map whatever the user calls the ingredient to a row of the table
TARGET_ALIASES = {
    "egg": "egg", "eggs": "egg", "egg yolk": "egg", "egg white": "egg",
    "heavy cream": "cream", "cream": "cream", "whipping cream": "cream", "half-and-half": "cream",
    "light cream": "cream", "double cream": "cream",
    "butter": "butter", "milk": "milk", "whole milk": "milk",
    "sour cream": "sour cream", "cheese": "cheese", "parmesan cheese": "cheese",
    "cheddar cheese": "cheese", "mozzarella cheese": "cheese", "flour": "flour",
}


@dataclass
class SubRequest:
    recipe_id: str
    remove: str
    restrictions: list[str] = field(default_factory=list)
    dataset_only: bool = False      # "use only ingredients that appear in the dataset"


@dataclass
class Candidate:
    name: str
    amount: str
    effect: str
    direct: list[tuple[str, str, str]] = field(default_factory=list)   # (id, title, line)
    n_direct: int = 0          # similar recipes WITHOUT the target that use this candidate
    rate_without: float = 0.0  # ... as a share of all similar recipes without the target
    rate_with: float = 0.0     # share of similar recipes WITH the target that use it anyway
    n_indirect: int = 0        # any recipe in the dataset without the target that uses it
    in_dataset: int = 0
    rejected: str | None = None
    contrast_ok: bool = True   # were there enough similar recipes WITH the target to compare against?

    @property
    def replaces(self) -> bool:
        """Is it noticeably MORE common when the target is absent? If it's just as
        common either way (olive oil in pasta), it's co-occurring, not substituting."""
        return self.rate_without > 1.2 * self.rate_with + 0.01

    @property
    def strength(self) -> str:
        # Without a "with target" group we can't tell substitution from co-occurrence,
        # so the best we'll ever call it is "limited".
        if self.n_direct >= 3 and self.replaces and self.contrast_ok:
            return "direct"
        if self.n_direct >= 1 and self.replaces:
            return "limited"
        if self.n_direct >= 1:
            return "co-occurs only"
        if self.n_indirect >= 1:
            return "indirect"
        return "none"

    @property
    def rank(self) -> int:
        return ["direct", "limited", "co-occurs only", "indirect", "none"].index(self.strength)


def _target_lines(store: RecipeStore, row, remove: str) -> tuple[list[str], list[str], str]:
    """Which lines of the recipe are we replacing? Returns (lines, categories, label)."""
    cats, term = resolve_restriction(remove)
    if cats and not term:
        hits = category_hits(row, cats)
        lines = sorted({ln for c in cats for ln in hits[c]}, key=row["ingredients"].index)
        return lines, cats, ", ".join(CATEGORY_LABELS.get(c, c) for c in cats)
    fam = normalize_user_ingredient(remove)
    # normalised-name match first ("heavy whipping cream" IS heavy cream), raw text as a fallback
    lines = [ln for ln in row["ingredients"] if line_matches_family(store, ln, fam)]
    lines = lines or term_hits(row, fam) or term_hits(row, remove)
    # "cream" should not catch "cream cheese"/"sour cream"/"ice cream" lines
    if fam in ("cream", "heavy cream"):
        lines = [ln for ln in lines if not any(x in ln.lower() for x in ("cream cheese", "sour cream", "ice cream", "cream of"))]
    return lines, [], fam


def _restricted_categories(restrictions: list[str]) -> tuple[set[str], set[str]]:
    cats, terms = set(), set()
    for r in restrictions:
        c, t = resolve_restriction(r)
        cats.update(c)
        if t:
            terms.add(t)
    return cats, terms


def _siblings(store: RecipeStore, pos: int, k: int = 400) -> np.ndarray:
    """The 'same kind of dish' neighbourhood: 60% title similarity + 40% ingredient similarity.

    Title alone fails on names like "Penne with Sausage and Cheesy Garlic Bread"
    (it pulls in garlic breads); ingredients alone pull in unrelated dishes that
    happen to share a pantry.
    """
    t = (store.title_mat @ store.title_mat[pos].T).toarray().ravel()
    i = (store.ing_mat @ store.ing_mat[pos].T).toarray().ravel()
    sims = 0.6 * t + 0.4 * i
    sims[pos] = -1
    order = np.argsort(-sims)[:k]
    return order[sims[order] > 0.25]


def suggest_substitutes(store: RecipeStore, req: SubRequest, rewriter=None) -> tuple[str, dict]:
    row = store.get(req.recipe_id)
    if row is None:
        return (f"I couldn't find a recipe with ID `{req.recipe_id}`. Search for it first, "
                f"or give me the exact ID.", {"ok": False})
    pos = store.pos[row["id"]]
    lines, target_cats, label = _target_lines(store, row, req.remove)
    if not lines:
        return (f"**{row['title']}** (`{row['id']}`) doesn't list any {label} in its ingredients, "
                f"so there's nothing to replace.\n\nIngredients: " + "; ".join(row["ingredients"]),
                {"ok": False, "reason": "target not in recipe"})

    restricted_cats, restricted_terms = _restricted_categories(req.restrictions)
    restricted_cats |= set(target_cats)

    # Other lines that ALSO break the user's restrictions (e.g. "no dairy" but the
    # recipe has half-and-half as well as cream). We must not quietly leave them in.
    other_violations = [ln for ln in row["ingredients"] if ln not in lines and
                        (_violation(ln, restricted_cats, restricted_terms))]

    # target masks: does a recipe contain the thing we're removing?
    if target_cats:
        has_target = np.zeros(len(store), dtype=bool)
        for c in target_cats:
            has_target |= store.category_mask.get(c, np.zeros(len(store), dtype=bool))
    elif store.names_for(label):
        # normalised names, so "coconut cream" doesn't count as cream
        has_target = store.mask_for(label)
    else:
        has_target = broad_mask(store, label)

    sib = _siblings(store, pos)
    sib_with = sib[has_target[sib]]
    sib_without = sib[~has_target[sib]]

    key = TARGET_ALIASES.get(label) or (target_cats and {"dairy": "cream", "egg": "egg"}.get(target_cats[0]))
    role, table = SUB_TABLE.get(key, ("unknown - not in my role table, so any role I give is a prediction", []))

    contrast_ok = len(sib_with) >= 3
    candidates: list[Candidate] = []
    for name, rx_term, amount, effect in table:
        cand = Candidate(name, amount, effect, contrast_ok=contrast_ok)
        bad = line_categories(clean_line(name)) & restricted_cats
        if any(term_regex(t).search(name) for t in restricted_terms):
            bad.add("your restriction")
        if bad:
            cand.rejected = "violates restriction: " + ", ".join(CATEGORY_LABELS.get(b, b) for b in bad)
            candidates.append(cand)
            continue
        rx = term_regex(rx_term) if "|" not in rx_term else re.compile(r"\b(?:" + rx_term + r")\b")
        uses = np.fromiter((bool(rx.search(t)) for t in store.ing_text), dtype=bool, count=len(store))
        cand.in_dataset = int(uses.sum())
        if req.dataset_only and cand.in_dataset == 0:
            cand.rejected = "never appears in the dataset"
            candidates.append(cand)
            continue
        direct = sib_without[uses[sib_without]]
        cand.n_direct = len(direct)
        cand.rate_without = len(direct) / max(len(sib_without), 1)
        cand.rate_with = int(uses[sib_with].sum()) / max(len(sib_with), 1)
        cand.n_indirect = int((uses & ~has_target).sum())
        for p in direct[:3]:
            r = store.row(int(p))
            ln = next((x for x in r["ingredients"] if rx.search(clean_line(x))), "")
            cand.direct.append((r["id"], r["title"], ln))
        candidates.append(cand)

    # data-driven: what do the "without" versions use more often than the "with" versions?
    discovered = _over_represented(store, sib_with, sib_without, set(row["names"]), restricted_cats)

    usable = [c for c in candidates if not c.rejected]
    usable.sort(key=lambda c: (c.rank, -c.n_direct, -c.n_indirect))
    best = usable[0] if usable and usable[0].strength != "none" else None
    weak = best is not None and best.strength not in ("direct", "limited")

    # ---------- write the answer ----------
    out = [f"### Adapting: {row['title']} (`{row['id']}`)",
           f"**Removing:** {label} — affected lines: " + "; ".join(f"'{ln}'" for ln in lines)]
    if req.restrictions:
        out.append("**Your restrictions:** " + ", ".join(req.restrictions))
    out.append(f"**Role of {label} in this dish** _(general cooking knowledge, not from the dataset)_: {role}")
    out.append("")
    out.append(f"**Dataset evidence.** I found {len(sib):,} recipes with similar titles. "
               f"{len(sib_with):,} of them use {label} and {len(sib_without):,} don't.")
    if len(sib_without) == 0:
        out.append(f"⚠️ None of the similar recipes do without {label}. Any evidence below is "
                   f"indirect (from other kinds of dishes).")
    elif not contrast_ok:
        out.append(f"⚠️ Only {len(sib_with)} similar recipe(s) use {label}, so I can't compare 'with' "
                   f"vs 'without'. That means I can't tell a real substitute from something that "
                   f"just appears in this kind of dish anyway. No candidate is rated higher than *limited*.")
    elif len(sib_without) < 0.1 * max(len(sib), 1):
        out.append(f"⚠️ Most similar recipes keep {label} ({len(sib_with)} vs {len(sib_without)}), "
                   f"so leaving it out is unusual for this dish. The evidence is thin.")
    out.append(f"\n| Substitute | Evidence | Similar recipes **without** {label} using it | "
               f"Similar recipes **with** {label} using it | Anywhere in dataset without {label} |"
               "\n|---|---|---:|---:|---:|")
    for c in sorted(candidates, key=lambda c: (c.rejected is not None, c.rank, -c.n_direct)):
        if c.rejected:
            out.append(f"| ~~{c.name}~~ | rejected: {c.rejected} | – | – | – |")
        else:
            out.append(f"| {c.name} | {c.strength} | {c.n_direct} ({100 * c.rate_without:.0f}%) | "
                       f"{100 * c.rate_with:.0f}% | {c.n_indirect:,} |")
    out.append("\n_How to read this: a substitute only counts as evidence if it is **more common** in the "
               f"similar recipes that skip {label} than in the ones that use it. If it's equally common "
               "either way it just co-occurs (e.g. olive oil in pasta) and doesn't tell us it replaces anything._")
    if discovered:
        out.append("\nOther ingredients that show up more often in the similar recipes *without* "
                   f"{label} (just a data signal, not necessarily a substitute): "
                   + ", ".join(f"{n} ({cnt} recipes)" for n, cnt in discovered))

    data = {"ok": True, "recipe_id": row["id"], "target_lines": lines,
            "siblings": len(sib), "siblings_without": len(sib_without),
            "candidates": [{"name": c.name, "strength": c.strength, "direct": c.n_direct,
                            "indirect": c.n_indirect, "rejected": c.rejected} for c in candidates]}

    if best is None:
        out.append(f"\n### I can't support a reliable adaptation\nNone of the candidate substitutes "
                   f"has any support in the dataset that also respects your restrictions, so I'd "
                   f"rather not invent one.")
        data["best"] = None
        return "\n".join(out), data

    out.append(f"\n### Suggested change: replace {label} with **{best.name}**")
    if best.strength == "limited":
        out.append("⚠️ Evidence is **limited**: only a few similar recipes do this.")
    elif weak:
        out.append(f"⚠️ **Weak evidence.** No candidate is clearly used *instead of* {label} in similar "
                   f"recipes ({best.name}: {best.strength}). Treat this as an untested suggestion "
                   f"based mostly on general cooking knowledge, not as a dataset-backed swap.")
    data["weak_evidence"] = weak
    if best.direct:
        out.append("Supporting recipes (similar dishes that do this):")
        for rid, title, ln in best.direct:
            out.append(f"- `{rid}` — {title}: uses _'{ln}'_")
    out.append(f"- Amount guidance _(general cooking knowledge)_: {best.amount}")
    runner_up = [c for c in usable if c is not best and c.strength in ("direct", "limited")][:2]
    if runner_up:
        out.append("- Also supported: " + "; ".join(f"{c.name} ({c.n_direct} similar recipes)" for c in runner_up))

    if other_violations:
        out.append("\n⚠️ **Other ingredients in this recipe also break your restrictions:** "
                   + "; ".join(f"'{ln}'" for ln in other_violations))

    rewrite = None
    if rewriter is not None:
        try:
            rewrite = rewriter(row=row, target_lines=lines, substitute=best.name, amount=best.amount,
                               evidence=best.direct, restrictions=req.restrictions,
                               other_violations=other_violations)
        except Exception as exc:  # network / quota problems shouldn't kill the answer
            out.append(f"\n_(LLM rewrite unavailable: {exc}; using the simple rule-based rewrite.)_")
            rewrite = None
    if rewrite:
        problem = _check_rewrite(rewrite.get("ingredients", []), restricted_cats, restricted_terms, label, target_cats)
        if problem:
            out.append(f"\n_The model's rewrite failed my safety check ({problem}), so I fell back to a simple rule-based rewrite._")
            rewrite = None
    if not rewrite:
        rewrite = _rule_based_rewrite(row, lines, best)

    # final, independent check of whatever we're about to show
    still_bad = [ln for ln in rewrite["ingredients"] if _violation(ln, restricted_cats, restricted_terms)
                 and "replaces:" not in ln]
    data["still_violating"] = still_bad

    out.append("\n**Updated ingredients**")
    out += [f"- {x}" for x in rewrite["ingredients"]]
    out.append("\n**Revised instructions**")
    out += [f"{i}. {x}" for i, x in enumerate(rewrite["instructions"], 1)]
    out.append("\n**What will probably change** _(prediction - not tested, and not stated in the dataset)_")
    effects = rewrite.get("effects") or [best.effect]
    out += [f"- {e}" for e in effects]
    if still_bad:
        out.append(f"\n🚫 **This adapted version still does NOT meet your restrictions.** These lines remain: "
                   + "; ".join(f"'{x}'" for x in still_bad)
                   + ". I only had evidence for replacing the " + label + ". Ask me to replace those too, "
                   "or pick a different recipe.")
    else:
        out.append("\n_Safety note: I checked the new ingredient list against my keyword lists for your "
                   "restrictions and found nothing, but that is not a medical guarantee. Always check "
                   "packaged ingredient labels for allergens._")
    data["best"] = best.name
    data["rewrite"] = rewrite
    return "\n".join(out), data


def _over_represented(store, sib_with, sib_without, own_names: set, restricted: set, top: int = 5):
    if len(sib_without) < 2:
        return []
    names = store.df["names"].to_numpy()
    cw = Counter(n for p in sib_with for n in set(names[p]))
    co = Counter(n for p in sib_without for n in set(names[p]))
    res = []
    for n, c in co.items():
        if c < 2 or n in own_names or n in {"salt", "water", "black pepper"}:
            continue
        if line_categories(n) & restricted:
            continue
        fw = cw.get(n, 0) / max(len(sib_with), 1)
        fo = c / len(sib_without)
        if fo >= 1.5 * fw + 0.05:
            res.append((fo - fw, n, c))
    res.sort(reverse=True)
    return [(n, c) for _, n, c in res[:top]]


def _violation(line: str, cats: set, terms: set) -> bool:
    cl = clean_line(line)
    return bool(line_categories(cl) & cats) or any(term_regex(t).search(cl) for t in terms)


def _check_rewrite(ingredients: list[str], cats: set, terms: set, label: str, target_cats) -> str | None:
    for ln in ingredients:
        cl = clean_line(ln)
        bad = line_categories(cl) & cats
        if bad:
            return f"'{ln}' looks like {', '.join(bad)}"
        for t in terms:
            if term_regex(t).search(cl):
                return f"'{ln}' mentions {t}"
        if not target_cats and term_regex(label).search(cl) and "omit" not in cl and "replac" not in cl:
            return f"'{ln}' still contains {label}"
    return None


def _rule_based_rewrite(row, lines: list[str], best: Candidate) -> dict:
    """Simple deterministic fallback: swap the lines, annotate the method."""
    ings = []
    swapped = False
    for ln in row["ingredients"]:
        if ln in lines:
            if not swapped:
                ings.append(f"{best.name} — {best.amount} (replaces: {'; '.join(lines)})")
                swapped = True
            continue
        ings.append(ln)
    # replace mentions of the removed ingredient in the method, e.g. "beaten eggs" -> "the applesauce"
    names = sorted({n for ln in lines for n in _line_names(ln)}, key=len, reverse=True)
    steps = []
    for s in row["steps"]:
        new = s
        for n in names:
            new = re.sub(r"\b(?:slightly |lightly |well )?(?:beaten |whisked )?" + re.escape(n) + r"(?:e?s)?\b",
                         f"{best.name} [swapped]", new, flags=re.IGNORECASE)
        steps.append(new)
    return {"ingredients": ings, "instructions": steps, "effects": [best.effect]}


def _line_names(line: str) -> list[str]:
    from .normalize import canonical_names

    out = []
    for n in canonical_names(line):
        out.append(n)
        out.append(n.split()[-1])  # "heavy cream" -> also "cream"
    return out
