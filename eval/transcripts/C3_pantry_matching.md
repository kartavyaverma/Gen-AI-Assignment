# C3_pantry_matching
**Task 2 - ingredient matching with hard constraints + follow-up**

_Why this test:_ PDF example request, then 'Exclude eggs too' must update the results without dropping earlier constraints.

## Turn 1
**User:** I have eggs, onions, tomatoes, and rice. Suggest five recipes using as many of these as possible, with no peanuts and at most six instruction steps. Prefer recipes that need the fewest additional ingredients.

<details><summary>Router plan (LLM output)</summary>

```json
{
  "intent": "match",
  "constraints": {
    "add_exclude": [
      "peanuts"
    ],
    "max_steps": 6
  },
  "match": {
    "have": [
      "eggs",
      "onions",
      "tomatoes",
      "rice"
    ],
    "add_have": [],
    "remove_have": [],
    "prefer": "max_used",
    "max_missing": null,
    "must_use_all": false,
    "n": 5,
    "new_request": true
  }
}
```
</details>

**Bot:**

**Your ingredients (normalised):** egg, onion, tomato, rice
**Hard constraints:** excludes **peanuts** (checked every ingredient line against 4 peanut terms); at most 6 instruction steps
**Ranking:** most of your ingredients used → fewest extra ingredients → fewest steps (salt, pepper and water are assumed staples and not counted as missing)

52,415 recipes satisfy every constraint and use at least one of your ingredients. Top 5:

**1. Fiesta Egg Skillet** — `ar_QyVarQzRar/zTLW7ExZpc6qbYC1xQF6`
- Uses: egg, onion, tomato, rice
- Missing: olive oil, heavy cream, ham, green chili, cheddar cheese
- Steps: 5 · Why here: Top match: uses 4/4 of your ingredients, needs 5 extra, 5 steps.

**2. Curried Rice With Smoked Trout** — `fn_Akk/zqCo1n3wzwavH0..w6QIF5363M2`
- Uses: egg, onion, tomato, rice
- Missing: olive oil, curry powder, cilantro, greens, juice, smoked trout
- Steps: 3 · Why here: uses 4/4 of your ingredients, needs 6 extra, 3 steps — below the previous one because it needs more extra ingredients

**3. Omelet for Leftovers (Omurice)** — `ar_ylwbZEdf8zK8ZA6pqy15Wll6YtZyG2G`
- Uses: egg, onion, tomato, rice
- Missing: butter, bell pepper, zucchini, mushroom, ketchup, bacon, paprika
- Steps: 2 · Why here: uses 4/4 of your ingredients, needs 7 extra, 2 steps — below the previous one because it needs more extra ingredients

**4. Turkey Meatball Vindaloo** — `fn_Z8iATJKOvt1aLJVdw1DFqPxUlKbxwe.`
- Uses: egg, onion, tomato, rice
- Missing: ground turkey, breadcrumb, cilantro, ginger, olive oil, bell pepper, hot madras curry powder
- Steps: 3 · Why here: uses 4/4 of your ingredients, needs 7 extra, 3 steps — below the previous one because it has more steps

**5. Imitation Meatloaf** — `ar_q3kO3yCalJEVIp74kLkkcxHp6izs7zi`
- Uses: egg, onion, tomato, rice
- Missing: dry brown lentils, wheat germ, dry bread crumb, thyme, hot sauce, ketchup, soy sauce, mozzarella cheese
- Steps: 3 · Why here: uses 4/4 of your ingredients, needs 8 extra, 3 steps — below the previous one because it needs more extra ingredients

_Matching is by ingredient name only — you didn't give quantities, so I haven't checked whether you have enough of each._

**Checks:** ✅ all passed

---

## Turn 2
**User:** Exclude eggs too

<details><summary>Router plan (LLM output)</summary>

```json
{
  "intent": "match",
  "constraints": {
    "add_exclude": [
      "eggs"
    ]
  }
}
```
</details>

**Bot:**

**Your ingredients (normalised):** onion, tomato, rice
**Hard constraints:** excludes **peanuts** (checked every ingredient line against 4 peanut terms); excludes **egg** (checked every ingredient line against 9 egg terms); at most 6 instruction steps
**Ranking:** most of your ingredients used → fewest extra ingredients → fewest steps (salt, pepper and water are assumed staples and not counted as missing)
_Note: 'eggs' conflicts with your exclusion (egg), so I removed it from your available ingredients._

26,732 recipes satisfy every constraint and use at least one of your ingredients. Top 5:

**1. Easy Red Rice** — `ar_HEANjerxzzD5N/d0QMF7jOsTplW.f1K`
- Uses: onion, tomato, rice
- Missing: olive oil, chicken broth, basil
- Steps: 1 · Why here: Top match: uses 3/3 of your ingredients, needs 3 extra, 1 step.

**2. Zucchini Saute** — `ar_J/illFyDAANk7X1GwnmkQ4iMZPDTBmO`
- Uses: onion, tomato, rice
- Missing: vegetable oil, zucchini, bell pepper
- Steps: 2 · Why here: uses 3/3 of your ingredients, needs 3 extra, 2 steps — below the previous one because it has more steps

**3. Mexican Rice I** — `ar_tlxZ5TF3/OeA94/bLSh51tLF//pNk3.`
- Uses: onion, tomato, rice
- Missing: vegetable oil, cumin, chili powder
- Steps: 2 · Why here: uses 3/3 of your ingredients, needs 3 extra, 2 steps — tied on everything; ordered by ID

**4. Black Beans and Rice** — `fn_RwGqUrp5Mxzf/f5nCKmr0MofUtRB0Oy`
- Uses: onion, tomato, rice
- Missing: black bean, vegetable oil, okra
- Steps: 2 · Why here: uses 3/3 of your ingredients, needs 3 extra, 2 steps — tied on everything; ordered by ID

**5. Vary Aminanana (Collard Greens and Rice)** — `ar_wA.9BnVROfR6gjMSi2k5C7WoEoLYWOK`
- Uses: onion, tomato, rice
- Missing: olive oil, ginger, collard greens
- Steps: 3 · Why here: uses 3/3 of your ingredients, needs 3 extra, 3 steps — below the previous one because it has more steps

_Matching is by ingredient name only — you didn't give quantities, so I haven't checked whether you have enough of each._

**Checks:** ✅ all passed

---

## Turn 3
**User:** Actually rank them by fewest steps instead

<details><summary>Router plan (LLM output)</summary>

```json
{
  "intent": "match",
  "constraints": {
    "add_exclude": [],
    "remove_exclude": [],
    "max_steps": null,
    "clear_max_steps": false
  },
  "match": {
    "have": null,
    "add_have": [],
    "remove_have": [],
    "prefer": "fewest_steps",
    "max_missing": null,
    "must_use_all": false,
    "n": 5,
    "new_request": false
  }
}
```
</details>

**Bot:**

**Your ingredients (normalised):** onion, tomato, rice
**Hard constraints:** excludes **peanuts** (checked every ingredient line against 4 peanut terms); excludes **egg** (checked every ingredient line against 9 egg terms); at most 6 instruction steps
**Ranking:** fewest steps → most of your ingredients used → fewest extra ingredients (salt, pepper and water are assumed staples and not counted as missing)
_Note: 'eggs' conflicts with your exclusion (egg), so I removed it from your available ingredients._

26,732 recipes satisfy every constraint and use at least one of your ingredients. Top 5:

**1. Easy Red Rice** — `ar_HEANjerxzzD5N/d0QMF7jOsTplW.f1K`
- Uses: onion, tomato, rice
- Missing: olive oil, chicken broth, basil
- Steps: 1 · Why here: Top match: uses 3/3 of your ingredients, needs 3 extra, 1 step.

**2. Beef and Rice Medley** — `ar_mRW6Fb3mGS4xmtqe9fBLwNuutK9IFKC`
- Uses: onion, tomato, rice
- Missing: ground beef, beef bouillon, bell pepper, mozzarella cheese
- Steps: 1 · Why here: uses 3/3 of your ingredients, needs 4 extra, 1 step — below the previous one because it needs more extra ingredients

**3. Spanish Rice I** — `ar_oDeodbxQOVgVRfCJs8AYeVszKfd5pfG`
- Uses: onion, tomato, rice
- Missing: vegetable oil, bell pepper, mustard, tomato juice
- Steps: 1 · Why here: uses 3/3 of your ingredients, needs 4 extra, 1 step — tied on everything; ordered by ID

**4. Tracy's Tomato Artichoke Rice Salad** — `ar_q1pHj7jmtuLgyGutgL.WJkSPQuIBgWe`
- Uses: onion, tomato, rice
- Missing: marinated artichoke heart, lemon juice, garlic, black olive
- Steps: 1 · Why here: uses 3/3 of your ingredients, needs 4 extra, 1 step — tied on everything; ordered by ID

**5. Quick Black Beans and Rice** — `ar_wfUlYjE9tdgGB/ORZpNBOD2addjeKCa`
- Uses: onion, tomato, rice
- Missing: vegetable oil, black bean, oregano, garlic powder
- Steps: 1 · Why here: uses 3/3 of your ingredients, needs 4 extra, 1 step — tied on everything; ordered by ID

_Matching is by ingredient name only — you didn't give quantities, so I haven't checked whether you have enough of each._

**Checks:** ✅ all passed

---
