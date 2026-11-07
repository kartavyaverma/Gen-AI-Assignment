# C4_no_match
**Task 1 + Task 2 - no-match cases**

_Why this test:_ Hard constraints must never be relaxed silently; alternatives must be clearly marked as violating.

## Turn 1
**User:** I have lobster, mango and dark chocolate. I need a dairy-free recipe that uses all three, with at most 4 steps.

<details><summary>Router plan (LLM output)</summary>

```json
{
  "intent": "match",
  "constraints": {
    "add_exclude": [
      "dairy"
    ],
    "max_steps": 4
  },
  "match": {
    "have": [
      "lobster",
      "mango",
      "dark chocolate"
    ],
    "must_use_all": true,
    "prefer": "max_used",
    "new_request": true
  }
}
```
</details>

**Bot:**

🥕 **Your ingredients (normalised):** lobster, mango, chocolate
**Hard constraints:** excludes **dairy** (checked every ingredient line against 50 dairy terms); at most 4 instruction steps; must use all of your ingredients
**Ranking:** most of your ingredients used → fewest extra ingredients → fewest steps (salt, pepper and water are assumed staples and not counted as missing)

### No match found
I checked all 122,931 recipes and none of them satisfies every hard constraint above. I have not relaxed any of them.

### Closest alternatives — ⚠️ these BREAK your constraints
_Shown only for reference. None of these is a valid answer to your request._

- ⚠️ **Chocolate Lobster** — `ar_Wlx3t3ngzqyjwnM9.Xl6PRafio1ZPK.` — violates: contains dairy ('1/2 cup milk'); uses only 2/3 of your ingredients (missing: mango)
- ⚠️ **Coconut-Mango-Macadamia Nut Bark** — `fn_h9LXANs0IxA4hlhOOl1rUH5Ji.XmTcS` — violates: uses only 2/3 of your ingredients (missing: lobster)
- ⚠️ **Spicy Sweet Chocolate Fondue** — `fn_FUqzAQgYv/BdWYIOPSdjppTK.Umj4Gm` — violates: contains dairy ('1/2 cup heavy whipping cream'); uses only 2/3 of your ingredients (missing: lobster)

**Checks:** ✅ all passed

---

## Turn 2
**User:** Forget that. Find me a beef stew.

<details><summary>Router plan (LLM output)</summary>

```json
{
  "intent": "search",
  "constraints": {
    "remove_exclude": [
      "dairy"
    ],
    "clear_max_steps": true
  },
  "search": {
    "query": "beef stew",
    "add_include": [],
    "remove_include": [],
    "new_search": true
  }
}
```
</details>

**Bot:**

🔎 **Search:** beef stew · **Active constraints:** none
7,865 recipes pass every constraint and share words with the query. Showing 1–5:

**1. No-Peek Beef Stew** — `ar_OpTajAUZc3F0KM6bxzbwVT0yjPbnR3y` · Allrecipes · 1 step · 5 ingredients
**2. Baghdad Beef Stew** — `ar_WmVac/8fcweXzMFOM9xS0u0cZfbgLse` · Allrecipes · 4 steps · 14 ingredients
**3. Beef Stew I** — `ar_04qM6cy6L/TUu0jwPZV/tX1etVy4flu` · Allrecipes · 4 steps · 13 ingredients
**4. Beef Stew** — `ar_Fs3gQxTstWSYwiBEQfDfE87CqCI3m52` · Allrecipes · 2 steps · 15 ingredients
**5. Beef Stew** — `fn_/XwmjjCvQvYbYxsh.drBwAqmWljsHM2` · Food Network · 2 steps · 12 ingredients

Say *show 2* for the full recipe, *more* for more results, or add a restriction.

**Checks:** ✅ all passed

---

## Turn 3
**User:** I'm vegan.

<details><summary>Router plan (LLM output)</summary>

```json
{
  "intent": "search",
  "constraints": {
    "add_exclude": [
      "vegan"
    ]
  },
  "search": {
    "query": null,
    "add_include": [],
    "remove_include": [],
    "new_search": false
  }
}
```
</details>

**Bot:**

🔎 **Search:** beef stew · **Active constraints:** excluding vegan
**No recipe matches everything in 'beef stew'** while meeting your constraints. The results below are only *partial* matches (each one is missing some of the words you asked for) — shown so you can decide, not as an answer.

**1. Miso Stew** — `epi_peEjR1jUEY13UK3pWO4EYM0Rt4jG6nu` · Epicurious · 13 steps · 15 ingredients · ⚠️ partial match (50% of query words)
   - ✅ no meat/poultry, fish, shellfish, dairy, egg, honey found in its 15 ingredient lines: _2 tablespoons arame*; 4 1/2 cups water (preferably filtered); 1/3 cup quinoa** (1 3/4 oz); 1 (1-inch) piece kombu* (kelp); 1/2 medium onion, cut into 3/4-inch pieces; 2 teaspoons extra-virgin olive oil; 2 garlic cloves, thinly sliced; 1/2 lb firm tofu, cut crosswise into 6 slices and each slice quartered; 1/2 carrot, halved lengthwise, then cut crosswise into 1/4-inch-thick slices; 5 fresh shiitake mushrooms, stems discarded and caps thinly sliced; 2 to 3 tablespoons white miso*** (also called shiro miso; not sweet, preferably white rice and soy miso); 1 cup very thinly sliced bok choy or Napa cabbage; 1 teaspoon tamari**** (wheat-free sauce from refined soy), or to taste; 1 scallion, thinly sliced; 1/2 teaspoon dulse flakes*****_
**2. Wok Stew** — `fn_fEH1uuqFTsPFtHo/B.6/qfcZqqHwvNC` · Food Network · 2 steps · 12 ingredients · ⚠️ partial match (50% of query words)
   - ✅ no meat/poultry, fish, shellfish, dairy, egg, honey found in its 12 ingredient lines: _2 to 3 ounces olive oil; 1 medium to large eggplant, cubed; 1 large onion, diced; 1/4 pound asparagus, cut into 1-inch pieces; 6 leaves Napa cabbage, chopped; 1 basket cherry tomatoes, sliced in half; 1/2 pound yucca, peeled and cut into 1/4-inch pieces, roasted (400 degrees 20 to 30 minutes, or until brown and tender); Oregano; Sage; Thyme; Salt and pepper to taste; Round mini-loaves of bread_
**3. Drunken Winter Stew** — `ar_lfyBbCAHDn0p6Hbgc0NlrE/MToDNrCO` · Allrecipes · 3 steps · 10 ingredients · ⚠️ partial match (50% of query words)
   - ✅ no meat/poultry, fish, shellfish, dairy, egg, honey found in its 10 ingredient lines: _3 potatoes, peeled and cubed; 1/4 cup chopped onion; 1/2 medium head cabbage, sliced; 1 (15 ounce) can kidney beans, drained and rinsed; 3 cups water; 1 (12 fluid ounce) can beer; 1 tablespoon prepared Dijon-style mustard; 1/4 tablespoon garlic powder; ground black pepper to taste; salt to taste_
**4. Eggplant-Olive Caponata** — `fn_1j98cL4cZxBbfR5cPNKDwOIKQUH3RqW` · Food Network · 1 step · 4 ingredients
   - ✅ no meat/poultry, fish, shellfish, dairy, egg, honey found in its 4 ingredient lines: _1 cup reserved roasted vegetables from Roasted Vegetable stew; 1 cup diced fresh beefsteak tomatoes; 1/2 cup diced pitted kalamata olives; 2 tablespoons chopped fresh parsley leaves_
**5. Squash Stew** — `ar_BmohYMvq6w4sMWx3mrq3bXhwJXpW6Me` · Allrecipes · 3 steps · 12 ingredients · ⚠️ partial match (50% of query words)
   - ✅ no meat/poultry, fish, shellfish, dairy, egg, honey found in its 12 ingredient lines: _3 tablespoons olive oil; 1 large white onion, diced; 1 tablespoon ground cinnamon; 2 tablespoons chili powder; 4 cloves crushed garlic; 1 tablespoon cumin seeds, toasted; 2 tablespoons fresh lemon juice; 4 large tomatoes - peeled, seeded, and coarsely chopped; 1 medium acorn squash, peeled and diced; 1 cup pinto beans, cooked or canned; 1 cup water; salt and pepper to taste_

Say *show 2* for the full recipe, *more* for more results, or add a restriction.

**Checks:** ✅ all passed

---
