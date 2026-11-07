# C1_search_followups
**Task 1 - search + multi-turn refinement**

_Why this test:_ PDF example: a newly stated restriction must refine the active search, with evidence from ingredient lists.

## Turn 1
**User:** Find a penne pasta recipe

<details><summary>Router plan (LLM output)</summary>

```json
{
  "intent": "search",
  "search": {
    "query": "penne pasta",
    "add_include": [],
    "remove_include": [],
    "new_search": true
  }
}
```
</details>

**Bot:**

🔎 **Search:** penne pasta · **Active constraints:** none
3,275 recipes pass every constraint and share words with the query. Showing 1–5:

**1. Creamy Penne Pasta** — `ar_nvQzTEX.J7/2LmKnF8KjsR6aCqNHGxO` · Allrecipes · 2 steps · 9 ingredients
**2. Bacon and Parmesan Penne Pasta** — `ar_hzvAPQudIHjif5vLsP8vv.H8aTThvAq` · Allrecipes · 3 steps · 5 ingredients
**3. Drunken Penne Pasta** — `fn_6Vi.RvXGd.fVPiUz10UWjlpt.bzgnXW` · Food Network · 2 steps · 12 ingredients
**4. Penne Pasta with Alex Guarnaschelli** — `fn_eEH8/TD4MHNzhQpPyxH6yUiw1olBZZW` · Food Network · 6 steps · 13 ingredients
**5. Creamy Ham and Penne Pasta** — `fn_4tITdgG7jS.lgVlCCxBlTiiLq9JCj2G` · Food Network · 2 steps · 6 ingredients

Say *show 2* for the full recipe, *more* for more results, or add a restriction.

**Checks:** ✅ all passed

---

## Turn 2
**User:** I cannot have dairy

<details><summary>Router plan (LLM output)</summary>

```json
{
  "intent": "search",
  "constraints": {
    "add_exclude": [
      "dairy"
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

🔎 **Search:** penne pasta · **Active constraints:** excluding dairy
717 recipes pass every constraint and share words with the query. Showing 1–5:

**1. Penne Pasta with Cannellini Beans and Escarole** — `ar_zwRAInNlhnKD1jMf/HOm5a9oKhjC8Om` · Allrecipes · 2 steps · 5 ingredients
   - ✅ no dairy found in its 5 ingredient lines: _1 (16 ounce) package dry penne pasta; 1 head escarole, chopped; 1 (15.5 ounce) can cannellini beans, with liquid; 1 (14.5 ounce) can diced tomatoes with garlic and onion, drained; salt and ground black pepper to taste_
**2. Penne Pasta with Spinach and Bacon** — `ar_23to8XzUux0FF.g5ZFsqnxvhByMzfJ.` · Allrecipes · 3 steps · 6 ingredients
   - ✅ no dairy found in its 6 ingredient lines: _1 (12 ounce) package penne pasta; 2 tablespoons olive oil, divided; 6 slices bacon, chopped; 2 tablespoons minced garlic; 1 (14.5 ounce) can diced tomatoes; 1 bunch fresh spinach, rinsed and torn into bite-size pieces_
**3. Scallops and Penne Pasta in a Saffron Broth** — `fn_3xGSq4jxwkdB1cabVkvXBRVHv7OxflC` · Food Network · 1 step · 11 ingredients
   - ✅ no dairy found in its 11 ingredient lines: _1/2 pound sea scallops, sliced into rounds; 1/2 pound shrimp, peeled and deveined; 2 tablespoons olive oil; 2 cloves garlic, minced; 1/4 cup dry white wine; 1 cup fish stock; 1 cup clam juice; 14-ounce can crushed tomatoes (about 2 cups); 4 carrots, peeled and sliced; 1/4 to 1/2 teaspoon crumbled saffron; 1/4 teaspoon dried orange peel_
**4. Penne Pasta Salad with Sun Dried Tomatoes, Asparagus and Basil** — `fn_ck/foCIv1g.W0SyPMLF5DWS/ZdeQBRi` · Food Network · 2 steps · 7 ingredients
   - ✅ no dairy found in its 7 ingredient lines: _1 pound penne pasta; 1 cup fresh asparagus tips; 4 garlic cloves, minced; 1/4 cup olive oil; Salt and pepper, to taste; 1 bunch basil, chopped; 1 cup sun-dried tomatoes in oil_
**5. Italian Sausage Penne Pasta with Tomatoes and Peas and Sweet Corn Salad** — `fn_Fa0AuDYa4SItG.bL1kA8votemAaTPZ6` · Food Network · 2 steps · 12 ingredients
   - ✅ no dairy found in its 12 ingredient lines: _2 pounds sweet Italian sausage, roughly chopped; 3/4 cups olive oil, divided; 1 1/2 cups onion, diced and divided; 1 tablespoon dried oregano, crushed; 2 tablespoons garlic, chopped; 6 cups plus 6 whole tomatoes, chopped; 1/4 cup parsley, chopped; 1 cup basil, julienned and divided; 2 cups frozen peas; 2 pounds penne pasta; 3 ears corn, blanched; Salt and pepper_

Say *show 2* for the full recipe, *more* for more results, or add a restriction.

**Checks:** ✅ all passed

---

## Turn 3
**User:** Show me the ingredients and instructions for the second one

<details><summary>Router plan (LLM output)</summary>

```json
{
  "intent": "show_recipe",
  "show": {
    "ref": "2"
  }
}
```
</details>

**Bot:**

### Penne Pasta with Spinach and Bacon
`ar_23to8XzUux0FF.g5ZFsqnxvhByMzfJ.` · Allrecipes · 6 ingredients · 3 steps

**Ingredients** (as in the dataset)
- 1 (12 ounce) package penne pasta
- 2 tablespoons olive oil, divided
- 6 slices bacon, chopped
- 2 tablespoons minced garlic
- 1 (14.5 ounce) can diced tomatoes
- 1 bunch fresh spinach, rinsed and torn into bite-size pieces

**Instructions** (as in the dataset)
1. Bring a large pot of lightly salted water to a boil. Add the penne pasta, and cook until tender, 8 to 10 minutes.
2. Meanwhile, heat 1 tablespoon of olive oil in a skillet over medium heat. Place bacon in the skillet, and cook until browned and crisp. Add garlic, and cook for about 1 minute. Stir in the tomatoes, and cook until heated through.
3. Place the spinach into a colander, and drain the hot pasta over it so it is wilted. Transfer to a large serving bowl, and toss with the remaining olive oil, and the bacon and tomato mixture.

_The dataset has no nutrition, servings or total cooking time for recipes._

**Checks:** ✅ all passed

---

## Turn 4
**User:** How many calories does that have?

<details><summary>Router plan (LLM output)</summary>

```json
{
  "intent": "unsupported",
  "unsupported": {
    "missing": "calories"
  }
}
```
</details>

**Bot:**

The Recipe Box dataset doesn't contain **calories** — each recipe only has a title, an ingredient list and instructions. I'd rather say that than make up a number.

**Checks:** ✅ all passed

---
