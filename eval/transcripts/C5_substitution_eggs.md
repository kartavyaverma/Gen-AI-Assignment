# C5_substitution_eggs
**Task 3 - substitution with limited evidence**

_Why this test:_ PDF example: remove eggs from banana bread using only dataset ingredients; cite supporting recipe IDs.

## Turn 1
**User:** Find a banana bread recipe

<details><summary>Router plan (LLM output)</summary>

```json
{
  "intent": "search",
  "constraints": {
    "add_exclude": [],
    "remove_exclude": [],
    "max_steps": null,
    "clear_max_steps": false
  },
  "search": {
    "query": "banana bread",
    "add_include": [],
    "remove_include": [],
    "new_search": true
  }
}
```
</details>

**Bot:**

🔎 **Search:** banana bread · **Active constraints:** none
12,181 recipes pass every constraint and share words with the query. Showing 1–5:

**1. Banana Bread** — `ar_BoBTO3QUO3Ci.0kayPs8.CfDU5oEXuu` · Allrecipes · 3 steps · 7 ingredients
**2. Banana Bread** — `fn_mhYRmKoUCwpXz5XIJ5.WG6FxMZwIR3m` · Food Network · 6 steps · 10 ingredients
**3. Banana Bread** — `epi_ZQd7/SuSfF5BCcq998A7.Zyhfaqusf6` · Epicurious · 6 steps · 10 ingredients
**4. Banana Bread** — `epi_Br9fwQQSw3wDvb/cp/nyL0LjUWtMfRi` · Epicurious · 13 steps · 10 ingredients
**5. Banana Bread** — `fn_J9d89klHetj.4b5OKiASicRh8tfXK6m` · Food Network · 2 steps · 10 ingredients

Say *show 2* for the full recipe, *more* for more results, or add a restriction.

**Checks:** ✅ all passed

---

## Turn 2
**User:** Take this banana bread recipe and remove the eggs. Use only ingredients that appear in the dataset. What replacements have evidence from related baked recipes, and how might the texture change?

<details><summary>Router plan (LLM output)</summary>

```json
{
  "intent": "substitute",
  "substitute": {
    "recipe_ref": "focus",
    "remove": "eggs",
    "restrictions": [],
    "dataset_only": true
  }
}
```
</details>

**Bot:**

### Adapting: Banana Bread (`ar_BoBTO3QUO3Ci.0kayPs8.CfDU5oEXuu`)
**Removing:** egg — affected lines: '2 eggs, beaten'
**Role of egg in this dish** _(general cooking knowledge, not from the dataset)_: binding (holds the crumb together), some lift/structure, and moisture

**Dataset evidence.** I found 188 recipes with similar titles. 169 of them use egg and 19 don't.

| Substitute | Evidence | Similar recipes **without** egg using it | Similar recipes **with** egg using it | Anywhere in dataset without egg |
|---|---|---:|---:|---:|
| yogurt | limited | 2 (11%) | 5% | 2,522 |
| silken tofu | limited | 1 (5%) | 0% | 99 |
| banana | co-occurs only | 15 (79%) | 96% | 1,517 |
| extra baking powder | co-occurs only | 5 (26%) | 50% | 1,327 |
| applesauce | co-occurs only | 1 (5%) | 5% | 184 |
| buttermilk | indirect | 0 (0%) | 12% | 1,016 |
| ground flaxseed | indirect | 0 (0%) | 2% | 279 |

_How to read this: a substitute only counts as evidence if it is **more common** in the similar recipes that skip egg than in the ones that use it. If it's equally common either way it just co-occurs (e.g. olive oil in pasta) and doesn't tell us it replaces anything._

Other ingredients that show up more often in the similar recipes *without* egg (just a data signal, not necessarily a substitute): bread flour (3 recipes), rolled oat (2 recipes), active dry yeast (2 recipes), over-ripe banana (2 recipes), honey (3 recipes)

### Suggested change: replace egg with **yogurt**
⚠️ Evidence is **limited**: only a few similar recipes do this.
Supporting recipes (similar dishes that do this):
- `fn_p174TykunvO./PLjDpl03RBTaXiOEdu` — Vegan Banana Bread: uses _'1/2 cup plain soy milk yogurt'_
- `ar_zDXYTtHNZiB/zBsPG4GYb4clr3Q4FYy` — Quaker® Banana Bread Overnight Oats: uses _'Plain or vanilla non-fat yogurt (optional)'_
- Amount guidance _(general cooking knowledge)_: about 1/4 cup plain yogurt per egg
- Also supported: silken tofu (1 similar recipes)

**Updated ingredients**
- 1 1/2 cups all-purpose flour
- 1 teaspoon baking soda
- 1/2 teaspoon salt
- 1 cup white sugar
- 1/2 cup plain yogurt
- 1/4 cup butter, melted
- 3 bananas, mashed

**Revised instructions**
1. Grease and flour two 7x3 inch loaf pans. Preheat oven to 350 degrees F (175 degrees C).
2. In one bowl, whisk together flour, soda, salt, and sugar. Mix in 1/2 cup plain yogurt, melted butter, and mashed bananas. Stir in nuts if desired. Pour into prepared pans.
3. Bake at 350 degrees F (175 degrees C) for 1 hour, or until a wooden toothpick inserted in the center comes out clean.

**What will probably change** _(prediction - not tested, and not stated in the dataset)_
- The bread will be extra moist and have a slight tang from the yogurt.
- Without eggs, the crumb may be a bit denser and rise slightly less, giving a softer texture.
- ⚠️ Yogurt does not provide the same structure as eggs, so the loaf may be a bit more crumbly and rise less than the original.

_Safety note: I checked the new ingredient list against my keyword lists for your restrictions and found nothing, but that is not a medical guarantee. Always check packaged ingredient labels for allergens._

**Checks:** ✅ all passed

---
