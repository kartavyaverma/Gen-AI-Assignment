# C2_aggregate_stats
**Task 1 - aggregate statistics**

_Why this test:_ Counts / percentages / rankings must be computed over the full filtered set and state filters, n and method.

## Turn 1
**User:** How many recipes contain both garlic and onion? What percentage of the dataset is that?

<details><summary>Router plan (LLM output)</summary>

```json
{
  "intent": "stats",
  "stats": {
    "metric": "count",
    "include": [
      "garlic",
      "onion"
    ]
  }
}
```
</details>

**Bot:**

**15,974 recipes** match — that is **12.99%** of the 122,931 recipes in the dataset.

For comparison, a looser rule — *any ingredient line that mentions the word*, which also counts things like garlic powder, onion soup mix or green onions — gives 20,244 recipes (16.47%). I report the stricter number as the answer because a recipe using only garlic powder doesn't really 'contain garlic'.

**How this was computed**
- Dataset: 122,931 complete recipes (all three source files; 2,233 empty/incomplete records excluded).
- Filters: contains **garlic** (normalised names counted: garlic, granulated garlic, crushed garlic, bulb garlic, pureed garlic, green garlic + 150 rarer variants); contains **onion** (normalised names counted: onion, red onion, pearl onion, granulated onion, yellow skinned onion, pickled red onion + 385 rarer variants)
- Recipes analysed: **15,974**
- Ingredient matching: lines are normalised (quantities, units and prep words removed, plurals singularised, varieties merged - e.g. red/yellow onion → onion, egg yolk → egg). Different products stay separate: *garlic powder* is not *garlic*, *green onion* is not *onion*.
- Calculation: count of recipes passing all filters ÷ 122,931 × 100.

**Checks:** ✅ all passed

---

## Turn 2
**User:** Among recipes containing tomato, which five have the fewest instruction steps?

<details><summary>Router plan (LLM output)</summary>

```json
{
  "intent": "stats",
  "stats": {
    "metric": "rank_by_steps",
    "include": [
      "tomato"
    ],
    "n": 5,
    "order": "asc"
  }
}
```
</details>

**Bot:**

The 5 matching recipes with the **fewest steps**:

| # | Recipe | ID | Steps | Ingredients |
|---|---|---|---:|---:|
| 1 | Sun-dried Tomatoes II | `ar_uBCUvjuuCrntPa57pw4TzLRAU/YE2DK` | 1 | 1 |
| 2 | Microwave Tomato Sauce | `fn_PXWJNziiEsfBUbX.EfiY/wtnaOVMThe` | 1 | 1 |
| 3 | Tilapia in Stewed Tomatoes | `ar_N/wTTh7I1Xp/DI51lAmn4jlttzh2npC` | 1 | 2 |
| 4 | Homemade Stewed Tomatoes | `ar_s.Y.9gQPj8/UboVuA9QPvWkqexshTE.` | 1 | 2 |
| 5 | Tomato Salsa | `fn_Cv.LzyOIGtSJN3dvLIBqPQo8ac.K97G` | 1 | 2 |

Note: 2,059 matching recipes have exactly 1 step, so the order among ties is decided by ingredients (fewest first) and then by ID.

**How this was computed**
- Dataset: 122,931 complete recipes (all three source files; 2,233 empty/incomplete records excluded).
- Filters: contains **tomato** (normalised names counted: tomato, plum tomato, cherry tomato, roma tomato, crushed tomato, grape tomato + 659 rarer variants)
- Recipes analysed: **13,781**
- Ingredient matching: lines are normalised (quantities, units and prep words removed, plurals singularised, varieties merged - e.g. red/yellow onion → onion, egg yolk → egg). Different products stay separate: *garlic powder* is not *garlic*, *green onion* is not *onion*.
- Calculation: sorted all 13,781 matches by steps (ascending). Rule: a step = one non-empty line of the original instructions, ignoring boilerplate like 'Watch how to make this recipe.' and exact duplicate lines.

**Checks:** ✅ all passed

---

## Turn 3
**User:** What's the average and median number of ingredients per recipe? Break it down by source.

<details><summary>Router plan (LLM output)</summary>

```json
{
  "intent": "stats",
  "stats": {
    "metric": "ingredient_count_stats",
    "group_by_source": true
  }
}
```
</details>

**Bot:**

Number of ingredients per recipe across 122,931 recipes:

| Mean | Median | Min | Max | Std dev |
|---:|---:|---:|---:|---:|
| 10.26 | 9.0 | 1 | 71 | 5.14 |

| Source | Recipes | Mean | Median |
|---|---:|---:|---:|
| Allrecipes | 39,522 | 9.02 | 9.0 |
| Epicurious | 25,258 | 9.71 | 9.0 |
| Food Network | 58,151 | 11.34 | 10.0 |

**How this was computed**
- Dataset: 122,931 complete recipes (all three source files; 2,233 empty/incomplete records excluded).
- Filters: none (whole dataset)
- Recipes analysed: **122,931**
- Calculation: numpy mean/median/min/max/std over all 122,931 values. Rule: ingredient count = number of distinct ingredient lines, ignoring section headers ('For the sauce:') and the scraper's 'ADVERTISEMENT' artefacts.

**Checks:** ✅ all passed

---
