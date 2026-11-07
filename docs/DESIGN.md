# Design notes

These are the decisions behind RecipeBot and the reasons for them. The short version: **the LLM
handles language, the code handles facts.**

---

## 1. Overall architecture

```
user message
   │
   ▼
LLM router (Groq, JSON mode, temperature 0)
   │   → {"intent": "search", "search": {"query": null}, "constraints": {"add_exclude": ["dairy"]}}
   ▼
Session state  ── active restrictions, step limit, current query, pantry, last results, recipe in focus
   │
   ▼
Deterministic tool ── search.py | analytics.py | matching.py | substitution.py
   │
   ▼
Markdown answer built from the actual records (titles, IDs, ingredient lines, computed numbers)
```

I picked this split because each kind of mistake has one place to look. If the bot misunderstood
the question, the router JSON shows it (it's displayed in the UI). If the numbers or filters are
wrong, that's a bug in deterministic code, which the evaluation can test directly.

The LLM is used in exactly two places:

| Where | Why an LLM | What stops it from making things up |
|---|---|---|
| **Router** (`llm.route`) | Turning free text into a structured request is what LLMs are good at, and rules would be brittle ("I can't do dairy", "lose the eggs too"). | It only outputs a plan. It never sees or produces recipe facts or numbers. |
| **Rewriter** (`llm.rewrite_recipe`, Task 3 only) | Rewriting a method so it reads naturally after a swap. | The substitute is already chosen from evidence. The rewrite is re-checked against the user's restrictions, and it falls back to a rule-based rewrite if it fails. |

Everything else (search ranking, filters, counts, rankings, matching scores, choosing a substitute)
is ordinary Python.

## 2. Data loading

* **All three files** are loaded (`data.py`). 125,164 raw records → 122,931 usable ones. A record is
  dropped only if it is null, or has no title, no ingredients, or no instructions. Keeping empty
  shells would quietly change every percentage. The count of dropped records is shown in every
  statistics answer.
* **Stable ID** = `<source>_<original key>`. The key is the hash the dataset author already uses, so
  IDs don't depend on load order or machine. The prefix (`ar`/`epi`/`fn`) tells you the site.
* **Originals are preserved.** `ingredients_raw` and `instructions` are exactly what's in the JSON.
  The display version of the ingredients only removes the `ADVERTISEMENT` token, which is scraper
  junk on every Allrecipes line, not recipe content.

### Step-counting rule

> One step = one non-empty line of the original instructions, after removing boilerplate lines
> ("Watch how to make this recipe.") and exact duplicate lines.

I chose this over sentence splitting because line breaks are how the original authors grouped the
work. A sentence like "Season with salt and pepper." isn't really a step of its own. Two data
quirks drove the rule:

* About **7,100 Epicurious recipes repeat their whole method twice**, which is a scraping artefact.
  Without de-duplication they'd look twice as long.
* About **8,400 Food Network recipes start with "Watch how to make this recipe."**

The known downside: about 10k Food Network recipes put the whole method in one paragraph, so they
count as 1 step. Every ranking answer states the rule so the user can judge.

### Ingredient count rule

> Number of distinct ingredient lines, ignoring section headers ("For the sauce:") and scraper artefacts.

## 3. Ingredient normalisation (`normalize.py`)

This is the most important part. Matching, filtering and counting all depend on it. Every
ingredient line goes through:

1. **Clean**: drop `ADVERTISEMENT`, convert unicode fractions (½ → 1/2), lower-case.
2. **Strip quantity and unit**: `2 (10.75 ounce) cans …` → `…`. Parenthesised notes go first, then
   leading numbers/ranges, then a unit word (cup, tbsp, can, clove, package…).
3. **Pick the right comma segment**: `skinless, boneless chicken breast halves`. The first segment
   ("skinless") is only a descriptor, so the next one is used.
4. **Remove descriptor words** (chopped, fresh, large, softened…). "ground" is kept for meat
   (*ground beef*) but dropped for spices (*ground cumin* → *cumin*).
5. **Singularise** the head word (*tomatoes* → *tomato*).
6. **Synonyms** (hand-written, about 150): *scallion → green onion*, *all-purpose flour → flour*,
   *kosher salt → salt*, *heavy whipping cream → heavy cream*…

That gives a **canonical name**. On top of that there are two kinds of grouping.

**Families (varieties of the same thing):** *red/yellow/vidalia onion → onion*,
*cherry/roma/plum tomato → tomato*, *egg yolk/egg white → egg*, *basmati/jasmine rice → rice*.
These are listed explicitly in `FAMILIES`.

**Ends-with matching with a blocklist:** when you ask for "chocolate", any name ending in
"chocolate" counts (*bittersweet chocolate*, *semisweet chocolate*), **except** names on a
`DIFFERENT_PRODUCTS` list: *sweet potato* is not potato, *peanut butter* is not butter,
*coconut milk* is not milk, *garlic powder* is not garlic, *green onion* is not onion.

This is the "normalise where justified, keep forms apart when it matters" requirement. The rule is
written down, and every statistics answer prints the names that were merged (e.g. "names counted:
onion, red onion, sweet onion…"), so the user can see exactly what was counted.

I considered using the LLM or embeddings for normalisation. I rejected both, because results would
change between runs and couldn't be explained line by line. A hand-written list can be read in a
code review, and anyone can argue with a specific entry.

### "Strict" vs "loose" counts

For counting questions the bot reports the strict (normalised) number as the answer. It also shows
the loose number ("any ingredient line mentioning the word", which also catches garlic powder,
onion soup mix and so on). For garlic AND onion: strict 15,974 (12.99%) vs loose 20,244. The gap
matters, and hiding it would make the answer look more certain than it is.

### Allergen / diet categories

Each ingredient line is checked against keyword lists for dairy, egg, peanut, tree nuts, gluten,
meat, fish, shellfish, pork, alcohol, soy and honey. There's also an **exception list** that is
removed before matching (*peanut butter*, *coconut milk*, *cream of tartar* aren't dairy; *eggplant*
isn't egg; *nutmeg* isn't a nut). Diet words map onto categories: *vegan* → meat + fish + shellfish
+ dairy + egg + honey; *vegetarian* → meat + fish + shellfish; and so on.

These checks run on the **whole cleaned line**, not just the canonical name. For safety filters, a
false alarm (dropping a recipe that was actually fine) costs far less than a miss, so the lists are
deliberately broad. ("chopped nuts" counts as tree nuts even if they might be peanuts.)

## 4. Retrieval (`search.py`)

1. **Hard filters first, over the whole dataset.** Include/exclude/step limits become a boolean
   mask over all 122,931 recipes, built from an inverted index (ingredient → recipe rows) and
   precomputed category masks. This means a restriction can never be lost because the right recipe
   was outside a top-k list. It's also what the PDF asks for: aggregates use the complete filtered
   set.
2. **Rank what's left** with TF-IDF cosine similarity: 70% title, 30% normalised ingredient names
   (unigrams and bigrams, scikit-learn).
3. **Coverage re-rank**: the top 500 are re-scored by `similarity × (share of query words present)²`.
   I added this after finding that "creamy penne" returned "Creamy Cocoaccino" (a drink) first,
   because a two-word title gets a very high cosine score from one matching word.
4. If no result contains all the query words, the answer says so explicitly. Partial matches are
   labelled as partial, never passed off as matches.

**Why not embeddings / FAISS?** I considered them. For this data, the questions are mostly about
dish names and ingredients, where lexical matching is precise and explainable. Embeddings would
add a large model download (torch), several minutes of indexing on CPU, and less predictable
results ("penne" and "rigatoni" being near each other is helpful sometimes and wrong at other
times). The LLM router already turns vague requests into keywords. If I had more time, I'd add an
optional embedding re-ranker for purely conceptual queries.

## 5. Computation (`analytics.py`)

Supported metrics: `count` (with % of dataset), `top_ingredients`, `ingredient_count_stats`,
`step_count_stats`, `rank_by_steps`, `rank_by_ingredients`. Any of them can be filtered by
ingredients, exclusions, title words, step limit or source, and some can be grouped by source.

Every answer ends with a **"How this was computed"** block:

* dataset size and how many records were excluded as incomplete,
* every filter applied,
* number of recipes analysed,
* the exact calculation and the counting rule used.

Rankings break ties deterministically (by the other count, then by ID). When there are many ties at
the cut-off (e.g. 1,700+ tomato recipes with 1 step), the answer says so instead of pretending the
top 5 are uniquely the "fewest".

## 6. Ranking for ingredient matching (`matching.py`)

**Lexicographic ranking**, not a weighted score:

1. how many of *your* ingredients the recipe uses (more first),
2. how many extra ingredients you'd need (fewer first; salt, pepper and water count as staples),
3. number of steps (fewer first),
4. recipe ID (only to make ties reproducible).

The user can flip the priority ("fewest missing first" / "fewest steps first"). I avoided a
weighted score (e.g. `0.6·coverage − 0.3·missing …`) because the weights would be arbitrary, and
"why is #3 below #2?" wouldn't have a clean answer. Here, each result comes with a one-line reason:
*"below the previous one because it needs more extra ingredients"*.

How "missing" is interpreted: the PDF lists matched / missing / extra-required ingredients. The
answer shows **Uses** (your ingredients the recipe uses), **Missing** (what the recipe needs that
you don't have, i.e. the extra required ingredients) and **Not used** (your ingredients it doesn't
use).

**Hard constraints are never relaxed silently.** They are applied before ranking. If nothing is
left, the answer says "No match found… I have not relaxed any of them". It then shows the closest
recipes under a separate heading, each labelled with the exact rule it breaks (*"contains dairy
('1/2 cup milk'); uses only 2/3 of your ingredients"*). If the user's own pantry item conflicts
with an exclusion ("exclude eggs too"), it's removed from the pantry with a note.

**Quantities:** parsed from both sides ("2 cups rice" vs "1 cup instant rice") and compared only
when units are in the same dimension (volume vs volume, mass vs mass, count vs count). Otherwise
the answer says sufficiency was **not verified**. It also refuses to compare raw rice against
*cooked* rice.

## 7. Substitution evidence (`substitution.py`)

Order of evidence:

1. **Find the dish neighbourhood.** Recipes most similar to this one (60% title + 40% ingredient
   TF-IDF similarity) are split into those **with** and **without** the ingredient being removed.
2. **Test candidates.** For each candidate substitute from a small role table (e.g. egg →
   applesauce, banana, yogurt, flaxseed…), measure how often it appears in the "without" group vs
   the "with" group.
3. **Only count it as evidence if it's more common without the target.** This rule came from a
   failed first version, which suggested *olive oil* as a cream replacement only because olive
   oil is in almost every pasta recipe. Now each candidate is labelled:
   * `direct`: 3+ similar recipes use it without the target, and it's over-represented there
     (only possible if at least 3 similar recipes *do* use the target, otherwise there's nothing
     to compare against and the best rating is `limited`),
   * `limited`: 1–2 such recipes,
   * `co-occurs only`: present, but just as common when the target is used (not evidence),
   * `indirect`: only used without the target in other kinds of dishes,
   * `none`.
4. **Cite IDs with the actual ingredient line** (e.g. `fn_p174… — Vegan Banana Bread: uses
   '1/2 cup plain soy milk yogurt'`), so amounts come from real recipes.
5. **Restrictions are applied to candidates** (yogurt is rejected under "no dairy"). They are also
   applied to the **rest of the recipe**: if the user says "no dairy" and the recipe also has
   parmesan, that is flagged with 🚫 rather than hidden.
6. **Rewrite**: the LLM rewrites the ingredient list and steps with the chosen swap. The result is
   independently re-checked against the restrictions. If it fails, a simple rule-based rewrite is
   used instead and the user is told.

The **role** of an ingredient (binding, moisture, richness…) and the **amount guidance** ("about
1/4 cup applesauce per egg") come from general cooking knowledge, not the dataset. They are always
labelled as such. Predicted effects on taste and texture are labelled as predictions. If no
candidate has any support, the bot says it can't support a reliable adaptation.

## 8. Uncertainty — how it's communicated

| Situation | What the bot does |
|---|---|
| Asked for calories / nutrition / cost / servings | Says the dataset doesn't contain it; no estimate |
| Asked for cooking time | Says there is no time field, but lists durations written in the steps, labelled as "individual steps, not a verified total" |
| No recipe meets the constraints | Says "no match", names which constraint removes everything, shows alternatives only as labelled violations |
| Only partial text matches | Labels them as partial with the share of query words found |
| Ambiguous ingredient matching | Shows strict and loose counts side by side |
| Substitution evidence is thin or absent | `limited` / `weak evidence` / "can't support a reliable adaptation" |
| A rewrite still violates a restriction | 🚫 banner listing the offending lines |
| Allergens in general | "Keyword check, not a medical guarantee; check labels" |

## 9. External search

**Not used.** The PDF allows optional internet search as a secondary source for substitutions. I
decided against it for two reasons:

* Everything the bot shows can be traced back to a recipe ID and re-checked offline. That's also
  what makes the evaluation reproducible.
* When local evidence is weak, the PDF allows *either* stating the uncertainty *or* searching. I
  chose to state the uncertainty, and to label the role table as general cooking knowledge.

If I added it, the plan would be a separate "External sources" block with links, shown only when
local evidence is `indirect` or `none`, and never mixed into the dataset evidence table.

## 10. Session state & follow-ups

`SessionState` (in `agent.py`) holds the active query, required ingredients, **restrictions**, the
step limit, the pantry, the last results and the recipe in focus. The router gets a text summary of
this state with each message and returns *changes* (`add_exclude`, `remove_exclude`, `query: null`
to keep the current one). That's what makes "I cannot have dairy" refine the penne search, and
"Exclude eggs too" add to the earlier no-peanuts constraint instead of replacing it. Restrictions
stay active across search, matching and substitution until the user changes them or says "start
over".

References like "the second one", "this recipe" and "that banana bread" are resolved against the
last results first. A fuzzy title match is used only as a last resort, and the bot then says which
recipe it picked.
