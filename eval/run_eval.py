"""Reproducible evaluation.

    uv run python eval/run_eval.py            # everything (needs GROQ_API_KEY for parts B and C)
    uv run python eval/run_eval.py --offline  # part A only (no API key needed)

Part A - deterministic tool checks (no LLM). These pin down the properties that
         matter: filters really exclude things, rankings are really sorted,
         numbers equal an independent recomputation, no-match is reported.
Part B - scripted multi-turn conversations through the full bot (LLM router +
         tools). Each turn has assertions; transcripts go to eval/transcripts/.
Part C - a plain one-shot LLM baseline on the same kind of questions, to show
         where an ungrounded answer goes wrong.

Results: eval/results.md and eval/results.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from recipebot.analytics import StatsSpec, run_stats  # noqa: E402
from recipebot.matching import MatchRequest, match_recipes  # noqa: E402
from recipebot.normalize import canonical_names, clean_line, family_of, line_categories  # noqa: E402
from recipebot.search import Filters, apply_filters, search  # noqa: E402
from recipebot.store import load_store  # noqa: E402
from recipebot.substitution import SubRequest, suggest_substitutes  # noqa: E402

EVAL_DIR = ROOT / "eval"
TRANSCRIPTS = EVAL_DIR / "transcripts"


# --------------------------------------------------------------------------- #
# Part A
# --------------------------------------------------------------------------- #

def part_a(store) -> list[dict]:
    results = []

    def check(cid, desc, fn):
        t = time.time()
        try:
            ok, detail = fn()
        except Exception as exc:  # a crash is a failure, not a stop
            ok, detail = False, f"crashed: {exc!r}"
        results.append({"id": cid, "desc": desc, "pass": bool(ok), "detail": detail,
                        "secs": round(time.time() - t, 2)})
        print(f"  [{'PASS' if ok else 'FAIL'}] {cid}: {desc} - {detail}")

    # --- normalisation ---
    def a1():
        cases = {
            "2 tablespoons peanut butter": ("peanut butter", {"peanut"}, "dairy"),
            "1 cup coconut milk": ("coconut milk", set(), "dairy"),
            "1 large eggplant, cubed": ("eggplant", set(), "egg"),
            "1 teaspoon garlic powder": ("garlic powder", set(), None),
            "2 (10.75 ounce) cans condensed cream of chicken soup ADVERTISEMENT": ("cream of chicken soup", {"dairy", "meat"}, None),
            "4 skinless, boneless chicken breast halves ADVERTISEMENT": ("chicken breast", {"meat"}, None),
        }
        bad = []
        for line, (name, cats, not_cat) in cases.items():
            got = canonical_names(line)
            gc = line_categories(clean_line(line))
            if not got or got[0] != name or not cats <= gc or (not_cat and not_cat in gc):
                bad.append(f"{line!r} -> {got} {sorted(gc)}")
        fam_ok = family_of("garlic powder") != "garlic" and family_of("red onion") == "onion" and family_of("egg yolk") == "egg"
        return (not bad and fam_ok), ("all normalisation cases ok" if not bad else "; ".join(bad))
    check("A1", "ingredient normalisation & allergen exceptions", a1)

    # --- step rule ---
    def a2():
        df = store.df
        epi = df[df["source"] == "epi"]
        dup = epi[epi["instructions"].map(lambda s: len([x for x in s.split("\n") if x.strip()])) > epi["n_steps"]]
        sample = dup.iloc[0]
        lines = [x.strip() for x in sample["instructions"].split("\n") if x.strip()]
        ok = sample["n_steps"] == len(dict.fromkeys(lines))
        return ok, f"{len(dup):,} Epicurious recipes had duplicated method lines; e.g. {sample['id']}: {len(lines)} raw lines -> {sample['n_steps']} steps"
    check("A2", "step counting removes duplicated/boilerplate lines", a2)

    # --- stats: count equals an independent recomputation ---
    def a3():
        ans = run_stats(store, StatsSpec("count", Filters(include=["garlic", "onion"])))
        g, o = store.mask_for("garlic"), store.mask_for("onion")
        manual = int((g & o).sum())
        pct = 100 * manual / len(store)
        ok = ans.data["count"] == manual and abs(ans.data["percent"] - pct) < 1e-3 and ans.data["broad_count"] >= manual
        return ok, f"bot={ans.data['count']:,} manual={manual:,} ({pct:.2f}% of {len(store):,}); broad rule={ans.data['broad_count']:,}"
    check("A3", "garlic AND onion count == independent numpy recomputation", a3)

    # --- stats: ranking is really the minimum ---
    def a4():
        ans = run_stats(store, StatsSpec("rank_by_steps", Filters(include=["tomato"]), n=5))
        mask = store.mask_for("tomato")
        true_min = int(store.n_steps[mask].min())
        steps = [r["steps"] for r in ans.data["ranking"]]
        all_tomato = all(mask[store.pos[r["id"]]] for r in ans.data["ranking"])
        ok = steps == sorted(steps) and steps[0] == true_min and all_tomato
        return ok, f"steps={steps}, true minimum over {int(mask.sum()):,} tomato recipes={true_min}"
    check("A4", "fewest-steps ranking is sorted and starts at the true minimum", a4)

    # --- search: dairy filter really holds over the whole result set ---
    def a5():
        res = search(store, "penne pasta", Filters(exclude=["dairy"]), k=20)
        info = apply_filters(store, Filters(exclude=["dairy"]))
        leaked = int((info.mask & store.category_mask["dairy"]).sum())
        hits_ok = all("dairy" not in store.row(h.pos)["cats"] for h in res.hits)
        return leaked == 0 and hits_ok and res.n_eligible > 0, f"{res.n_eligible:,} eligible penne results, 0 dairy leaks"
    check("A5", "'no dairy' filter excludes every dairy-flagged recipe", a5)

    # --- matching: PDF example ---
    def a6():
        md, d = match_recipes(store, MatchRequest(have=["eggs", "onions", "tomatoes", "rice"], exclude=["peanuts"], max_steps=6))
        rows = [store.get(r["id"]) for r in d["results"]]
        ok = len(rows) == 5 and all(r["n_steps"] <= 6 and "peanut" not in r["cats"] for r in rows)
        used = [len(r["used"]) for r in d["results"]]
        ok = ok and used == sorted(used, reverse=True)
        return ok, f"top-5 used counts {used}, steps {[int(r['n_steps']) for r in rows]}"
    check("A6", "pantry match respects no-peanuts / <=6 steps and ranks by ingredients used", a6)

    def a7():
        md, d = match_recipes(store, MatchRequest(have=["eggs", "onions", "tomatoes", "rice"], exclude=["peanuts", "eggs"], max_steps=6))
        rows = [store.get(r["id"]) for r in d["results"]]
        ok = "egg" not in d["pantry"] and all("egg" not in r["cats"] for r in rows) and "removed it" in md
        return ok, f"pantry now {d['pantry']}; no egg in any result"
    check("A7", "'exclude eggs too' removes eggs from pantry AND results", a7)

    def a8():
        md, d = match_recipes(store, MatchRequest(have=["lobster", "mango", "dark chocolate"], exclude=["dairy"], must_use_all=True, max_steps=4))
        ok = d.get("no_match") and "BREAK your constraints" in md and not d["results"]
        return ok, "no-match reported; alternatives shown separately and labelled as violations"
    check("A8", "no-match case is reported, never silently relaxed", a8)

    # --- substitution ---
    bread = store.get("ar_BoBTO3QUO3Ci.0kayPs8.CfDU5oEXuu")

    def a9():
        md, d = suggest_substitutes(store, SubRequest(bread["id"], "eggs", dataset_only=True))
        best = d.get("best")
        ok = best is not None and "egg" not in line_categories(best)
        cited = [c for c in re.findall(r"`((?:ar|epi|fn)_[^`]+)`", md.split("Suggested change")[-1]) if c != bread["id"]]
        cited_ok = bool(cited) and all(store.get(c) is not None and "egg" not in store.get(c)["cats"] for c in cited)
        banana = next(c for c in d["candidates"] if c["name"] == "banana")
        return ok and cited_ok and banana["strength"] == "co-occurs only", (
            f"best={best} (evidence: {next(c['strength'] for c in d['candidates'] if c['name'] == best)}); "
            f"cited {len(cited)} egg-free recipes, all verified egg-free; banana correctly marked 'co-occurs only'")
    check("A9", "egg substitution cites real egg-free recipes; co-occurrence isn't treated as evidence", a9)

    def a10():
        res = search(store, "creamy penne", Filters(include=["heavy cream"]), k=1)
        rid = store.ids[res.hits[0].pos]
        md, d = suggest_substitutes(store, SubRequest(rid, "cream", restrictions=["dairy"]))
        chosen_ok = d.get("best") is None or "dairy" not in line_categories(clean_line(d["best"]))
        rejected = [c["name"] for c in d["candidates"] if c["rejected"]]
        flagged = (not d.get("still_violating")) or ("does NOT meet your restrictions" in md)
        return chosen_ok and flagged, (f"recipe {rid}; best={d.get('best')}; still-violating lines flagged: "
                                       f"{d.get('still_violating') or 'none'}; rejected={rejected or 'none'}")
    check("A10", "dairy-free cream swap never picks dairy and flags leftover dairy lines", a10)

    def a11():
        md, d = suggest_substitutes(store, SubRequest(bread["id"], "saffron"))
        return (not d["ok"]) and "doesn't list" in md, "asking to replace an ingredient the recipe doesn't have is refused"
    check("A11", "substitution of an absent ingredient is refused, not invented", a11)

    return results


# --------------------------------------------------------------------------- #
# Part B
# --------------------------------------------------------------------------- #

def _turn_checks(bot, store, reply, exp: dict) -> list[str]:
    fails = []
    md, trace = reply.markdown, reply.trace
    intent = trace.get("intent")
    st = bot.state
    rows = [store.get(r) for r in st.last_results[:5]]

    if "intent" in exp and intent != exp["intent"]:
        fails.append(f"intent={intent}, expected {exp['intent']}")
    if "intent_any" in exp and intent not in exp["intent_any"]:
        fails.append(f"intent={intent}, expected one of {exp['intent_any']}")
    for w in exp.get("state_exclude_has", []):
        if not any(w.lower() in e.lower() for e in st.exclude):
            fails.append(f"active restrictions {st.exclude} missing '{w}'")
    if exp.get("results_nonempty") and not st.last_results:
        fails.append("no results")
    for cat in exp.get("results_avoid_categories", []):
        bad = [r["id"] for r in rows if cat in r["cats"]]
        if bad:
            fails.append(f"results contain {cat}: {bad}")
    if "results_max_steps" in exp:
        bad = [r["id"] for r in rows if r["n_steps"] > exp["results_max_steps"]]
        if bad:
            fails.append(f"results over step limit: {bad}")
    for w in exp.get("results_mention_all", []):
        bad = [r["id"] for r in rows if w not in (r["title"].lower() + " " + r["ing_text"])]
        if bad:
            fails.append(f"results not mentioning '{w}': {bad}")
    for s in exp.get("output_contains", []):
        if s not in md:
            fails.append(f"output missing '{s}'")
    if "output_contains_any" in exp and not any(s in md for s in exp["output_contains_any"]):
        fails.append(f"output has none of {exp['output_contains_any']}")
    for s in exp.get("output_not_contains", []):
        if s in md:
            fails.append(f"output should not contain '{s}'")
    if "output_regex" in exp and not re.search(exp["output_regex"], md):
        fails.append(f"output doesn't match /{exp['output_regex']}/")
    if "output_not_regex" in exp and re.search(exp["output_not_regex"], md, re.I):
        fails.append(f"output matches forbidden /{exp['output_not_regex']}/")
    if "focus_is_result" in exp:
        k = exp["focus_is_result"]
        if len(st.last_results) < k or st.focus != st.last_results[k - 1]:
            fails.append(f"focus {st.focus} is not result #{k}")
    if "matches_direct_stats" in exp:
        spec = exp["matches_direct_stats"]
        direct = run_stats(store, StatsSpec(
            metric=spec["metric"], filters=Filters(include=spec.get("include", [])),
            n=spec.get("n", 5), order=spec.get("order", "asc"), group_by_source=spec.get("group_by_source", False)))
        d = direct.data
        if spec["metric"] == "count" and f"{d['count']:,}" not in md:
            fails.append(f"count {d['count']:,} (direct computation) not in answer")
        if spec["metric"].startswith("rank_by"):
            missing = [r["id"] for r in d["ranking"] if r["id"] not in md]
            if missing:
                fails.append(f"ranking differs from direct computation: {missing}")
        if spec["metric"].endswith("_stats") and f"{d['stats']['mean']:.2f}" not in md:
            fails.append(f"mean {d['stats']['mean']:.2f} not in answer")
    if "rewrite_avoids_categories" in exp:
        sect = md.split("**Updated ingredients**")[-1].split("**Revised instructions**")[0]
        for cat in exp["rewrite_avoids_categories"]:
            bad = [ln for ln in sect.splitlines() if ln.startswith("- ") and cat in line_categories(clean_line(ln))
                   and "replaces:" not in ln]
            if bad:
                fails.append(f"rewritten ingredients still contain {cat}: {bad}")
    if exp.get("state_or_request_restricts"):
        plan = trace.get("plan", {})
        req = [r.lower() for r in (plan.get("substitute", {}) or {}).get("restrictions", [])] + [e.lower() for e in st.exclude]
        if not any(exp["state_or_request_restricts"] in r for r in req):
            fails.append(f"restriction '{exp['state_or_request_restricts']}' not passed to substitution")
    if "chosen_substitute_not_category" in exp:
        m = re.search(r"replace \w[\w ]* with \*\*(.+?)\*\*", md)
        if m and exp["chosen_substitute_not_category"] in line_categories(clean_line(m.group(1))):
            fails.append(f"chosen substitute {m.group(1)} is {exp['chosen_substitute_not_category']}")
    return fails


def part_b(store) -> list[dict]:
    from recipebot.agent import RecipeBot, plan_to_json

    TRANSCRIPTS.mkdir(parents=True, exist_ok=True)
    convs = json.loads((EVAL_DIR / "conversations.json").read_text(encoding="utf-8"))
    out = []
    for conv in convs:
        print(f"  conversation {conv['id']}")
        bot = RecipeBot(store=store)
        lines = [f"# {conv['id']}", f"**{conv['task']}**", "", f"_Why this test:_ {conv['why']}", ""]
        turn_results = []
        for i, turn in enumerate(conv["turns"], 1):
            reply = bot.handle(turn["user"])
            if reply.trace.get("error"):          # e.g. rate limit: wait once and retry
                time.sleep(20)
                reply = bot.handle(turn["user"])
            fails = _turn_checks(bot, store, reply, turn["expect"])
            turn_results.append({"turn": i, "user": turn["user"], "pass": not fails, "fails": fails,
                                 "intent": reply.trace.get("intent")})
            print(f"    turn {i}: {'PASS' if not fails else 'FAIL ' + '; '.join(fails)}")
            lines += [f"## Turn {i}", f"**User:** {turn['user']}", "",
                      "<details><summary>Router plan (LLM output)</summary>", "", "```json",
                      plan_to_json(reply.trace.get("plan", {})), "```", "</details>", "",
                      "**Bot:**", "", reply.markdown, "",
                      f"**Checks:** {'✅ all passed' if not fails else '❌ ' + '; '.join(fails)}", "", "---", ""]
            time.sleep(1.0)  # stay friendly with the free-tier rate limit
        (TRANSCRIPTS / f"{conv['id']}.md").write_text("\n".join(lines), encoding="utf-8")
        out.append({"id": conv["id"], "task": conv["task"], "turns": turn_results,
                    "pass": all(t["pass"] for t in turn_results)})
    return out


# --------------------------------------------------------------------------- #
# Part C
# --------------------------------------------------------------------------- #

def part_c(store) -> list[dict]:
    from recipebot.llm import one_shot_answer

    res = []
    count = run_stats(store, StatsSpec("count", Filters(include=["garlic", "onion"]))).data
    rank = run_stats(store, StatsSpec("rank_by_steps", Filters(include=["tomato"]), n=5)).data

    q1 = ("How many recipes in the Recipe Box dataset (Allrecipes, Epicurious and Food Network recipes) "
          "contain both garlic and onion? What percentage of the dataset is that?")
    refusal = re.compile(r"(don.t|do not|can.t|cannot|not able|unable)[^.]{0,60}(access|have|query|look|pull|browse)", re.I)

    a1 = one_shot_answer(q1)
    nums = [float(x.replace(",", "")) for x in re.findall(r"\b\d{1,3}(?:,\d{3})+\b|\b\d{4,6}\b", a1)]
    close = any(abs(n - count["count"]) / count["count"] < 0.05 for n in nums)
    if close:
        v1 = "a number within 5% of the computed count"
    elif refusal.search(a1[:600]):
        v1 = ("declined to answer (it can't see the data) and only offered code or a guess - honest, "
              "but the user gets no answer; RecipeBot computes it")
    else:
        v1 = "WRONG - no number within 5% of the real count"
    res.append({"id": "B1", "question": q1, "one_shot": a1,
                "grounded_answer": f"{count['count']:,} recipes = {count['percent']:.2f}% of {count['denominator']:,} (strict); "
                                   f"{count['broad_count']:,} with the loose any-mention rule",
                "verdict": v1})

    q2 = ("In the Recipe Box dataset, among recipes containing tomato, which five have the fewest "
          "instruction steps? Give their recipe IDs.")
    a2 = one_shot_answer(q2)
    ids = re.findall(r"\b[A-Za-z0-9./]{20,40}\b", a2)
    real = [i for i in ids if store.get(i) is not None or store.get("ar_" + i) is not None
            or store.get("epi_" + i) is not None or store.get("fn_" + i) is not None]
    if not ids:
        v2 = "gave no recipe IDs (declined / can't access the data) - no usable answer"
    else:
        v2 = f"{len(real)} of {len(ids)} ID-like strings exist in the dataset" + (" - IDs are invented" if not real else "")
    res.append({"id": "B2", "question": q2, "one_shot": a2,
                "grounded_answer": ", ".join(f"{r['id']} ({r['title']}, {r['steps']} step)" for r in rank["ranking"]),
                "verdict": v2})

    q4 = ("From the Recipe Box dataset, suggest five recipes that use eggs, onions, tomatoes and rice, "
          "contain no peanuts and have at most six instruction steps. Give the exact recipe titles as they "
          "appear in the dataset and the number of steps for each.")
    a4 = one_shot_answer(q4)
    titles = set(store.df["title"].str.lower().str.strip())
    named = [t.strip(" *\"'").strip() for t in re.findall(r"^\s*(?:\d+[.)]|[-*])\s*\**([^*\n|–—(]+)", a4, re.M)]
    named = [t for t in named if 3 < len(t) < 80]
    exist = [t for t in named if t.lower() in titles]
    md, d = match_recipes(store, MatchRequest(have=["eggs", "onions", "tomatoes", "rice"], exclude=["peanuts"], max_steps=6))
    res.append({"id": "B4", "question": q4, "one_shot": a4,
                "grounded_answer": "; ".join(f"{r['id']} ({r['title']}, {r['steps']} steps, uses {len(r['used'])}/4)" for r in d["results"]),
                "verdict": (f"{len(exist)} of {len(named)} titles it named exist in the dataset; even for those, its "
                            f"step counts and 'no peanuts' claim are unverified" if named else
                            "named no recipes")})

    q3 = ("Using the Recipe Box dataset, how many calories are in one slice of the Allrecipes 'Banana Bread' "
          "recipe and how long does it take to make?")
    a3 = one_shot_answer(q3)
    gives_number = bool(re.search(r"\b\d{2,4}\s*(k?cal|calories)\b", a3, re.I))
    res.append({"id": "B3", "question": q3, "one_shot": a3,
                "grounded_answer": "The dataset has no nutrition or time fields - RecipeBot says so and only quotes durations written in the steps.",
                "verdict": "states a calorie number the dataset cannot support" if gives_number else "did not invent calories"})
    return res


# --------------------------------------------------------------------------- #

def write_report(a, b, c) -> None:
    lines = ["# Evaluation results", "", f"_Generated by `eval/run_eval.py` on {time.strftime('%Y-%m-%d %H:%M')}._", ""]
    pa = sum(r["pass"] for r in a)
    lines += [f"## Part A - deterministic tool checks: {pa}/{len(a)} passed", "",
              "| ID | Check | Result | Detail |", "|---|---|---|---|"]
    lines += [f"| {r['id']} | {r['desc']} | {'✅' if r['pass'] else '❌'} | {r['detail']} |" for r in a]
    if b is not None:
        pt = sum(t["pass"] for conv in b for t in conv["turns"])
        nt = sum(len(conv["turns"]) for conv in b)
        lines += ["", f"## Part B - multi-turn conversations: {pt}/{nt} turns passed", "",
                  "| Conversation | Task | Turns passed | Failures |", "|---|---|---|---|"]
        for conv in b:
            fails = "; ".join(f"t{t['turn']}: {', '.join(t['fails'])}" for t in conv["turns"] if not t["pass"]) or "–"
            lines.append(f"| [{conv['id']}](transcripts/{conv['id']}.md) | {conv['task']} | "
                         f"{sum(t['pass'] for t in conv['turns'])}/{len(conv['turns'])} | {fails} |")
    else:
        lines += ["", "## Part B - skipped (no GROQ_API_KEY / --offline)"]
    if c is not None:
        lines += ["", "## Part C - one-shot LLM baseline vs. RecipeBot", ""]
        for r in c:
            lines += [f"### {r['id']}: {r['question']}", "", "**One-shot LLM answer:**", "",
                      "> " + r["one_shot"].strip().replace("\n", "\n> "), "",
                      f"**Grounded answer (RecipeBot):** {r['grounded_answer']}", "",
                      f"**Verdict:** {r['verdict']}", ""]
    else:
        lines += ["", "## Part C - skipped (no GROQ_API_KEY / --offline)"]
    (EVAL_DIR / "results.md").write_text("\n".join(lines), encoding="utf-8")
    (EVAL_DIR / "results.json").write_text(json.dumps({"A": a, "B": b, "C": c}, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="only run part A (no LLM calls)")
    args = ap.parse_args()

    from recipebot.config import GROQ_API_KEY

    store = load_store()
    print("Part A - deterministic tool checks")
    a = part_a(store)
    b = c = None
    if not args.offline and GROQ_API_KEY and GROQ_API_KEY != "your_groq_key_here":
        print("Part B - conversations")
        b = part_b(store)
        print("Part C - one-shot baseline")
        c = part_c(store)
    else:
        print("Skipping parts B and C (no API key or --offline).")
    write_report(a, b, c)
    print(f"\nWrote {EVAL_DIR / 'results.md'}")


if __name__ == "__main__":
    main()
