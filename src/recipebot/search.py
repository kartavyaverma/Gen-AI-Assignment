from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .normalize import (
    CATEGORY_TERMS,
    clean_line,
    normalize_user_ingredient,
    resolve_restriction,
    term_regex,
)
from .store import RecipeStore

CATEGORY_LABELS = {
    "dairy": "dairy", "egg": "egg", "peanut": "peanuts", "tree_nut": "tree nuts",
    "gluten": "gluten", "meat": "meat/poultry", "fish": "fish", "shellfish": "shellfish",
    "pork": "pork", "alcohol": "alcohol", "soy": "soy", "honey": "honey",
}


@dataclass
class Filters:
    include: list[str] = field(default_factory=list)
    include_any: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    max_steps: int | None = None
    min_steps: int | None = None
    max_ingredients: int | None = None
    title_contains: list[str] = field(default_factory=list)
    source: str | None = None

    def is_empty(self) -> bool:
        return not (self.include or self.include_any or self.exclude or self.max_steps
                    or self.min_steps or self.max_ingredients or self.title_contains or self.source)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v not in (None, [], "")}


@dataclass
class FilterResult:
    mask: np.ndarray
    description: list[str]
    include_families: list[str]
    exclude_categories: list[str]
    exclude_terms: list[str]


def _family_mask(store: RecipeStore, family: str) -> tuple[np.ndarray, str]:
    names = store.names_for(family)
    if names:
        mask = store.mask_for(family)
        shown = ", ".join(names[:6])
        more = f" + {len(names) - 6} rarer variants" if len(names) > 6 else ""
        return mask, f"normalised names counted: {shown}{more}"
    rx = term_regex(family)
    mask = np.fromiter((bool(rx.search(t)) for t in store.ing_text), dtype=bool, count=len(store))
    return mask, "text match on ingredient lines (name not in the normalised vocabulary)"


def broad_mask(store: RecipeStore, term: str) -> np.ndarray:
    rx = term_regex(term)
    return np.fromiter((bool(rx.search(t)) for t in store.ing_text), dtype=bool, count=len(store))


def exclusion_parts(exclude: list[str]) -> tuple[list[str], list[str]]:
    cats, terms = [], []
    for word in exclude:
        c, t = resolve_restriction(word)
        for x in c:
            if x not in cats:
                cats.append(x)
        if t and t not in terms:
            terms.append(t)
    return cats, terms


def apply_filters(store: RecipeStore, f: Filters) -> FilterResult:
    mask = np.ones(len(store), dtype=bool)
    desc: list[str] = []

    fams = []
    for ing in f.include:
        fam = normalize_user_ingredient(ing)
        fams.append(fam)
        m, how = _family_mask(store, fam)
        mask &= m
        desc.append(f"contains **{fam}** ({how})")

    if f.include_any:
        any_mask = np.zeros(len(store), dtype=bool)
        any_fams = [normalize_user_ingredient(x) for x in f.include_any]
        for fam in any_fams:
            any_mask |= _family_mask(store, fam)[0]
        mask &= any_mask
        desc.append("contains at least one of: " + ", ".join(any_fams))

    cats, terms = exclusion_parts(f.exclude)
    for c in cats:
        cm = store.category_mask.get(c)
        if cm is not None:
            mask &= ~cm
        desc.append(f"excludes **{CATEGORY_LABELS.get(c, c)}** "
                    f"(checked every ingredient line against {len(CATEGORY_TERMS.get(c, []))} {c} terms)")
    for t in terms:
        mask &= ~broad_mask(store, t)
        desc.append(f"excludes anything mentioning **{t}** in any ingredient line")

    if f.max_steps is not None:
        mask &= store.n_steps <= f.max_steps
        desc.append(f"at most {f.max_steps} instruction steps")
    if f.min_steps is not None:
        mask &= store.n_steps >= f.min_steps
        desc.append(f"at least {f.min_steps} instruction steps")
    if f.max_ingredients is not None:
        mask &= store.n_ingredients <= f.max_ingredients
        desc.append(f"at most {f.max_ingredients} ingredients")
    for word in f.title_contains:
        rx = term_regex(word)
        titles = store.df["title"].str.lower().to_numpy()
        mask &= np.fromiter((bool(rx.search(t)) for t in titles), dtype=bool, count=len(store))
        desc.append(f"title contains '{word}'")
    if f.source:
        mask &= (store.df["source"].to_numpy() == f.source)
        desc.append(f"source = {f.source}")

    return FilterResult(mask, desc, fams, cats, terms)


@dataclass
class SearchHit:
    pos: int
    score: float
    coverage: float = 1.0


@dataclass
class SearchResult:
    query: str
    filters: Filters
    filter_info: FilterResult
    hits: list[SearchHit]
    n_eligible: int


def text_scores(store: RecipeStore, query: str) -> np.ndarray:
    q = clean_line(query)
    t = store.title_mat @ store.title_vec.transform([q]).T
    i = store.ing_mat @ store.ing_vec.transform([q]).T
    return 0.7 * t.toarray().ravel() + 0.3 * i.toarray().ravel()


def search(store: RecipeStore, query: str, filters: Filters | None = None, k: int = 5,
           exclude_ids: set[str] | None = None) -> SearchResult:
    filters = filters or Filters()
    info = apply_filters(store, filters)
    mask = info.mask.copy()
    if exclude_ids:
        for rid in exclude_ids:
            p = store.pos.get(rid)
            if p is not None:
                mask[p] = False

    q = (query or "").strip() or " ".join(filters.include + filters.include_any)
    if q:
        scores = text_scores(store, q)
        eligible = mask & (scores > 0)
    else:
        scores = -store.n_steps.astype(float)
        eligible = mask

    n_eligible = int(eligible.sum())
    if n_eligible == 0:
        return SearchResult(q, filters, info, [], 0)
    cand = np.flatnonzero(eligible)
    order = cand[np.argsort(-scores[cand], kind="stable")[:500]]
    cov_of: dict[int, float] = {}
    if q and (query or "").strip():
        words = _content_words(q)
        if words:
            titles = store.df["title"].to_numpy()
            cov = np.array([_coverage(words, titles[p].lower() + " " + store.ing_text[p]) for p in order])
            cov_of = {int(p): float(c) for p, c in zip(order, cov)}
            final = scores[order] * cov ** 2
            order = order[np.argsort(-final, kind="stable")]
            scores = scores.copy()
            scores[order] = np.sort(final)[::-1]
    order = order[:k]
    hits = [SearchHit(int(p), float(scores[p]), cov_of.get(int(p), 1.0)) for p in order]
    return SearchResult(q, filters, info, hits, n_eligible)


_STOP = {"a", "an", "the", "with", "and", "or", "recipe", "recipes", "for", "of", "in", "some",
         "find", "me", "show", "dish", "something", "make", "easy", "good", "best", "quick"}


def _content_words(q: str) -> list[str]:
    from .normalize import singularize

    return [singularize(w) for w in clean_line(q).replace(",", " ").split() if w not in _STOP and len(w) > 2]


def _coverage(words: list[str], text: str) -> float:
    return sum(1 for w in words if w in text) / len(words)


def find_by_title(store: RecipeStore, title: str, k: int = 5) -> list[int]:
    s = (store.title_mat @ store.title_vec.transform([clean_line(title)]).T).toarray().ravel()
    order = np.argsort(-s)[:k]
    return [int(p) for p in order if s[p] > 0]


def line_matches_family(store: RecipeStore, line: str, family: str) -> bool:
    from .normalize import canonical_names, family_of

    names = store.names_for(family)
    if names:
        allowed = set(names)
        return any(n in allowed or family_of(n) == family for n in canonical_names(line))
    return bool(term_regex(family).search(clean_line(line)))


def evidence_lines(store: RecipeStore, row, families: list[str]) -> dict[str, list[str]]:
    return {fam: [ln for ln in row["ingredients"] if line_matches_family(store, ln, fam)]
            for fam in families}


def category_hits(row, categories: list[str]) -> dict[str, list[str]]:
    from .normalize import line_categories

    out: dict[str, list[str]] = {c: [] for c in categories}
    for ln in row["ingredients"]:
        cats = line_categories(clean_line(ln))
        for c in categories:
            if c in cats:
                out[c].append(ln)
    return out


def term_hits(row, term: str) -> list[str]:
    rx = term_regex(term)
    return [ln for ln in row["ingredients"] if rx.search(clean_line(ln))]
