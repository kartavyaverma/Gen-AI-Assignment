from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .normalize import (
    clean_line,
    compare_quantity,
    line_categories,
    normalize_user_ingredient,
    parse_quantity,
    resolve_restriction,
    term_regex,
)
from .search import CATEGORY_LABELS, Filters, apply_filters, category_hits, line_matches_family, term_hits
from .store import RecipeStore

STAPLES = {"salt", "black pepper", "water"}

SORT_MODES = {
    "max_used": "most of your ingredients used → fewest extra ingredients → fewest steps",
    "fewest_missing": "fewest extra ingredients → most of your ingredients used → fewest steps",
    "fewest_steps": "fewest steps → most of your ingredients used → fewest extra ingredients",
}


@dataclass
class MatchRequest:
    have: list[str]
    exclude: list[str] = field(default_factory=list)
    max_steps: int | None = None
    max_missing: int | None = None
    must_use_all: bool = False
    prefer: str = "max_used"
    n: int = 5


@dataclass
class PantryItem:
    raw: str
    family: str
    names: set[str]
    qty: tuple


@dataclass
class Match:
    pos: int
    used: list[PantryItem]
    missing: list[str]
    unused: list[PantryItem]
    n_steps: int
    key: tuple
    qty_notes: list[str]


def _pantry(store: RecipeStore, have: list[str]) -> list[PantryItem]:
    items, seen = [], set()
    for raw in have:
        fam = normalize_user_ingredient(raw)
        if not fam or fam in seen:
            continue
        seen.add(fam)
        names = set(store.names_for(fam)) or {fam}
        items.append(PantryItem(raw, fam, names, parse_quantity(raw)))
    return items


def _sort_key(prefer: str, used: int, missing: int, steps: int, rid: str) -> tuple:
    if prefer == "fewest_missing":
        return (missing, -used, steps, rid)
    if prefer == "fewest_steps":
        return (steps, -used, missing, rid)
    return (-used, missing, steps, rid)


def _quantity_notes(store: RecipeStore, row, item: PantryItem) -> list[str]:
    if item.qty[0] is None:
        return []
    lines = [ln for ln in row["ingredients"] if line_matches_family(store, ln, item.family)]
    if not lines:
        return [f"{item.family}: quantity not verified (couldn't find the matching line)"]
    need = parse_quantity(lines[0])
    if "cooked" in lines[0].lower() and "cooked" not in item.raw.lower():
        return [f"{item.family}: recipe asks for '{lines[0]}' (cooked) and you gave a raw amount — "
                f"not comparable, so quantity sufficiency was NOT verified"]
    verdict = compare_quantity(item.qty, need)
    if verdict is None:
        return [f"{item.family}: you have '{item.raw}', recipe says '{lines[0]}' — units not "
                f"comparable, so quantity sufficiency was NOT verified"]
    return [f"{item.family}: you have '{item.raw}', recipe needs '{lines[0]}' → **{verdict}**"]


def _rank(store: RecipeStore, mask: np.ndarray, pantry: list[PantryItem], prefer: str,
          max_missing: int | None, must_use_all: bool = False) -> list[Match]:
    uses_any = np.zeros(len(store), dtype=bool)
    for it in pantry:
        uses_any |= store.mask_for(it.family) if store.names_for(it.family) else False
    cand = np.flatnonzero(mask & uses_any)
    all_pantry_names = set().union(*(it.names for it in pantry)) if pantry else set()

    names_col = store.df["names"].to_numpy()
    results = []
    for p in cand:
        rnames = names_col[p]
        rset = set(rnames)
        used = [it for it in pantry if rset & it.names]
        missing = [n for n in rnames if n not in all_pantry_names and n not in STAPLES]
        if max_missing is not None and len(missing) > max_missing:
            continue
        if must_use_all and len(used) < len(pantry):
            continue
        unused = [it for it in pantry if it not in used]
        steps = int(store.n_steps[p])
        key = _sort_key(prefer, len(used), len(missing), steps, store.ids[p])
        results.append(Match(int(p), used, missing, unused, steps, key, []))
    results.sort(key=lambda m: m.key)
    return results


def _why(prev: Match | None, cur: Match, prefer: str, n_pantry: int) -> str:
    base = (f"uses {len(cur.used)}/{n_pantry} of your ingredients, needs {len(cur.missing)} "
            f"extra, {cur.n_steps} step{'s' if cur.n_steps != 1 else ''}")
    if prev is None:
        return f"Top match: {base}."
    labels = {
        "max_used": ["uses fewer of your ingredients", "needs more extra ingredients", "has more steps", "tied on everything; ordered by ID"],
        "fewest_missing": ["needs more extra ingredients", "uses fewer of your ingredients", "has more steps", "tied on everything; ordered by ID"],
        "fewest_steps": ["has more steps", "uses fewer of your ingredients", "needs more extra ingredients", "tied on everything; ordered by ID"],
    }[prefer]
    for i, (a, b) in enumerate(zip(prev.key, cur.key)):
        if a != b:
            return f"{base} — below the previous one because it {labels[i]}" if i < 3 else f"{base} — {labels[3]}"
    return base


def match_recipes(store: RecipeStore, req: MatchRequest) -> tuple[str, dict]:
    prefer = req.prefer if req.prefer in SORT_MODES else "max_used"
    notes: list[str] = []

    ex_cats, ex_terms = [], []
    for w in req.exclude:
        c, t = resolve_restriction(w)
        ex_cats += c
        if t:
            ex_terms.append(t)
    have = []
    for h in req.have:
        cl = clean_line(h)
        hit_cats = line_categories(cl) & set(ex_cats)
        hit_terms = [t for t in ex_terms if term_regex(t).search(cl)]
        if hit_cats or hit_terms:
            why = ", ".join([CATEGORY_LABELS.get(c, c) for c in hit_cats] + hit_terms)
            notes.append(f"'{h}' conflicts with your exclusion ({why}), so I removed it from your available ingredients.")
            continue
        have.append(h)
    pantry = _pantry(store, have)
    if not pantry:
        msg = "**No match possible:** none of your ingredients are left after applying your exclusions."
        if notes:
            msg += "\n" + "\n".join(f"- {n}" for n in notes)
        return msg, {"results": [], "no_match": True, "n_eligible": 0}

    filters = Filters(exclude=req.exclude, max_steps=req.max_steps)
    info = apply_filters(store, filters)
    ranked = _rank(store, info.mask, pantry, prefer, req.max_missing, req.must_use_all)

    out = []
    pantry_str = ", ".join(f"{it.family}" + (f" ({it.raw})" if it.qty[0] is not None else "") for it in pantry)
    out.append(f"**Your ingredients (normalised):** {pantry_str}")
    hard = info.description + ([f"at most {req.max_missing} extra ingredients"] if req.max_missing is not None else [])
    hard += (["must use all of your ingredients"] if req.must_use_all else [])
    out.append("**Hard constraints:** " + ("; ".join(hard) if hard else "none"))
    out.append(f"**Ranking:** {SORT_MODES[prefer]} (salt, pepper and water are assumed staples and not counted as missing)")
    for n in notes:
        out.append(f"_Note: {n}_")
    out.append("")

    data = {"pantry": [it.family for it in pantry], "n_eligible": len(ranked), "results": []}

    if not ranked:
        out.append(f"### No match found\nI checked all {len(store):,} recipes and none of them satisfies "
                   f"every hard constraint above. I have not relaxed any of them.")
        out += _closest_violations(store, pantry, req, prefer, info)
        data["no_match"] = True
        return "\n".join(out), data

    out.append(f"{len(ranked):,} recipes satisfy every constraint and use at least one of your ingredients. Top {min(req.n, len(ranked))}:\n")
    prev = None
    any_qty = any(it.qty[0] is not None for it in pantry)
    for rank, m in enumerate(ranked[: req.n], 1):
        row = store.row(m.pos)
        qnotes = []
        for it in m.used:
            qnotes += _quantity_notes(store, row, it)
        out.append(f"**{rank}. {row['title']}** — `{row['id']}`")
        out.append(f"- Uses: {', '.join(it.family for it in m.used)}")
        out.append(f"- Missing: {', '.join(m.missing) if m.missing else 'nothing beyond staples'}")
        if m.unused:
            out.append(f"- Not used: {', '.join(it.family for it in m.unused)}")
        out.append(f"- Steps: {m.n_steps} · Why here: {_why(prev, m, prefer, len(pantry))}")
        for q in qnotes:
            out.append(f"- Quantity: {q}")
        out.append("")
        prev = m
        data["results"].append({
            "id": row["id"], "title": row["title"], "used": [it.family for it in m.used],
            "missing": m.missing, "steps": m.n_steps,
        })
    if not any_qty:
        out.append("_Matching is by ingredient name only — you didn't give quantities, so I haven't checked whether you have enough of each._")
    return "\n".join(out), data


def _closest_violations(store: RecipeStore, pantry, req: MatchRequest, prefer: str, info) -> list[str]:
    relaxed = _rank(store, np.ones(len(store), dtype=bool), pantry, prefer, None)[:3]
    if not relaxed:
        return ["\nThere are no recipes using these ingredients at all, even without constraints."]
    lines = ["\n### Closest alternatives — ⚠️ these BREAK your constraints",
             "_Shown only for reference. None of these is a valid answer to your request._\n"]
    for m in relaxed:
        row = store.row(m.pos)
        broken = []
        for c in info.exclude_categories:
            hits = category_hits(row, [c])[c]
            if hits:
                broken.append(f"contains {CATEGORY_LABELS.get(c, c)} ('{hits[0]}')")
        for t in info.exclude_terms:
            hits = term_hits(row, t)
            if hits:
                broken.append(f"contains {t} ('{hits[0]}')")
        if req.max_steps is not None and m.n_steps > req.max_steps:
            broken.append(f"has {m.n_steps} steps (limit {req.max_steps})")
        if req.max_missing is not None and len(m.missing) > req.max_missing:
            broken.append(f"needs {len(m.missing)} extra ingredients (limit {req.max_missing})")
        if req.must_use_all and len(m.used) < len(pantry):
            broken.append(f"uses only {len(m.used)}/{len(pantry)} of your ingredients "
                          f"(missing: {', '.join(it.family for it in m.unused)})")
        lines.append(f"- ⚠️ **{row['title']}** — `{row['id']}` — violates: {'; '.join(broken) or 'n/a'}")
    return lines
