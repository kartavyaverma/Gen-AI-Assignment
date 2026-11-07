# C6_substitution_dairy_weak
**Task 3 - substitution with weak / conflicting evidence and a hard restriction**

_Why this test:_ PDF example: replace cream in a pasta without dairy. The chosen recipe also contains other dairy, which must be flagged, not hidden.

## Turn 1
**User:** Show me a creamy penne pasta recipe that uses heavy cream

<details><summary>Router plan (LLM output)</summary>

```json
{
  "intent": "search",
  "search": {
    "query": "penne pasta",
    "add_include": [
      "heavy cream"
    ],
    "new_search": true
  }
}
```
</details>

**Bot:**

🔎 **Search:** penne pasta · **Active constraints:** must include heavy cream
337 recipes pass every constraint and share words with the query. Showing 1–5:

**1. Penne Pasta with Sausage and Cheesy Garlic Bread** — `fn_lh9vsC29xv9U6.ywWsPcsJL/I31Bnha` · Food Network · 7 steps · 14 ingredients
   - contains heavy cream: _1/4 cup heavy cream_
**2. Pepperoni Penne** — `ar_mvenq6TC20.ln4I3ub7aVIoPJzX/Udi` · Allrecipes · 4 steps · 8 ingredients
   - contains heavy cream: _1 cup heavy whipping cream_
**3. Penne with Five Cheeses** — `fn_WLt0/oFuLw9V2/v6rGC54Hcpx0irl.u` · Food Network · 5 steps · 11 ingredients
   - contains heavy cream: _2 cups heavy cream_
**4. Penne Russo a la Vodka** — `ar_4/X8.H3Jsz5imVukzjRXy5FEz83A/Nq` · Allrecipes · 2 steps · 11 ingredients
   - contains heavy cream: _1 cup heavy cream_
**5. Thyme Pasta Frittata** — `fn_G.1x5l6/.SCd6b2SINmxz5z2FCd696S` · Food Network · 3 steps · 10 ingredients
   - contains heavy cream: _3 tablespoons whipping cream_

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
    "dataset_only": true
  }
}
```
</details>

**Bot:**

🔁 ### Adapting: Penne Pasta with Sausage and Cheesy Garlic Bread (`fn_lh9vsC29xv9U6.ywWsPcsJL/I31Bnha`)
**Removing:** heavy cream — affected lines: '1/4 cup heavy cream'
**Your restrictions:** dairy
**Role of heavy cream in this dish** _(general cooking knowledge, not from the dataset)_: richness (fat), body, and a smooth sauce that coats the food

**Dataset evidence.** I found 36 recipes with similar titles. 0 of them use heavy cream and 36 don't.
⚠️ Only 0 similar recipe(s) use heavy cream, so I can't compare 'with' vs 'without'. That means I can't tell a real substitute from something that just appears in this kind of dish anyway. No candidate is rated higher than *limited*.

| Substitute | Evidence | Similar recipes **without** heavy cream using it | Similar recipes **with** heavy cream using it | Anywhere in dataset without heavy cream |
|---|---|---:|---:|---:|
| olive oil + pasta water | limited | 19 (53%) | 0% | 31,650 |
| broth thickened with cornstarch | limited | 2 (6%) | 0% | 12,604 |
| coconut milk | indirect | 0 (0%) | 0% | 1,324 |
| coconut cream | indirect | 0 (0%) | 0% | 96 |
| cashews (blended) | indirect | 0 (0%) | 0% | 543 |
| soy milk | indirect | 0 (0%) | 0% | 240 |
| almond milk | indirect | 0 (0%) | 0% | 266 |

_How to read this: a substitute only counts as evidence if it is **more common** in the similar recipes that skip heavy cream than in the ones that use it. If it's equally common either way it just co-occurs (e.g. olive oil in pasta) and doesn't tell us it replaces anything._

Other ingredients that show up more often in the similar recipes *without* heavy cream (just a data signal, not necessarily a substitute): parsley (14 recipes), oregano (9 recipes), italian bread (6 recipes), zucchini (3 recipes), paprika (3 recipes)

### Suggested change: replace heavy cream with **olive oil + pasta water**
⚠️ Evidence is **limited**: only a few similar recipes do this.
Supporting recipes (similar dishes that do this):
- `fn_O6AnyXtraQPjPjvXJHxqs.d7gt0F8ua` — Grilled Cheesy Garlic Bread: uses _'1/2 cup virgin olive oil'_
- `ar_nvQzTEX.J7/2LmKnF8KjsR6aCqNHGxO` — Creamy Penne Pasta: uses _'2 tablespoons olive oil'_
- `fn_RvZR9.CbNY3mVGdNFzT6QDJ2oq.TZlu` — Garlic Bread: uses _'1/4 cup olive oil'_
- Amount guidance _(general cooking knowledge)_: a few tbsp olive oil emulsified with starchy pasta water
- Also supported: broth thickened with cornstarch (2 similar recipes)

⚠️ **Other ingredients in this recipe also break your restrictions:** '1 cup shredded mozzarella cheese'

**Updated ingredients**
- 1 pound penne pasta
- 2 tablespoons olive oil
- 1/2 medium yellow onion, diced
- 1 tablespoon garlic, chopped
- 1 tablespoon Italian seasoning mix
- 1/4 teaspoon crushed red pepper flake, optional
- 4 Italian-style hot pork sausages, cut into 1/2-inch slices
- 1 (28-ounce) can diced tomatoes, drained
- Kosher salt and freshly ground black pepper
- 1/4 cup olive oil (to be emulsified with starchy pasta water)
- Basil leaves, for garnish
- 1/2 store-bought garlic bread (save other half for Pizza)
- 1 cup shredded dairy-free mozzarella-style cheese
- 1/2 teaspoon Italian seasoning mix

**Revised instructions**
1. Bring large pot of salted water to a boil over high heat. Cook pasta according to package directions.
2. In a large deep skillet over medium-high heat, add olive oil. Add onion, garlic, Italian seasoning mix and red pepper flakes, if using. Stir frequently and cook until the onions are soft and fragrant, about 3 to 4 minutes. Add sausage and cook for 1 minute. Add can of diced tomatoes, stirring all the ingredients together to combine. Season with kosher salt and freshly ground black pepper, to taste and let simmer for 10 minutes. Reserve 1/2 cup pasta water before draining the pasta. Stir in 1/4 cup olive oil and a few tablespoons of the reserved pasta water to create a creamy emulsion, and mix well.
3. Drain the pasta and add directly to the skillet with the sauce Toss the pasta to coat with the sauce. Transfer to a serving bowl or platter and garnish with basil leaves. Serve with the cheesy garlic bread.
4. For the cheesy garlic bread:
5. Preheat oven to 400 degrees F.
6. Sprinkle dairy-free shredded mozzarella-style cheese and Italian seasoning over garlic bread half. Place on tinfoil lined baking sheet and cook in the oven for 10 to 12 minutes, until the cheese is melted and bread is warmed through. Slice and serve.
7. Use the leftover garlic bread from this recipe to make Garlic Bread Pizza.

**What will probably change** _(prediction - not tested, and not stated in the dataset)_
- The sauce will be lighter and less rich than with heavy cream, offering a subtle olive oil flavor and a slightly thinner, but still velvety, texture thanks to the starch from the pasta water.
- The dairy‑free cheese will melt, though it may be less stretchy and have a milder flavor than traditional mozzarella, giving the garlic bread a slightly different mouthfeel.
- Overall the dish remains savory and comforting, with a hint of olive richness replacing the dairy creaminess.
- ⚠️ Olive oil and pasta water may not fully replicate the thickness of heavy cream; the sauce could be a bit thinner or oilier if too much oil is used.
- ⚠️ Dairy‑free mozzarella may not melt as uniformly, resulting in less gooey cheese on the garlic bread.
- ⚠️ Be sure to reserve pasta water before draining, otherwise you won’t have the starchy liquid needed for emulsifying the sauce.

_Safety note: I checked the new ingredient list against my keyword lists for your restrictions and found nothing, but that is not a medical guarantee. Always check packaged ingredient labels for allergens._

**Checks:** ✅ all passed

---
