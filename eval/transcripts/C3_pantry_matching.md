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
    "prefer": "fewest_missing",
    "max_missing": null,
    "must_use_all": false,
    "n": 5,
    "new_request": true
  }
}
```
</details>

**Bot:**

🥕 **Your ingredients (normalised):** egg, onion, tomato, rice
**Hard constraints:** excludes **peanuts** (checked every ingredient line against 4 peanut terms); at most 6 instruction steps
**Ranking:** fewest extra ingredients → most of your ingredients used → fewest steps (salt, pepper and water are assumed staples and not counted as missing)

52,415 recipes satisfy every constraint and use at least one of your ingredients. Top 5:

**1. Steakhouse Onion Rings** — `fn_2i2JF.Q2bD0/0Rc3rFk/zWI7vTnthdu`
- ✅ Uses: egg, onion
- 🛒 Missing (you'd need): nothing beyond staples
- ➖ Not used from your list: tomato, rice
- Steps: 2 · Why here: Top match: uses 2/4 of your ingredients, needs 0 extra, 2 steps.

**2. Rice Cake** — `fn_XWh0MhuWrZJdmd/DXSa4AUs6PSLVmNu`
- ✅ Uses: egg, onion
- 🛒 Missing (you'd need): nothing beyond staples
- ➖ Not used from your list: tomato, rice
- Steps: 4 · Why here: uses 2/4 of your ingredients, needs 0 extra, 4 steps — below the previous one because it has more steps

**3. Divine Hard-Boiled Eggs** — `ar_GFZiUDrChDfN4bXTTNrraXqfRkle9oO`
- ✅ Uses: egg
- 🛒 Missing (you'd need): nothing beyond staples
- ➖ Not used from your list: onion, tomato, rice
- Steps: 1 · Why here: uses 1/4 of your ingredients, needs 0 extra, 1 step — below the previous one because it uses fewer of your ingredients

**4. Homemade Stewed Tomatoes** — `ar_s.Y.9gQPj8/UboVuA9QPvWkqexshTE.`
- ✅ Uses: tomato
- 🛒 Missing (you'd need): nothing beyond staples
- ➖ Not used from your list: egg, onion, rice
- Steps: 1 · Why here: uses 1/4 of your ingredients, needs 0 extra, 1 step — tied on everything; ordered by ID

**5. Soft Hard-Boiled Eggs** — `ar_t2AIs6xJeb9OlevKR7GSKwx4mklPPCe`
- ✅ Uses: egg
- 🛒 Missing (you'd need): nothing beyond staples
- ➖ Not used from your list: onion, tomato, rice
- Steps: 1 · Why here: uses 1/4 of your ingredients, needs 0 extra, 1 step — tied on everything; ordered by ID

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
  },
  "match": {
    "new_request": false
  }
}
```
</details>

**Bot:**

🥕 **Your ingredients (normalised):** onion, tomato, rice
**Hard constraints:** excludes **peanuts** (checked every ingredient line against 4 peanut terms); excludes **egg** (checked every ingredient line against 9 egg terms); at most 6 instruction steps
**Ranking:** fewest extra ingredients → most of your ingredients used → fewest steps (salt, pepper and water are assumed staples and not counted as missing)
_Note: 'eggs' conflicts with your exclusion (egg), so I removed it from your available ingredients._

26,732 recipes satisfy every constraint and use at least one of your ingredients. Top 5:

**1. Homemade Stewed Tomatoes** — `ar_s.Y.9gQPj8/UboVuA9QPvWkqexshTE.`
- ✅ Uses: tomato
- 🛒 Missing (you'd need): nothing beyond staples
- ➖ Not used from your list: onion, rice
- Steps: 1 · Why here: Top match: uses 1/3 of your ingredients, needs 0 extra, 1 step.

**2. Sun-dried Tomatoes II** — `ar_uBCUvjuuCrntPa57pw4TzLRAU/YE2DK`
- ✅ Uses: tomato
- 🛒 Missing (you'd need): nothing beyond staples
- ➖ Not used from your list: onion, rice
- Steps: 1 · Why here: uses 1/3 of your ingredients, needs 0 extra, 1 step — tied on everything; ordered by ID

**3. Perfect Steamed Rice** — `epi_.vfNcqqph.q4sRuaY8I/DopYilvhONy`
- ✅ Uses: rice
- 🛒 Missing (you'd need): nothing beyond staples
- ➖ Not used from your list: onion, tomato
- Steps: 1 · Why here: uses 1/3 of your ingredients, needs 0 extra, 1 step — tied on everything; ordered by ID

**4. Steamed Jasmine Rice** — `epi_3CGbKsbV.FR48TBGFbnWwUNK0q8zwtK`
- ✅ Uses: rice
- 🛒 Missing (you'd need): nothing beyond staples
- ➖ Not used from your list: onion, tomato
- Steps: 1 · Why here: uses 1/3 of your ingredients, needs 0 extra, 1 step — tied on everything; ordered by ID

**5. Chopstick Ready Rice** — `epi_DVsbqba5h4pGcFv/S38G7ujxy22cLCe`
- ✅ Uses: rice
- 🛒 Missing (you'd need): nothing beyond staples
- ➖ Not used from your list: onion, tomato
- Steps: 1 · Why here: uses 1/3 of your ingredients, needs 0 extra, 1 step — tied on everything; ordered by ID

_Matching is by ingredient name only — you didn't give quantities, so I haven't checked whether you have enough of each._

**Checks:** ✅ all passed

---

## Turn 3
**User:** Actually rank them by fewest steps instead

<details><summary>Router plan (LLM output)</summary>

```json
{
  "intent": "match",
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

🥕 **Your ingredients (normalised):** onion, tomato, rice
**Hard constraints:** excludes **peanuts** (checked every ingredient line against 4 peanut terms); excludes **egg** (checked every ingredient line against 9 egg terms); at most 6 instruction steps
**Ranking:** fewest steps → most of your ingredients used → fewest extra ingredients (salt, pepper and water are assumed staples and not counted as missing)
_Note: 'eggs' conflicts with your exclusion (egg), so I removed it from your available ingredients._

26,732 recipes satisfy every constraint and use at least one of your ingredients. Top 5:

**1. Easy Red Rice** — `ar_HEANjerxzzD5N/d0QMF7jOsTplW.f1K`
- ✅ Uses: onion, tomato, rice
- 🛒 Missing (you'd need): olive oil, chicken broth, basil
- Steps: 1 · Why here: Top match: uses 3/3 of your ingredients, needs 3 extra, 1 step.

**2. Beef and Rice Medley** — `ar_mRW6Fb3mGS4xmtqe9fBLwNuutK9IFKC`
- ✅ Uses: onion, tomato, rice
- 🛒 Missing (you'd need): ground beef, beef bouillon, bell pepper, mozzarella cheese
- Steps: 1 · Why here: uses 3/3 of your ingredients, needs 4 extra, 1 step — below the previous one because it needs more extra ingredients

**3. Spanish Rice I** — `ar_oDeodbxQOVgVRfCJs8AYeVszKfd5pfG`
- ✅ Uses: onion, tomato, rice
- 🛒 Missing (you'd need): vegetable oil, bell pepper, mustard, tomato juice
- Steps: 1 · Why here: uses 3/3 of your ingredients, needs 4 extra, 1 step — tied on everything; ordered by ID

**4. Tracy's Tomato Artichoke Rice Salad** — `ar_q1pHj7jmtuLgyGutgL.WJkSPQuIBgWe`
- ✅ Uses: onion, tomato, rice
- 🛒 Missing (you'd need): marinated artichoke heart, lemon juice, garlic, black olive
- Steps: 1 · Why here: uses 3/3 of your ingredients, needs 4 extra, 1 step — tied on everything; ordered by ID

**5. Quick Black Beans and Rice** — `ar_wfUlYjE9tdgGB/ORZpNBOD2addjeKCa`
- ✅ Uses: onion, tomato, rice
- 🛒 Missing (you'd need): vegetable oil, black bean, oregano, garlic powder
- Steps: 1 · Why here: uses 3/3 of your ingredients, needs 4 extra, 1 step — tied on everything; ordered by ID

_Matching is by ingredient name only — you didn't give quantities, so I haven't checked whether you have enough of each._

**Checks:** ✅ all passed

---
