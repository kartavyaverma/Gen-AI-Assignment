# RecipeBot — a grounded recipe chatbot

A chatbot over the [Recipe Box dataset](https://eightportions.com/datasets/Recipes/) (~125k recipes
from Allrecipes, Epicurious and Food Network) that can:

1. **Search & answer questions** about recipes, and compute statistics over the whole dataset
2. **Match recipes to what you have** in your kitchen, with hard constraints you can stack up
3. **Adapt a recipe** when an ingredient is unavailable, backed by evidence from similar recipes

The main idea: **the LLM never makes up facts or numbers.** It only turns your message into a
structured request (a small JSON plan). Searching, filtering, counting, ranking and choosing
substitutes all happen in plain Python over the real data, and every answer shows recipe IDs and
how it was worked out. When the data can't answer something (calories, cooking time), the bot
says so.

```
you ─► Groq LLM "router" ─► JSON plan ─► session state (active restrictions, last results…)
                                     └─► search / stats / matching / substitution  (pandas + numpy + TF-IDF)
                                              └─► answer built from real records, with IDs and method
```

---

## Quick start

You need [uv](https://docs.astral.sh/uv/getting-started/installation/) and a free
[Groq API key](https://console.groq.com/keys). uv installs the right Python (3.12) for you.

```bash
git clone <this repo> recipebot && cd recipebot
uv sync
```

**1. Add your API key.** Copy `.env.example` to `.env` and paste your key:

```bash
cp .env.example .env
```

```env
GROQ_API_KEY=gsk_...
GROQ_MODEL=openai/gpt-oss-120b   # optional, any Groq chat model with JSON mode works
```

**2. Download the dataset** (~53 MB zip with the three JSON files, saved in `data/raw/`):

```bash
uv run python scripts/download_data.py
```

**3. Build the index** (one-time, about 1.5 minutes; writes `data/processed/`):

```bash
uv run recipebot-build
```

**4. Run it.** Web UI (Gradio) at http://127.0.0.1:7860:

```bash
uv run recipebot-ui
```

…or in the terminal:

```bash
uv run recipebot-cli
```

If you skip step 3, the app builds the index on its first start. Loading the processed data takes
about 8 seconds after that.

### Things to try (in this order, in one conversation)

```
Find a penne pasta recipe
I cannot have dairy
show 2
How many calories does that have?
How many recipes contain both garlic and onion? What percentage of the dataset is that?
Among recipes containing tomato, which five have the fewest instruction steps?
I have eggs, onions, tomatoes and rice. Suggest five recipes using as many as possible, no peanuts, at most six steps, fewest extra ingredients.
Exclude eggs too
Find a banana bread recipe
Take this banana bread recipe and remove the eggs. Use only ingredients that appear in the dataset.
```

The right-hand panel of the UI shows the **active state** (restrictions, pantry, recipe in focus).
It also shows the **router's JSON plan** for your last message, so you can see exactly how the bot
understood you.

---

## Running the evaluation

```bash
uv run pytest                              # unit tests for normalisation (no data/key needed)
uv run python eval/run_eval.py --offline   # deterministic tool checks (needs data, no key)
uv run python eval/run_eval.py             # + 7 multi-turn conversations + one-shot LLM baseline (needs key)
```

Results go to [`eval/results.md`](eval/results.md), and conversation transcripts go to
[`eval/transcripts/`](eval/transcripts/). The write-up of what worked and what didn't is in
[`docs/EVALUATION.md`](docs/EVALUATION.md).

---

## Project layout

| Path | What's in it |
|---|---|
| `scripts/download_data.py` | Downloads and unzips the dataset |
| `src/recipebot/data.py` | Loads all three JSON files, stable IDs, step-counting rule, cleaning |
| `src/recipebot/normalize.py` | Ingredient-line parsing, synonyms, variety families, allergen/diet categories, quantities |
| `src/recipebot/store.py` | Processed table + TF-IDF indexes + inverted ingredient index (built once, cached) |
| `src/recipebot/search.py` | Hard filters over the whole dataset, then ranked text search (Task 1) |
| `src/recipebot/analytics.py` | Counts, percentages, top ingredients, mean/median, rankings (Task 1) |
| `src/recipebot/matching.py` | Pantry → recipe matching with explainable ranking (Task 2) |
| `src/recipebot/substitution.py` | Evidence-based substitutions with cited recipe IDs (Task 3) |
| `src/recipebot/llm.py` | Groq calls: the router prompt, the recipe rewriter, the one-shot baseline |
| `src/recipebot/agent.py` | Session state and follow-ups; connects the router to the tools |
| `src/recipebot/app.py` / `cli.py` | Gradio UI / terminal UI |
| `eval/` | Conversation test set, evaluation runner, results, transcripts |
| `tests/` | Unit tests |
| `docs/DESIGN.md` | Design notes: retrieval, normalisation, ranking, computation, uncertainty, external search |
| `docs/EVALUATION.md` | Evaluation report: what worked, what failed, and why |
| `docs/AI_USAGE.md` | Disclosure of AI tool use |

## Dataset notes

- All three files are used. 125,164 raw records → **122,931 usable recipes**. 2,233 were dropped
  because they were empty: null records, a title with no ingredients, or no instructions.
- Every recipe keeps a **stable ID** of the form `<source>_<original key>`, e.g.
  `ar_rmK12Uau.ntP510KeImX506H6Mr6jTu`. This is the dataset's own key with a prefix for the site.
- The original title, ingredient list and instruction text are stored untouched. For display, the
  only change is stripping the `ADVERTISEMENT` token that the Allrecipes scraper attached to every
  ingredient line.
- The dataset has **no nutrition, times, servings, ratings or cuisine** fields. The bot won't
  make these up.

## Limitations (short version — details in `docs/EVALUATION.md`)

- Ingredient normalisation is rule-based. It handles the common cases well, but rare phrasings
  can produce odd names ("juice", "greens").
- Allergen/diet detection is keyword-based and works only on what each recipe lists. A packaged
  product like "semisweet chocolate" may contain milk without saying so. Treat the dietary filters
  as a strong helper, not a medical guarantee.
- Search is lexical (TF-IDF). The LLM rewrites vague requests into keywords, but purely
  conceptual queries ("something cosy for a rainy day") work less well than with embeddings.
- Step counts follow the source's own line breaks. Food Network often puts the whole method in one
  paragraph, so those recipes count as 1 step.
