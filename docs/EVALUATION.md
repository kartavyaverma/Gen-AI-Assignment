# Evaluation

To reproduce:

```bash
uv run pytest
uv run python eval/run_eval.py --offline
uv run python eval/run_eval.py
```

`pytest` runs 9 unit tests that don't need the data. `--offline` runs only part A below, which
needs the data but no API key. The last command runs everything and needs the Groq key. The full
output is in [eval/results.md](../eval/results.md), and every test conversation (including the
JSON the router produced for each message) is in [eval/transcripts/](../eval/transcripts/).

## What's in the evaluation

There are three parts.

**Part A: tool checks (11 checks, no LLM).** These call the search, statistics, matching and
substitution code directly. Where possible the bot's result is compared against a separate
calculation done in the test itself, rather than against a number I typed in by hand.

| ID | What it checks |
|---|---|
| A1 | ingredient cleanup edge cases: peanut butter isn't dairy, coconut milk isn't dairy, eggplant isn't egg, garlic powder isn't garlic |
| A2 | the step rule removes the duplicated Epicurious instructions |
| A3 | the garlic and onion count matches a separate numpy count, and the percentage uses the full dataset |
| A4 | "fewest steps among tomato recipes" is sorted and starts at the real minimum |
| A5 | the "no dairy" filter lets zero dairy recipes through, across the whole dataset |
| A6 | the pantry example from the assignment: no peanuts, at most 6 steps, ranked by ingredients used |
| A7 | "exclude eggs too" removes eggs from the pantry and from the results |
| A8 | an impossible request gives "No match found", with alternatives marked as breaking the rules |
| A9 | egg-free banana bread: the cited recipes really are egg-free, and banana isn't treated as evidence |
| A10 | a dairy-free cream swap never picks a dairy substitute, and leftover dairy lines are pointed out |
| A11 | asking to replace an ingredient the recipe doesn't have is refused |

**Part B: 7 conversations, 19 messages in total.** These go through the whole bot, LLM included.
Each message has automatic checks (right intent, restrictions remembered, results actually obey
the filters, numbers match a direct calculation, and so on).

| Conversation | What it covers |
|---|---|
| C1 | task 1 follow-ups: penne, then "I cannot have dairy", then "show the second one", then a calories question |
| C2 | task 1 statistics: garlic and onion count and percentage, the five fewest-step tomato recipes, average and median ingredients by source |
| C3 | task 2: the pantry request from the assignment, then "Exclude eggs too", then "rank by fewest steps instead" |
| C4 | no-match cases: an impossible pantry request, and a beef stew search followed by "I'm vegan" |
| C5 | task 3: remove eggs from banana bread using only dataset ingredients |
| C6 | task 3: replace cream in a pasta without dairy (weak evidence, plus other dairy in the recipe) |
| C7 | a question the data can't answer (lowest-calorie lasagna), then starting over |

**Part C: plain LLM for comparison.** The same Groq model is asked four similar questions without
any of my code, and the answers are checked.

## Results

### Part A: 11 of 11 passed

| ID | Result |
|---|---|
| A1 | all cleanup cases correct |
| A2 | 7,129 Epicurious recipes had duplicated instructions, now counted once |
| A3 | 15,974 recipes (12.99% of 122,931), same as the separate count. The loose count is 20,244 |
| A4 | the five results have 1 step each, which is the real minimum across 13,781 tomato recipes |
| A5 | 717 penne recipes without dairy, no dairy recipes let through |
| A6 | all top five use 4 of 4 ingredients, with 5, 3, 2, 3 and 3 steps |
| A7 | pantry becomes onion, tomato, rice, and no result contains egg |
| A8 | "No match found" shown, alternatives listed separately and marked |
| A9 | best substitute is yogurt with limited evidence; both cited recipes are egg-free; banana marked "co-occurs only" |
| A10 | best substitute is broth thickened with cornstarch; the leftover parmesan line is flagged |
| A11 | refused |

### Part B: 19 of 19 messages passed

Model: `openai/gpt-oss-120b` on Groq, temperature 0. The first full run only passed 15 of 19, and
later runs turned up two more problems. All of them were real bugs, and they're listed in the
table further down.

| Conversation | Passed | Notes |
|---|---|---|
| [C1](../eval/transcripts/C1_search_followups.md) | 4/4 | "I cannot have dairy" kept the penne search and added the restriction. The calories question was answered with "the dataset doesn't contain that" |
| [C2](../eval/transcripts/C2_aggregate_stats.md) | 3/3 | count, ranking and average all matched a direct calculation |
| [C3](../eval/transcripts/C3_pantry_matching.md) | 3/3 | "Exclude eggs too" kept the earlier no-peanuts and 6-step limits |
| [C4](../eval/transcripts/C4_no_match.md) | 3/3 | the impossible pantry request got an explicit no-match. "Beef stew" plus vegan found no full match and the partial ones were labelled |
| [C5](../eval/transcripts/C5_substitution_eggs.md) | 2/2 | cited egg-free recipes; banana marked as "co-occurs only" |
| [C6](../eval/transcripts/C6_substitution_dairy_weak.md) | 2/2 | evidence capped at "limited"; the mozzarella in the recipe was pointed out and swapped |
| [C7](../eval/transcripts/C7_unsupported_and_reset.md) | 2/2 | no calorie numbers made up |

### Part C: plain LLM vs. RecipeBot

| Question | Plain LLM | RecipeBot |
|---|---|---|
| How many recipes contain garlic and onion, and what percentage? | No number, just Python code to run yourself. The code assumes files like `allrecipes.jsonl` and `recipe_index.csv`, which don't exist in this dataset | 15,974 recipes, 12.99% of 122,931 (20,244 with the loose rule) |
| The five tomato recipes with the fewest steps, with IDs | Said it can't access the data, no IDs | Five real IDs with 1 step each, plus a note that 2,059 recipes tie |
| Five recipes for eggs, onions, tomatoes and rice, no peanuts, at most 6 steps | Said it can't access the data | Five real recipes using all four ingredients, 2 to 5 steps |
| Calories per slice and total time for the Allrecipes banana bread | "≈ 210 kcal" and "1 hour 15 minutes", presented as "as listed in the dataset", with a made-up `total_time` field | Says the dataset has no calorie or time data, and only lists times mentioned in the steps |

This turned out differently from what I expected. The model is fairly careful when it obviously
can't see the data, so for counting questions you get no answer rather than a wrong one. That
still doesn't help the user. When a question sounds like something the dataset might contain, like
the calories of a well-known recipe, it made up the numbers and claimed they came from the
dataset. It even described fields that don't exist. That's the kind of answer this project is
meant to prevent.

## What worked

- **Numbers you can check.** Every count, percentage and ranking can be reproduced and matches a
  separate calculation (A3, A4). Answers list the filters, how many recipes were analysed, and the
  rule used.
- **Filtering before ranking.** Since restrictions are applied to the whole dataset before anything
  is ranked, "no dairy" lets nothing through (A5), and follow-up restrictions don't get lost.
- **Not bending the rules.** Impossible requests get a clear "no match", and anything shown as an
  alternative says exactly which rule it breaks (A8).
- **Honest substitution evidence.** Comparing recipes with and without the ingredient stops the bot
  from treating "it's always there" as evidence. Banana appears in 96% of banana breads that use
  eggs, so egg-free banana breads containing banana don't prove anything (A9).

## What went wrong and what I changed

I found all of these by running the bot and looking at the answers.

| Problem | Cause | Fix |
|---|---|---|
| "creamy penne" returned Creamy Cocoaccino, a drink, as the top result | TF-IDF gives short titles a high score from one matching word | re-rank by how many of the query words the recipe contains |
| olive oil came out as the best cream substitute for pasta | counting "similar recipes without cream that use X" favours ingredients that are everywhere | only count a candidate if it's more common in recipes without the ingredient than with it |
| coconut cream scored zero as a cream substitute | "cream" was matched as plain text, so coconut cream recipes counted as containing cream | match on the cleaned ingredient names, where coconut cream is its own product |
| a "no dairy" adaptation still had half-and-half in it | only the requested line was swapped, the rest wasn't checked | check the whole rewritten recipe against the restrictions and warn about anything left |
| peanut butter stayed in the pantry after "no peanuts" | pantry items were only compared with exclusions by exact name | check pantry items against the exclusion categories and remove them, with a note |
| "chocolate" only matched 690 recipes | strict matching missed bittersweet chocolate, semisweet chocolate and so on | ends-with matching plus a list of exceptions; now 3,737 |
| "quinoa chocolate lasagna" showed plain quinoa as if it matched | the best partial match was shown as a normal answer | partial matches are labelled and the answer says nothing matched fully |
| "I'm vegan" was stored as only dairy, egg and meat | the router expanded "vegan" itself and left out fish, shellfish and honey | the router passes diet words through unchanged and the code applies the definition. A good reminder not to let the LLM handle rules |
| "replace the cream" said the recipe had no heavy cream | the line was "heavy whipping cream" and lines were matched as raw text | match lines on cleaned names (heavy whipping cream is heavy cream) everywhere |
| "I have lobster, mango and dark chocolate…" was run as a search | the router picked the wrong intent | router rule: "I have …" always means pantry matching, and "uses all three" sets `must_use_all` |
| "rank them by fewest steps instead" became a statistics question | the router lost track of the pantry conversation | router rule: after a pantry match, ranking changes stay in pantry matching |
| "Forget that. Find me a beef stew." cleared the chat and ignored the search | the model read "forget that" as the whole request | router rule: only start over if nothing else is asked |
| "Find a penne pasta recipe" searched for "penen pasta" | the router made a typo when copying the dish name | router told to copy words exactly, plus a check in `agent.py` that swaps any search word the user didn't type for the closest word they did |
| olive oil was rated "direct" evidence again, for a pasta whose similar recipes had no cream at all | with no recipes using cream, there was nothing to compare against | if fewer than 3 similar recipes use the ingredient, evidence is capped at "limited" with a warning |
| the LLM's "dairy-free mozzarella-style cheese" failed the dairy check | the word "cheese" matched | products explicitly labelled dairy-free, vegan or plant-based are allowed, but only that product |

## Known limitations

- **Ingredient cleanup isn't perfect.** Some unusual lines end up with names like "juice", "greens"
  or "vegetable", which then appear in the "Missing" lists. A bigger synonym list or a proper
  ingredient parser would help.
- **Recipes can leave things out.** For example `fn_3xGSq4…` (Scallops and Penne Pasta) doesn't
  list penne in its ingredients, so it isn't flagged as containing gluten. The filters only know
  what the recipe lists.
- **Hidden allergens in products.** Things like semisweet chocolate or some sauces can contain
  allergens the ingredient line doesn't mention. That's why the bot never says something is safe.
- **Step counts depend on formatting.** Around 11,000 Food Network recipes are one paragraph and
  count as one step, so they show up a lot in "fewest steps" rankings. The answer states the rule
  and how many recipes tie.
- **Search is keyword-based.** Vague requests only work as well as the router's translation into
  keywords.
- **The substitution table is small.** It covers egg, cream, butter, milk, sour cream, cheese and
  flour. For anything else, the bot only has the "what do recipes without it use more often"
  signal, and it says the ingredient's role is a guess.
- **"Similar recipes" can be off.** For "Penne with Sausage and Cheesy Garlic Bread", some of the
  cited evidence comes from garlic bread recipes. It's labelled as limited, but a better way of
  grouping dishes would help.
- **The router can still misread things.** The conversation tests catch the cases I know about, and
  "Parsed request" in the app shows what happened, but new phrasings can still be misread.
- **The fallback rewrite is basic.** If the LLM rewrite isn't available or fails the check, the
  simple rule-based version can produce odd steps like "whip the broth". The LLM version is asked
  to point out problems like this.
