# C6_substitution_dairy_weak
**Task 3 - substitution with weak / conflicting evidence and a hard restriction**

_Why this test:_ PDF example: replace cream in a pasta without dairy. The chosen recipe also contains other dairy, which must be flagged, not hidden.

## Turn 1
**User:** Show me a creamy penne pasta recipe that uses heavy cream

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
    "query": "creamy penne pasta",
    "add_include": [
      "heavy cream"
    ],
    "remove_include": [],
    "new_search": true
  }
}
```
</details>

**Bot:**

**Search:** creamy penne pasta · **Filters:** must include heavy cream
626 recipes pass every constraint and share words with the query. Showing 1–5:


**1. Creamy Pumpkin Pasta** — `ar_v37bt9V/V/yvSeFEP6XWiOWN73ep9pC` · Allrecipes · 3 steps · 11 ingredients
- contains heavy cream: _2/3 cup heavy whipping cream_

**2. 3-Ingredient Creamy Pumpkin Pasta** — `epi_OnoB5F/sLs8t/3UUmn.Hsmr1v8HjUSK` · Epicurious · 4 steps · 5 ingredients
- contains heavy cream: _1 1/4 cups heavy cream_

**3. Penne Pasta with Sausage and Cheesy Garlic Bread** — `fn_lh9vsC29xv9U6.ywWsPcsJL/I31Bnha` · Food Network · 7 steps · 14 ingredients · ⚠️ partial match (67% of query words)
- contains heavy cream: _1/4 cup heavy cream_

**4. One Recipe, Two Meals: Penne with a Creamy Tomato Vodka Sauce** — `fn_7XHa/jzELyj6nhcXaRChTkp032PQMp2` · Food Network · 6 steps · 10 ingredients
- contains heavy cream: _1/2 cup heavy cream_

**5. Creamy Garlic Pasta with Mushrooms and Prosciutto** — `epi_uUs4VGbDbASbOaz2esUPmJvkEsbFtZq` · Epicurious · 5 steps · 11 ingredients
- contains heavy cream: _3/4 cup whipping cream_

Say *show 2* for the full recipe, *more* for more results, or add a restriction.

**Checks:** ✅ all passed

---

## Turn 2
**User:** Replace the cream in this pasta recipe without dairy. Prefer examples from recipes already in the database.

<details><summary>Router plan (LLM output)</summary>

```json
{
  "intent": "substitute",
  "constraints": {
    "add_exclude": [
      "dairy"
    ]
  },
  "substitute": {
    "recipe_ref": "focus",
    "remove": "heavy cream",
    "restrictions": [
      "dairy"
    ],
    "dataset_only": false
  }
}
```
</details>

**Bot:**

### Adapting: Creamy Pumpkin Pasta (`ar_v37bt9V/V/yvSeFEP6XWiOWN73ep9pC`)
**Removing:** heavy cream — affected lines: '2/3 cup heavy whipping cream'
**Your restrictions:** dairy
**Role of heavy cream in this dish** _(general cooking knowledge, not from the dataset)_: richness (fat), body, and a smooth sauce that coats the food

**Dataset evidence.** I found 22 recipes with similar titles. 4 of them use heavy cream and 18 don't.

| Substitute | Evidence | Similar recipes **without** heavy cream using it | Similar recipes **with** heavy cream using it | Anywhere in dataset without heavy cream |
|---|---|---:|---:|---:|
| olive oil + pasta water | direct | 7 (39%) | 25% | 31,650 |
| coconut milk | limited | 1 (6%) | 0% | 1,324 |
| coconut cream | limited | 1 (6%) | 0% | 96 |
| cashews (blended) | limited | 1 (6%) | 0% | 543 |
| broth thickened with cornstarch | co-occurs only | 6 (33%) | 75% | 12,604 |
| soy milk | indirect | 0 (0%) | 0% | 240 |
| almond milk | indirect | 0 (0%) | 0% | 266 |

_How to read this: a substitute only counts as evidence if it is **more common** in the similar recipes that skip heavy cream than in the ones that use it. If it's equally common either way it just co-occurs (e.g. olive oil in pasta) and doesn't tell us it replaces anything._

Other ingredients that show up more often in the similar recipes *without* heavy cream (just a data signal, not necessarily a substitute): cinnamon (8 recipes), pumpkin puree (11 recipes), egg (4 recipes), vanilla extract (3 recipes), sage (3 recipes)

### Suggested change: replace heavy cream with **olive oil + pasta water**
Supporting recipes (similar dishes that do this):
- `ar_WNqifUmN8xhR/bA1mSeti.ZtxCn0/FW` — Pumpkin Pasta: uses _'1 tablespoon olive oil'_
- `ar_qcaXgvRsaURz35dwoz2rMhpCSYlt0vG` — Frugal Pumpkin Pasta: uses _'2 tablespoons olive oil'_
- `ar_nO670b2udJoZkwc69ZAp84G9fROBmu2` — Pumpkin Pasta with Cheddar: uses _'1 teaspoon olive oil'_
- Amount guidance _(general cooking knowledge)_: a few tbsp olive oil emulsified with starchy pasta water
- Also supported: coconut milk (1 similar recipes); cashews (blended) (1 similar recipes)

⚠️ **Other ingredients in this recipe also break your restrictions:** '1 tablespoon shredded Parmesan cheese, or more to taste'

**Updated ingredients**
- 2 tablespoons olive oil
- 1 onion, finely chopped
- 1 pound pumpkin - peeled, seeded, and cubed
- 2 cloves garlic, crushed
- 1 cup chicken stock
- 1 pinch ground nutmeg
- 9 ounces penne pasta
- 6 ounces bacon, cut into strips
- 1 tablespoon chopped fresh parsley
- 2-3 tablespoons olive oil, emulsified with reserved starchy pasta water
- 1 tablespoon nutritional yeast, or more to taste

**Revised instructions**
1. Heat oil in a pot over medium heat; cook and stir onion until slightly tender, about 3 minutes. Add pumpkin and garlic; continue cooking for 3 minutes. Add chicken stock and nutmeg; bring to a boil. Reduce heat to medium-low, cover, and simmer until pumpkin is tender, about 10 minutes more.
2. Bring a large pot of lightly salted water to a boil; add penne and cook, stirring occasionally, until tender yet firm to the bite, about 11 minutes. Drain and transfer to serving bowls.
3. Mix bacon and parsley into pumpkin mixture; cook, stirring frequently, until bacon is cooked, 2 to 5 minutes. Add the olive oil and a splash of reserved pasta water, stirring to emulsify, and cook until heated through, about 2 minutes more. Spoon sauce over pasta and top with nutritional yeast.

**What will probably change** _(prediction - not tested, and not stated in the dataset)_
- The olive oil‑pasta‑water emulsion will give a lighter, silkier sauce rather than the rich, thick mouthfeel of heavy cream.
- Nutritional yeast provides a cheesy, umami flavor but lacks the melt and texture of Parmesan.
- Overall the dish remains creamy‑sounding while being dairy‑free, though it may be slightly less indulgent.
- ⚠️ Olive oil cannot be whipped; the sauce relies on emulsifying with starchy pasta water, so reserve enough cooking water before draining.
- ⚠️ Nutritional yeast does not melt like Parmesan; the topping will be more powdery and may require extra seasoning to achieve desired flavor.
- ⚠️ If the sauce seems too thin, add a bit more pasta water or a drizzle of olive oil to reach desired consistency.

_Safety note: I checked the new ingredient list against my keyword lists for your restrictions and found nothing, but that is not a medical guarantee. Always check packaged ingredient labels for allergens._

**Checks:** ✅ all passed

---
