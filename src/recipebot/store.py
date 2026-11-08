from __future__ import annotations

import pickle
from collections import defaultdict
from functools import lru_cache

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from .config import INDEX_PKL, PROCESSED_DIR, RECIPES_PKL


class RecipeStore:
    def __init__(self, df: pd.DataFrame, title_vec, title_mat, ing_vec, ing_mat, report: dict):
        self.df = df
        self.title_vec, self.title_mat = title_vec, title_mat
        self.ing_vec, self.ing_mat = ing_vec, ing_mat
        self.report = report
        self.ids = df["id"].to_numpy()
        self.pos = {rid: i for i, rid in enumerate(self.ids)}
        self.n_steps = df["n_steps"].to_numpy()
        self.n_ingredients = df["n_ingredients"].to_numpy()
        self.ing_text = df["ing_text"].to_numpy()
        self._names_cache: dict[str, list[str]] = {}

        fam_idx, name_idx = defaultdict(list), defaultdict(list)
        for i, (fams, names) in enumerate(zip(df["families"], df["names"])):
            for f in fams:
                fam_idx[f].append(i)
            for n in names:
                name_idx[n].append(i)
        self.family_index = {k: np.asarray(v, dtype=np.int32) for k, v in fam_idx.items()}
        self.name_index = {k: np.asarray(v, dtype=np.int32) for k, v in name_idx.items()}

        cats_series = df["cats"]
        all_cats = sorted({c for cs in cats_series for c in cs})
        self.category_mask = {
            c: np.fromiter((c in cs for cs in cats_series), dtype=bool, count=len(df))
            for c in all_cats
        }

    def __len__(self) -> int:
        return len(self.df)

    def row(self, i: int) -> pd.Series:
        return self.df.iloc[i]

    def get(self, recipe_id: str) -> pd.Series | None:
        i = self.pos.get(recipe_id)
        if i is None:
            matches = [rid for rid in self.ids if rid.startswith(recipe_id)] if len(recipe_id) >= 6 else []
            if len(matches) == 1:
                i = self.pos[matches[0]]
        return None if i is None else self.df.iloc[i]

    def family_count(self, family: str) -> int:
        return len(self.family_index.get(family, ()))

    def names_for(self, family: str) -> list[str]:
        cached = self._names_cache.get(family)
        if cached is not None:
            return cached
        from .normalize import DIFFERENT_PRODUCTS, family_of

        out = []
        suffix = " " + family
        for name, idx in self.name_index.items():
            if name in DIFFERENT_PRODUCTS:
                continue
            if family_of(name) == family or name == family or name.endswith(suffix):
                out.append((len(idx), name))
        out.sort(reverse=True)
        names = [n for _, n in out]
        self._names_cache[family] = names
        return names

    def mask_for(self, family: str) -> np.ndarray:
        mask = np.zeros(len(self), dtype=bool)
        for n in self.names_for(family):
            mask[self.name_index[n]] = True
        return mask


def _build_text_indexes(df: pd.DataFrame):
    title_vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True, stop_words="english")
    title_mat = title_vec.fit_transform(df["title"].str.lower())
    ing_docs = df["names"].map(lambda ns: " ".join(ns))
    ing_vec = TfidfVectorizer(ngram_range=(1, 2), min_df=3, sublinear_tf=True)
    ing_mat = ing_vec.fit_transform(ing_docs)
    return title_vec, title_mat, ing_vec, ing_mat


def build_and_save(verbose: bool = True) -> RecipeStore:
    from .data import build_dataframe

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    if verbose:
        print("Reading and normalising the three JSON files...")
    df, report = build_dataframe(verbose=verbose)
    if verbose:
        print(f"Kept {report['kept']:,} of {report['raw_records']:,} records "
              f"({report['dropped_incomplete']:,} incomplete ones dropped).")
        print("Building TF-IDF indexes...")
    title_vec, title_mat, ing_vec, ing_mat = _build_text_indexes(df)
    df.to_pickle(RECIPES_PKL)
    with open(INDEX_PKL, "wb") as fh:
        pickle.dump({"title_vec": title_vec, "title_mat": title_mat,
                     "ing_vec": ing_vec, "ing_mat": ing_mat, "report": report}, fh)
    if verbose:
        print(f"Saved to {PROCESSED_DIR}")
    return RecipeStore(df, title_vec, title_mat, ing_vec, ing_mat, report)


@lru_cache(maxsize=1)
def load_store() -> RecipeStore:
    if not RECIPES_PKL.exists() or not INDEX_PKL.exists():
        print("Processed data not found - building it now (one-time, ~2 minutes).")
        return build_and_save()
    df = pd.read_pickle(RECIPES_PKL)
    with open(INDEX_PKL, "rb") as fh:
        idx = pickle.load(fh)
    return RecipeStore(df, idx["title_vec"], idx["title_mat"], idx["ing_vec"], idx["ing_mat"], idx["report"])
