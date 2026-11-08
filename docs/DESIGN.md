# Design notes

This is a write-up of how RecipeBot works and why I built it this way. The general rule I followed
was: let the LLM deal with language, and let code deal with facts.

## 1. Architecture

```
user message
   |
   v
LLM router (Groq, JSON mode, temperature 0)
   |   e.g. {"intent": "search", "search": {"query": null}, "constraints": {"add_exclude": ["dairy"]}}
   v
session state (current search, restrictions, step limit, pantry, last results, current recipe)
   |
   v
one of the tools: search.py, analytics.py, matching.py, substitution.py
   |
   v
answer built from the actual recipe records
```

Splitting it like this means that when something goes wrong, it's easy to tell where. If the bot
misread the question, the JSON shows it (it's visible in the app under "Parsed request"). If a
number or a filter is wrong, that's a bug in normal Python code, and the evaluation can test that
directly.

The LLM is only used in two places:

- **The router** (`llm.route`) turns the user's message into a JSON request. Doing this with rules
  would be fragile, because people phrase things in a lot of ways ("I can't do dairy", "lose the
  eggs too"). The router never sees or writes recipe facts or numbers.
- **The rewriter** (`llm.rewrite_recipe`, only for task 3) rewrites the ingredient list and steps
  once a substitute has been picked, so the result reads naturally. The substitute itself is chosen
  by code, and the rewrite gets checked against the user's restrictions afterwards. If the check
  fails, a simple rule-based rewrite is used instead.

Everything else (filters, ranking, counting, matching, choosing substitutes) is plain Python.

## 2. Loading the data

- All three JSON files are loaded in `data.py`. Of 125,164 records, 122,931 are kept. A record is
  only dropped if it's null or is missing its title, ingredients or instructions. Leaving those in
  would quietly change every percentage, so every statistics answer mentions how many were
  dropped.
- IDs are `<source>_<original key>`. The key is the hash the dataset already uses, so IDs don't
  depend on load order. The prefix (`ar`, `epi`, `fn`) shows which site the recipe came from.
- The original text is kept as-is in `ingredients_raw` and `instructions`. For display I only
  remove the "ADVERTISEMENT" word the Allrecipes scraper added to each ingredient line.

### Counting steps

A step is one non-empty line of the original instructions. Boilerplate lines ("Watch how to make
this recipe.") and exact duplicate lines are ignored.

I went with line breaks instead of splitting by sentence, because the line breaks are how the
original authors grouped the work. Something like "Season with salt and pepper." isn't really a
step on its own. Two things in the data shaped the rule:

- About 7,100 Epicurious recipes have their whole method repeated twice (a scraping issue). Without
  removing duplicates they'd look twice as long.
- About 8,400 Food Network recipes start with the line "Watch how to make this recipe."

The downside is that around 11,000 Food Network recipes are written as one paragraph, so they count
as one step. Ranking answers state the rule, so the user can judge for themselves.

### Counting ingredients

The number of distinct ingredient lines, ignoring section headers like "For the sauce:".

## 3. Ingredient normalisation (`normalize.py`)

Almost everything depends on this part, because matching, filtering and counting all need to know
that "2 cups chopped tomatoes" is tomato. Each ingredient line goes through these steps:

1. Clean up: remove "ADVERTISEMENT", turn ½ into 1/2, lower-case.
2. Remove the quantity and unit: anything in brackets, then numbers, then a unit word (cup, tbsp,
   can, clove, package and so on).
3. Pick the right part of the line. In "skinless, boneless chicken breast halves" the first part is
   just a description, so the next part is used.
4. Remove preparation words like chopped, fresh, large or softened. "ground" is kept for meat
   (ground beef) but removed for spices (ground cumin is just cumin).
5. Make the last word singular (tomatoes becomes tomato).
6. Apply a synonym list I wrote by hand (about 180 entries), e.g. scallion to green onion,
   all-purpose flour to flour, heavy whipping cream to heavy cream.

On top of that there are two kinds of grouping:

- **Families** for varieties of the same ingredient: red, yellow and vidalia onions all count as
  onion, cherry and roma tomatoes count as tomato, egg yolk and egg white count as egg. These are
  listed explicitly in `FAMILIES`.
- **Ends-with matching** for everything else. If you search for chocolate, anything ending in
  "chocolate" counts (bittersweet chocolate, semisweet chocolate). There's a `DIFFERENT_PRODUCTS`
  list of exceptions where that would be wrong: sweet potato isn't potato, peanut butter isn't
  butter, coconut milk isn't milk, garlic powder isn't garlic, green onion isn't onion.

This is my answer to the requirement about normalising names where it makes sense but keeping
different products apart. Statistics answers list which names were counted together, so you can
see exactly what was included.

I thought about using the LLM or embeddings for this, but decided against both. The results could
change from run to run, and I wouldn't be able to explain a particular decision. A hand-written
list is easy to read and easy to argue with.

### Strict and loose counts

For counting questions the main answer uses the normalised names. The bot also shows a looser count
(any ingredient line that mentions the word, which picks up things like garlic powder or onion soup
mix). For garlic and onion that's 15,974 recipes (12.99%) versus 20,244. I show both because the
difference is big enough to matter.

### Allergens and diets

Each ingredient line is checked against keyword lists for dairy, egg, peanut, tree nuts, gluten,
meat, fish, shellfish, pork, alcohol, soy and honey. Before checking, known exceptions are removed:
peanut butter, coconut milk and cream of tartar aren't dairy, eggplant isn't egg, nutmeg isn't a
nut. Products explicitly labelled as free of something ("dairy-free mozzarella") are also allowed.
Diet words are mapped to categories: vegan means no meat, fish, shellfish, dairy, egg or honey,
vegetarian means no meat, fish or shellfish, and so on.

The check runs on the whole ingredient line, not just the cleaned name. I made the keyword lists
broad on purpose. Wrongly dropping a recipe that was fine is much less of a problem than missing
an allergen, so "chopped nuts" is treated as tree nuts even if they might be peanuts.

## 4. Search (`search.py`)

1. Filters are applied to all 122,931 recipes first. Required ingredients, exclusions and step
   limits become a true/false array, built from a prebuilt ingredient index and allergen arrays.
   This means a restriction can't get lost just because the right recipe wasn't in a top-10 list,
   and it's also why statistics always use the complete filtered set.
2. What's left is ranked with TF-IDF similarity (scikit-learn): 70% based on the title and 30% on
   the ingredient names.
3. The top 500 are then re-ranked by how many of the query words they actually contain
   (`score × (share of query words found)²`). I added this after "creamy penne" returned a drink
   called "Creamy Cocoaccino" first. Short titles get a high score from a single matching word.
4. If no recipe contains all the words, the answer says so and marks the results as partial
   matches.

Why not embeddings or FAISS? Most questions here are about dish names and ingredients, where exact
word matching works well and is easy to explain. Embeddings would mean a big model download, a few
minutes of indexing on a CPU, and less predictable results. The router already turns vague
requests into keywords. If I had more time, I'd add embeddings as an optional second stage for
vague queries.

## 5. Statistics (`analytics.py`)

Supported questions: counts (with percentage of the dataset), most common ingredients, average
and median ingredient or step counts, and rankings by number of steps or ingredients. All of them
can be filtered by ingredients, exclusions, title words, step limit or source, and some can be
split by source.

Every answer ends with a "How this was computed" section listing the dataset size, how many
records were dropped, the filters, how many recipes were analysed, and the exact calculation.

Ties in rankings are broken by the other count and then by ID, so results are reproducible. If a
lot of recipes tie at the cutoff (2,059 tomato recipes have exactly one step), the answer says so
rather than pretending the top five are the only ones.

## 6. Ranking for ingredient matching (`matching.py`)

Results are sorted by a fixed order instead of a weighted score:

1. how many of your ingredients the recipe uses (more is better)
2. how many extra ingredients you'd need (fewer is better; salt, pepper and water don't count)
3. number of steps (fewer is better)
4. recipe ID, only to make ties consistent

The user can change the priority ("fewest missing first", "fewest steps first"). I didn't use a
weighted score because I'd have had to make up the weights, and then there's no simple answer to
"why is #3 below #2?". With a fixed order, each result gets a one-line reason, e.g. "below the
previous one because it needs more extra ingredients".

The assignment mentions matched, missing and extra required ingredients. In the answers, **Uses**
is your ingredients that the recipe uses, **Missing** is what the recipe needs that you don't have
(the extra required ingredients), and **Not used** is your ingredients that the recipe doesn't
need.

Hard constraints are applied before ranking and never loosened. If nothing passes, the answer says
"No match found" and that nothing was relaxed. Only after that does it show the closest recipes,
each marked with the rule it breaks ("contains dairy ('1/2 cup milk'); uses only 2/3 of your
ingredients"). If one of your own ingredients conflicts with an exclusion (you have eggs but said
"exclude eggs"), it's removed from your list and the answer mentions it.

Quantities are compared only when both sides use the same kind of unit (volume with volume, weight
with weight, count with count). Otherwise the answer says the amount wasn't checked. It also won't
compare raw rice against cooked rice.

## 7. Substitutions (`substitution.py`)

This is how a substitute gets picked:

1. Find recipes similar to the one being changed (60% title similarity, 40% ingredient similarity)
   and split them into the ones that use the ingredient and the ones that don't.
2. For each candidate from a small table of common swaps (for egg: applesauce, banana, yogurt,
   flaxseed and so on), check how often it appears in each group.
3. Only count a candidate as evidence if it's clearly more common in the recipes without the
   ingredient. My first version didn't do this and suggested olive oil as a cream substitute in
   pasta, just because olive oil is in nearly every pasta recipe. The labels are:
   - `direct`: at least 3 similar recipes use it instead, and it's more common there. This needs
     at least 3 similar recipes that do use the ingredient, otherwise there's nothing to compare
     against and the best possible label is `limited`.
   - `limited`: only 1 or 2 such recipes.
   - `co-occurs only`: it's there, but just as common in recipes that keep the ingredient, so it
     doesn't tell us anything.
   - `indirect`: only used this way in other kinds of dishes.
   - `none`.
4. Supporting recipes are cited by ID, together with the exact ingredient line they use, so the
   amounts come from real recipes.
5. The user's restrictions are checked against the candidates (no yogurt if they said no dairy) and
   against the rest of the recipe. If the recipe has other ingredients that break the restriction,
   like parmesan in a "no dairy" request, the answer points them out.
6. The LLM rewrites the recipe with the chosen swap. The result is checked again, and if anything
   forbidden is still in it, the user is told.

The role of an ingredient (binding, moisture, richness) and the amount guidance ("about 1/4 cup
applesauce per egg") come from general cooking knowledge, not from the dataset. The answer labels
them that way. Effects on taste and texture are labelled as predictions. If none of the candidates
have any support, the bot says it can't recommend a reliable change.

## 8. How uncertainty is shown

| Situation | What the bot does |
|---|---|
| Asked about calories, nutrition, cost or servings | Says the dataset doesn't have that information |
| Asked about cooking time | Says there's no time field, but lists any durations mentioned in the steps |
| Nothing meets the constraints | Says there's no match, says which constraint is responsible, and marks any alternatives |
| Only partial text matches | Labels them as partial, with how much of the query they match |
| Ingredient matching could go either way | Shows the strict and loose counts |
| Weak or no evidence for a substitution | Labels it `limited` or weak, or says it can't recommend a change |
| A rewritten recipe still breaks a restriction | Warns and lists the lines |
| Allergens in general | Notes that it's a keyword check, not a guarantee |

## 9. External search

I didn't use it. The assignment allows internet search as a backup for substitutions, but I
decided against it:

- Everything the bot says can be traced back to a recipe ID and checked offline, which also keeps
  the evaluation reproducible.
- When local evidence is weak, the assignment allows either stating the uncertainty or searching
  online. I went with stating the uncertainty, and I label the role table as general knowledge.

If I were to add it, I'd show web results in a separate "External sources" section with links,
only when the local evidence is `indirect` or `none`, and keep it apart from the dataset evidence.

## 10. Conversation state

`SessionState` in `agent.py` keeps track of the current query, required ingredients, restrictions,
step limit, pantry, last results and the recipe being discussed. With every message the router
gets a short summary of this and replies with changes (`add_exclude`, `remove_exclude`, or
`query: null` to keep the current search). That's how "I cannot have dairy" narrows the penne
search, and how "Exclude eggs too" adds to the earlier "no peanuts" instead of replacing it.
Restrictions stay active for search, matching and substitution until the user removes them or
starts over.

References like "the second one", "this recipe" or "that banana bread" are matched against the
last results first. A fuzzy title search is only used as a fallback, and the bot then says which
recipe it picked.

Two small safety nets came out of testing. The router is told to pass diet words like "vegan"
through unchanged, because it once expanded "vegan" itself and left out fish and honey. And if the
router's search words don't appear in the user's message, they're swapped for the closest word the
user actually typed (it once wrote "penen" instead of "penne").
