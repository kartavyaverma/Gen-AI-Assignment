"""Statistics over the dataset (Task 1, analytical questions).

Rule of the house: the LLM never produces a number. It only turns the question
into a structured spec (metric + filters); everything below is plain pandas /
numpy over the *complete* filtered set, and each answer says
  - which filters were applied,
  - how many recipes were analysed (and out of how many),
  - exactly how the number was calculated.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

import numpy as np

from .data import SOURCE_NAMES
from .search import Filters, apply_filters, broad_mask
from .store import RecipeStore

STEP_RULE = ("a step = one non-empty line of the original instructions, ignoring boilerplate "
             "like 'Watch how to make this recipe.' and exact duplicate lines")
INGREDIENT_RULE = ("ingredient count = number of distinct ingredient lines, ignoring section "
                   "headers ('For the sauce:') and the scraper's 'ADVERTISEMENT' artefacts")
STAPLES = {"salt", "black pepper", "water"}

METRICS = [
    "count",                 # how many recipes match (+ % of dataset)
    "top_ingredients",       # most common ingredients among matches
    "ingredient_count_stats",
    "step_count_stats",
    "rank_by_steps",         # fewest/most steps
    "rank_by_ingredients",   # fewest/most ingredients
]


@dataclass
class StatsSpec:
    metric: str
    filters: Filters = field(default_factory=Filters)
    n: int = 5
    order: str = "asc"                 # for rankings: asc = fewest first
    group_by_source: bool = False
    exclude_staples: bool = False      # for top_ingredients


@dataclass
class StatsAnswer:
    markdown: str
    data: dict


def _header(store: RecipeStore, desc: list[str], n: int) -> list[str]:
    total = len(store)
    lines = ["**How this was computed**"]
    lines.append(f"- Dataset: {total:,} complete recipes (all three source files; "
                 f"{store.report.get('dropped_incomplete', 0):,} empty/incomplete records excluded).")
    lines.append("- Filters: " + ("; ".join(desc) if desc else "none (whole dataset)"))
    lines.append(f"- Recipes analysed: **{n:,}**")
    return lines


def _norm_note(families: list[str]) -> str:
    if not families:
        return ""
    return ("- Ingredient matching: lines are normalised (quantities, units and prep words "
            "removed, plurals singularised, varieties merged - e.g. red/yellow onion → onion, "
            "egg yolk → egg). Different products stay separate: *garlic powder* is not *garlic*, "
            "*green onion* is not *onion*.")


def run_stats(store: RecipeStore, spec: StatsSpec) -> StatsAnswer:
    if spec.metric not in METRICS:
        return StatsAnswer(f"I can't compute '{spec.metric}'. Supported: {', '.join(METRICS)}.", {})
    info = apply_filters(store, spec.filters)
    mask = info.mask
    n = int(mask.sum())
    lines: list[str] = []
    data: dict = {"metric": spec.metric, "n_analysed": n, "filters": spec.filters.to_dict()}

    if spec.metric == "count":
        total = len(store)
        pct = 100 * n / total
        lines.append(f"**{n:,} recipes** match — that is **{pct:.2f}%** of the {total:,} recipes in the dataset.")
        data.update(count=n, percent=round(pct, 4), denominator=total)
        # transparency: what a looser "any line mentions the word" match would give
        if info.include_families and not spec.filters.include_any:
            loose = np.ones(len(store), dtype=bool)
            for fam in info.include_families:
                loose &= broad_mask(store, fam)
            # keep the other (non-include) filters identical
            other = apply_filters(store, Filters(**{**spec.filters.__dict__, "include": []})).mask
            loose &= other
            ln = int(loose.sum())
            data["broad_count"] = ln
            lines.append(
                f"\nFor comparison, a looser rule — *any ingredient line that mentions the word*, which "
                f"also counts things like garlic powder, onion soup mix or green onions — gives "
                f"{ln:,} recipes ({100 * ln / total:.2f}%). I report the stricter number as the answer "
                f"because a recipe using only garlic powder doesn't really 'contain garlic'.")
        if spec.group_by_source:
            lines.append("\n| Source | Matching | Source total | % of source |\n|---|---:|---:|---:|")
            src = store.df["source"].to_numpy()
            for s, name in SOURCE_NAMES.items():
                tot = int((src == s).sum())
                m = int((mask & (src == s)).sum())
                lines.append(f"| {name} | {m:,} | {tot:,} | {100 * m / tot:.2f}% |")
        calc = f"- Calculation: count of recipes passing all filters ÷ {total:,} × 100."

    elif spec.metric == "top_ingredients":
        if n == 0:
            return StatsAnswer(_no_match(store, info.description), data)
        counter: Counter = Counter()
        for fams in store.df["families"].to_numpy()[mask]:
            counter.update(set(fams))
        if spec.exclude_staples:
            for s in STAPLES:
                counter.pop(s, None)
        for fam in info.include_families:   # obviously every match contains these
            counter.pop(fam, None)
        top = counter.most_common(spec.n)
        lines.append(f"Most common ingredients across the {n:,} matching recipes:\n")
        lines.append("| # | Ingredient | Recipes | % of matches |\n|---|---|---:|---:|")
        for i, (name, c) in enumerate(top, 1):
            lines.append(f"| {i} | {name} | {c:,} | {100 * c / n:.1f}% |")
        data["top"] = top
        calc = ("- Calculation: for each recipe, the *set* of normalised ingredient names (so a recipe "
                "using butter twice counts once); counted across all matching recipes."
                + (" Salt, pepper and water hidden." if spec.exclude_staples else "")
                + (" The filter ingredients themselves are left out of the table." if info.include_families else ""))

    elif spec.metric in ("ingredient_count_stats", "step_count_stats"):
        if n == 0:
            return StatsAnswer(_no_match(store, info.description), data)
        vals = (store.n_ingredients if spec.metric == "ingredient_count_stats" else store.n_steps)[mask]
        what = "ingredients" if spec.metric == "ingredient_count_stats" else "instruction steps"
        stats = {
            "mean": float(np.mean(vals)), "median": float(np.median(vals)),
            "min": int(vals.min()), "max": int(vals.max()), "std": float(np.std(vals)),
        }
        lines.append(f"Number of {what} per recipe across {n:,} recipes:\n")
        lines.append("| Mean | Median | Min | Max | Std dev |\n|---:|---:|---:|---:|---:|")
        lines.append(f"| {stats['mean']:.2f} | {stats['median']:.1f} | {stats['min']} | {stats['max']} | {stats['std']:.2f} |")
        if spec.group_by_source:
            lines.append("\n| Source | Recipes | Mean | Median |\n|---|---:|---:|---:|")
            src = store.df["source"].to_numpy()[mask]
            for s, name in SOURCE_NAMES.items():
                v = vals[src == s]
                if len(v):
                    lines.append(f"| {name} | {len(v):,} | {np.mean(v):.2f} | {np.median(v):.1f} |")
        data["stats"] = stats
        rule = INGREDIENT_RULE if spec.metric == "ingredient_count_stats" else STEP_RULE
        calc = f"- Calculation: numpy mean/median/min/max/std over all {n:,} values. Rule: {rule}."

    else:  # rankings
        if n == 0:
            return StatsAnswer(_no_match(store, info.description), data)
        key = store.n_steps if spec.metric == "rank_by_steps" else store.n_ingredients
        tiebreak = store.n_ingredients if spec.metric == "rank_by_steps" else store.n_steps
        cand = np.flatnonzero(mask)
        sign = 1 if spec.order == "asc" else -1
        # sort by key, then by the other count, then by id -> fully reproducible
        order = sorted(cand, key=lambda p: (sign * key[p], sign * tiebreak[p], store.ids[p]))
        top = order[: spec.n]
        what = "steps" if spec.metric == "rank_by_steps" else "ingredients"
        other = "ingredients" if what == "steps" else "steps"
        word = "fewest" if spec.order == "asc" else "most"
        lines.append(f"The {len(top)} matching recipes with the **{word} {what}**:\n")
        lines.append(f"| # | Recipe | ID | {what.title()} | {other.title()} |\n|---|---|---|---:|---:|")
        rows = []
        for i, p in enumerate(top, 1):
            r = store.row(p)
            lines.append(f"| {i} | {r['title']} | `{r['id']}` | {key[p]} | {tiebreak[p]} |")
            rows.append({"id": r["id"], "title": r["title"], what: int(key[p]), other: int(tiebreak[p])})
        cutoff = key[top[-1]]
        tied = int((key[cand] == cutoff).sum())
        if tied > 1:
            unit = what[:-1] if cutoff == 1 else what
            lines.append(f"\nNote: {tied:,} matching recipes have exactly {cutoff} {unit}, so the "
                         f"order among ties is decided by {other} ({word} first) and then by ID.")
        data["ranking"] = rows
        rule = STEP_RULE if what == "steps" else INGREDIENT_RULE
        calc = f"- Calculation: sorted all {n:,} matches by {what} ({'ascending' if sign == 1 else 'descending'}). Rule: {rule}."

    lines.append("")
    lines += _header(store, info.description, n)
    note = _norm_note(info.include_families)
    if note:
        lines.append(note)
    lines.append(calc)
    return StatsAnswer("\n".join(lines), data)


def _no_match(store: RecipeStore, desc: list[str]) -> str:
    return ("**No recipes match these filters**, so there is nothing to compute.\n\n"
            "- Filters: " + "; ".join(desc) + f"\n- Searched all {len(store):,} recipes.")
