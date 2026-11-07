# Evaluation report

How to reproduce everything here:

```bash
uv run pytest                              # 9 unit tests (no data or key needed)
uv run python eval/run_eval.py --offline   # Part A only
uv run python eval/run_eval.py             # Parts A + B + C (needs GROQ_API_KEY)
```

The raw output is in [`eval/results.md`](../eval/results.md), and every conversation transcript,
including the router's JSON for each turn, is in [`eval/transcripts/`](../eval/transcripts/).

## What the evaluation set contains

**Part A: deterministic tool checks (11 checks, no LLM).** These test the properties that make
answers trustworthy, and they compare the bot's outputs against **independent recomputation**,
not against numbers I typed in:

| ID | What it checks |
|---|---|
| A1 | Normalisation edge cases: peanut butter ≠ dairy, coconut milk ≠ dairy, eggplant ≠ egg, garlic powder ≠ garlic |
| A2 | Step rule removes duplicated Epicurious methods |
| A3 | "garlic AND onion" count equals a separate numpy computation; percentage uses the full denominator |
| A4 | "fewest steps among tomato recipes" is sorted and starts at the true minimum of the filtered set |
| A5 | "No dairy" filter leaks zero dairy-flagged recipes across the *whole* dataset |
| A6 | PDF pantry example: no peanuts, ≤ 6 steps, ranked by ingredients used |
| A7 | "Exclude eggs too" removes eggs from both the pantry and the results |
| A8 | Impossible request → "No match found", alternatives labelled as violations |
| A9 | Egg-free banana bread: cited recipes really are egg-free; banana is *not* treated as evidence |
| A10 | Dairy-free cream swap never picks a dairy substitute; leftover dairy lines are flagged |
| A11 | Replacing an ingredient the recipe doesn't have is refused |

**Part B: 7 scripted multi-turn conversations (19 turns)** through the full bot (LLM router + tools),
each turn with automatic checks:

| Conversation | Covers |
|---|---|
| C1 | Task 1 multi-turn: penne → "I cannot have dairy" → "show the second one" → calories (unsupported) |
| C2 | Task 1 aggregates: garlic+onion count & %, 5 fewest-step tomato recipes, mean/median by source. **The bot's numbers are checked against a direct computation.** |
| C3 | Task 2: the PDF pantry request → "Exclude eggs too" → "rank by fewest steps instead" |
| C4 | No-match cases: impossible pantry request; "beef stew" → "I'm vegan" |
| C5 | Task 3: banana bread without eggs, dataset-only ingredients (limited evidence) |
| C6 | Task 3: cream → dairy-free in a pasta (weak evidence + other dairy left in the recipe) |
| C7 | Unsupported question (lowest-calorie lasagna) and reset |

**Part C: one-shot LLM baseline.** The same Groq model gets 4 questions directly with no tools
(garlic+onion count, fewest-step tomato recipe IDs, a pantry request, calories of a banana bread).
The answers are then checked: are the numbers close to the real ones, and do the IDs/titles exist?

## Results

### Part A — 11/11 passed

| ID | Result | Detail |
|---|---|---|
| A1 | ✅ | all normalisation cases ok |
| A2 | ✅ | 7,129 Epicurious recipes had duplicated method lines (e.g. 2 raw lines → 1 step) |
| A3 | ✅ | bot = manual = 15,974 recipes (12.99% of 122,931); loose rule = 20,244 |
| A4 | ✅ | steps [1, 1, 1, 1, 1]; true minimum over 13,781 tomato recipes = 1 |
| A5 | ✅ | 717 eligible penne results, 0 dairy leaks |
| A6 | ✅ | top-5 all use 4/4 ingredients; steps [5, 3, 2, 3, 3] |
| A7 | ✅ | pantry → onion, tomato, rice; no egg in any result |
| A8 | ✅ | no-match reported; alternatives labelled as violations |
| A9 | ✅ | best = yogurt (limited evidence); 2 cited recipes verified egg-free; banana = "co-occurs only" |
| A10 | ✅ | best = broth + cornstarch; leftover "Grated Parmesan" flagged as still violating |
| A11 | ✅ | refused |

### Part B — 19/19 turns passed (after fixes; the first run was 15/19)

Model: `openai/gpt-oss-120b` on Groq (temperature 0).

| Conversation | Turns | Notes |
|---|---|---|
| [C1](../eval/transcripts/C1_search_followups.md) search + follow-ups | 4/4 | "I cannot have dairy" kept the penne query and added the restriction; calories question refused |
| [C2](../eval/transcripts/C2_aggregate_stats.md) aggregates | 3/3 | The bot's count, ranking and mean were each checked against a direct computation |
| [C3](../eval/transcripts/C3_pantry_matching.md) pantry matching | 3/3 | "Exclude eggs too" kept no-peanuts and ≤6 steps |
| [C4](../eval/transcripts/C4_no_match.md) no-match | 3/3 | Impossible pantry → explicit no-match; beef stew + vegan → no full match, partials labelled |
| [C5](../eval/transcripts/C5_substitution_eggs.md) egg-free banana bread | 2/2 | Cited egg-free recipes; banana marked "co-occurs only" |
| [C6](../eval/transcripts/C6_substitution_dairy_weak.md) dairy-free cream | 2/2 | Weak evidence capped at "limited"; leftover mozzarella flagged, then swapped by the LLM |
| [C7](../eval/transcripts/C7_unsupported_and_reset.md) unsupported + reset | 2/2 | No calorie numbers invented |

The first full run failed 4 turns. All 4 were real problems, listed in the "What failed" table below
(the last four rows).

### Part C — one-shot LLM baseline

The same model was asked the questions directly, with no tools:

| Question | One-shot answer | RecipeBot |
|---|---|---|
| How many recipes contain garlic and onion, and what %? | Declined (can't see the data), offered code instead | 15,974 = 12.99% of 122,931 (strict), 20,244 loose |
| 5 fewest-step tomato recipes, with IDs | Declined, no IDs | 5 real IDs, each with 1 step, ties explained |
| 5 recipes for eggs/onions/tomatoes/rice, no peanuts, ≤6 steps | Declined | 5 real recipes using 4/4 ingredients, 2–5 steps |
| Calories per slice and total time of Allrecipes "Banana Bread" | **"≈ 210 kcal … Value (from the dataset)" and "1 hour 15 minutes"** | The dataset has no calorie or time fields, so it says so and quotes only durations written in the steps |

The interesting result: a modern model is mostly honest about data it can't see, so for
counting questions you get *no* answer rather than a wrong one. But when a question sounds
answerable, like calories of a well-known recipe, it confidently invents a value and even
attributes it to the dataset. That's the case the grounded design is meant to prevent. Older
or smaller models invent the counts too.

---

## What worked

- **Grounded numbers.** Every count/percentage/ranking is reproducible and matches an independent
  computation (A3, A4). Answers state the filters, n, denominator and rule.
- **Filter-then-rank.** Because restrictions are applied to the whole dataset before ranking,
  "no dairy" has zero leaks (A5) and follow-up restrictions never get lost.
- **Constraint handling.** Nothing is relaxed silently. Impossible requests produce an explicit
  no-match, and alternatives are labelled with the exact rule they break (A8).
- **Honest evidence for substitutions.** The with/without comparison correctly refuses to treat
  co-occurrence as evidence. Banana is in 96% of banana breads *with* egg, so egg-free banana
  breads using banana tell us nothing (A9).

## What failed (during development) and why

These were real failures found by running the system. Each led to a design change:

| Failure | Why it happened | Fix |
|---|---|---|
| "creamy penne" → *Creamy Cocoaccino* (a drink) ranked #1 | TF-IDF cosine gives short titles a high score from a single shared word | Coverage re-rank: score × (share of query words present)² |
| Olive oil proposed as the best cream substitute in a pasta | Counting "similar recipes without cream that use X" rewards ubiquitous ingredients | Count a candidate only if it's *more common* without the target than with it |
| "Coconut cream" scored 0 as a substitute | The target "cream" was detected by text, so coconut-cream recipes counted as *containing cream* | Target detection uses normalised names (coconut cream is a separate product) |
| A "no dairy" adaptation still listed half-and-half | Only the requested line was swapped; other dairy lines were never checked | Final independent restriction check on every rewrite, with a 🚫 banner listing what's left |
| "Peanut butter" stayed in the pantry under "no peanuts" | Pantry/exclusion overlap was checked by exact name only | Pantry items are checked against the exclusion's categories/terms and removed with a note |
| "Chocolate" matched only 690 recipes | Strict family matching missed *bittersweet chocolate*, *semisweet chocolate*… | Ends-with matching plus a `DIFFERENT_PRODUCTS` blocklist (3,737 now) |
| "quinoa chocolate lasagna" returned plain quinoa as if it were a match | Ranking found the best partial overlap and showed it as an answer | Partial matches are explicitly labelled; the header says no recipe matches everything |
| *(eval run 1)* "I'm vegan" stored only dairy, egg, meat | The LLM router expanded "vegan" itself and forgot fish, shellfish and honey | Router prompt: pass diet words through verbatim; the code owns the definition. A good reminder that LLMs shouldn't be trusted with rules |
| *(eval run 1)* "Replace the cream" said the recipe had no heavy cream | The line was "heavy whipping cream"; target lines were matched by raw text | Lines are matched on **normalised** names (heavy whipping cream → heavy cream) in search evidence, substitution and quantity checks |
| *(eval run 1)* "I have lobster, mango and dark chocolate…" ran a search | Router picked the wrong intent | Router rule: "I have …" is always a pantry match; "uses all three" → `must_use_all` |
| *(eval run 1)* "rank them by fewest steps instead" became a stats query | Router lost the matching context | Router rule: after a match, ranking changes stay in match |
| Olive oil rated "direct" evidence again for a pasta whose similar recipes had **no** cream at all | With zero "with cream" recipes, the with/without comparison is meaningless | If fewer than 3 similar recipes use the target, evidence is capped at "limited", with an explicit warning |
| LLM's "dairy-free mozzarella-style cheese" failed the dairy check | Keyword "cheese" matched | Explicit free-from labels (dairy-free / vegan / plant-based + product) are trusted, but only for that product |

## Known limitations (still open)

- **Normalisation misses.** Unusual phrasing yields junk names like "juice", "greens" or "vegetable".
  These show up in the "Missing" lists for some matches. A larger synonym list, or an
  ingredient-parsing model, would help.
- **Ingredient lists can be incomplete.** E.g. `fn_3xGSq4…` (*Scallops and Penne Pasta*) doesn't
  list penne in its ingredients, so it isn't flagged as containing gluten. Filters can only see
  what the recipe lists.
- **Hidden allergens in products.** "Semisweet chocolate" or "Worcestershire sauce" (anchovies are
  covered, but not every product) can contain allergens that the line doesn't name. That's why the
  bot never calls anything medically safe.
- **Step counts depend on formatting.** About 10k Food Network recipes put the whole method in one
  paragraph and count as 1 step, so "fewest steps" rankings are skewed towards them. The answer
  states the rule and the number of ties.
- **Lexical search.** Purely conceptual requests work only as well as the router's keyword
  translation.
- **The substitution role table is small** (egg, cream, butter, milk, sour cream, cheese, flour).
  For other ingredients the bot relies only on the data-driven "what do versions without X use
  more often" signal, and says the role is a prediction.
- **The "similar dish" neighbourhood can be off.** For "Penne with Sausage and Cheesy Garlic
  Bread", some cited evidence comes from garlic-bread recipes. The evidence is labelled
  *limited* in that case, but a better dish classifier would help.
- **Router intent errors are possible.** They're caught by the conversation tests and visible in
  the UI's router-JSON panel, but a new phrasing can still be misrouted.
- **The rule-based rewrite fallback is clumsy.** It can produce phrases like "whipped broth" when a
  substitute can't do what the original step did (whipping). The LLM rewrite is asked to flag this
  in `warnings`, and the fallback only kicks in if the LLM is unavailable or fails the safety check.
