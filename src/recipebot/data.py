from __future__ import annotations

import json
import re

import pandas as pd

from .config import RAW_DIR, SOURCES
from .normalize import canonical_names, clean_line, family_of, is_header, line_categories

SOURCE_NAMES = {"ar": "Allrecipes", "epi": "Epicurious", "fn": "Food Network"}

_BOILERPLATE = re.compile(
    r"^(watch how to make this recipe\.?|advertisement|photograph by .*|recipe courtesy .*)$",
    re.IGNORECASE,
)


def split_steps(instructions: str) -> list[str]:
    steps, seen = [], set()
    for raw in (instructions or "").split("\n"):
        line = raw.strip()
        if not line or _BOILERPLATE.match(line) or line in seen:
            continue
        seen.add(line)
        steps.append(line)
    return steps


def display_ingredients(raw: list[str]) -> list[str]:
    out = []
    for line in raw or []:
        text = re.sub(r"\s+", " ", (line or "").replace("ADVERTISEMENT", " ")).strip()
        if text:
            out.append(text)
    return out


def _process_record(source: str, key: str, rec: dict) -> dict | None:
    if not rec:
        return None
    title = (rec.get("title") or "").strip()
    raw_ings = rec.get("ingredients") or []
    instructions = rec.get("instructions") or ""
    ingredients = display_ingredients(raw_ings)
    steps = split_steps(instructions)
    if not title or not ingredients or not steps:
        return None

    names: list[str] = []
    cats: set[str] = set()
    counted_lines = []
    for line in ingredients:
        if is_header(line):
            continue
        cl = clean_line(line)
        if cl not in counted_lines:
            counted_lines.append(cl)
        cats |= line_categories(cl)
        for n in canonical_names(line):
            if n not in names:
                names.append(n)

    if not counted_lines:
        return None

    families = []
    for n in names:
        f = family_of(n)
        if f not in families:
            families.append(f)

    return {
        "id": f"{source}_{key}",
        "source": source,
        "title": title,
        "ingredients_raw": list(raw_ings),
        "ingredients": ingredients,
        "instructions": instructions,
        "steps": steps,
        "n_steps": len(steps),
        "n_ingredients": len(counted_lines),
        "names": names,
        "families": families,
        "ing_text": " | ".join(counted_lines),
        "cats": sorted(cats),
    }


def load_raw() -> dict[str, dict]:
    data = {}
    for src, fname in SOURCES.items():
        path = RAW_DIR / fname
        if not path.exists():
            raise FileNotFoundError(
                f"{path} not found. Run `uv run python scripts/download_data.py` first."
            )
        with open(path, encoding="utf-8") as fh:
            data[src] = json.load(fh)
    return data


def build_dataframe(verbose: bool = True) -> tuple[pd.DataFrame, dict]:
    raw = load_raw()
    rows, report = [], {"raw_records": 0, "kept": 0, "dropped_incomplete": 0, "per_source": {}}
    for src, recs in raw.items():
        kept = 0
        for key, rec in recs.items():
            report["raw_records"] += 1
            row = _process_record(src, key, rec)
            if row is None:
                report["dropped_incomplete"] += 1
                continue
            rows.append(row)
            kept += 1
        report["per_source"][src] = {"raw": len(recs), "kept": kept}
        if verbose:
            print(f"  {SOURCE_NAMES[src]:<13} {kept:>6} / {len(recs)} records kept")
    df = pd.DataFrame(rows).set_index("id", drop=False)
    report["kept"] = len(df)
    return df, report
