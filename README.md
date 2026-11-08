# RecipeBot

A chatbot for the [Recipe Box dataset](https://eightportions.com/datasets/Recipes/), which has about
125k recipes scraped from Allrecipes, Epicurious and Food Network. Built for the GenAI intern
assignment. It can:

1. search recipes and answer questions about them, including statistics over the whole dataset
2. suggest existing recipes for the ingredients you have, with restrictions like "no peanuts"
3. adapt a recipe when you need to swap an ingredient out, using other recipes as evidence

The main thing I wanted was for the bot to never make things up. The LLM is only used to work out
what you're asking for. It turns your message into a small JSON request, and then normal Python
code does the searching, filtering, counting and ranking on the actual data. Answers show recipe
IDs and explain how numbers were calculated. If the dataset can't answer something (calories,
cooking time, ratings), the bot says that instead of guessing.

```
your message -> LLM (Groq) -> JSON request -> Python tools over the data -> answer with IDs
```

## Setup

You'll need [uv](https://docs.astral.sh/uv/getting-started/installation/) and a free
[Groq API key](https://console.groq.com/keys). uv takes care of installing Python 3.12.

```bash
git clone https://github.com/kartavyaverma/Gen-AI-Assignment.git
cd Gen-AI-Assignment
uv sync
```

Copy `.env.example` to `.env` (on Windows use `copy` instead of `cp`) and put your key in it:

```bash
cp .env.example .env
```

```env
GROQ_API_KEY=gsk_...
GROQ_MODEL=openai/gpt-oss-120b
```

The model line is optional. Any Groq chat model that supports JSON mode should work.

Download the dataset (a ~53 MB zip, extracted into `data/raw/`):

```bash
uv run python scripts/download_data.py
```

Build the index. This only needs to be done once and takes about a minute and a half:

```bash
uv run recipebot-build
```

Start the web app (Streamlit, opens on http://localhost:8501):

```bash
uv run recipebot-ui
```

There's also a terminal version:

```bash
uv run recipebot-cli
```

If you skip the build step, the app will build the index itself the first time it starts. After
that it loads in around 8 seconds.

## Example conversation

Try these one after another in the same chat:

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

The sidebar shows which filters are currently active (search, exclusions, step limit, your
ingredients, the recipe you're looking at). Restrictions stay on until you remove them or start a
new chat. Each answer has a "Parsed request" section that shows the JSON the LLM produced, which
is handy for seeing how a message was understood.

## Evaluation

```bash
uv run pytest
uv run python eval/run_eval.py --offline
uv run python eval/run_eval.py
```

The first runs unit tests (no data needed). The second runs the tool checks without any LLM calls.
The third also runs 7 scripted conversations and a comparison against a plain LLM, so it needs the
API key. Results are written to [eval/results.md](eval/results.md), and the conversation
transcripts are in [eval/transcripts/](eval/transcripts/). My write-up is in
[docs/EVALUATION.md](docs/EVALUATION.md).

## Project structure

| Path | What it does |
|---|---|
| `scripts/download_data.py` | downloads and unzips the dataset |
| `src/recipebot/data.py` | loads the three JSON files, assigns IDs, counts steps |
| `src/recipebot/normalize.py` | cleans ingredient lines, synonyms, allergen/diet tags, quantities |
| `src/recipebot/store.py` | builds and loads the cached table and search indexes |
| `src/recipebot/search.py` | filtering and text search (task 1) |
| `src/recipebot/analytics.py` | counts, percentages, averages, rankings (task 1) |
| `src/recipebot/matching.py` | matching recipes to your ingredients (task 2) |
| `src/recipebot/substitution.py` | ingredient substitutions with evidence (task 3) |
| `src/recipebot/llm.py` | everything that talks to Groq |
| `src/recipebot/agent.py` | conversation state and deciding which tool to run |
| `src/recipebot/app.py`, `ui.py` | Streamlit app and its launcher |
| `src/recipebot/cli.py` | terminal version |
| `eval/` | test conversations, evaluation script, results, transcripts |
| `tests/` | unit tests |
| `docs/DESIGN.md` | design decisions and the reasoning behind them |
| `docs/EVALUATION.md` | what worked, what didn't, and what I changed |
| `docs/AI_USAGE.md` | how I used AI tools |

## Notes on the data

- All three files are used. Out of 125,164 records, 122,931 are kept. The other 2,233 were empty:
  null entries, or a title with no ingredients or instructions.
- Recipe IDs look like `ar_rmK12Uau.ntP510KeImX506H6Mr6jTu`. That's the dataset's own key with
  the source (`ar`, `epi` or `fn`) in front, so they stay the same on every machine.
- The original title, ingredients and instructions are kept as they are. The only cleanup for
  display is removing the word "ADVERTISEMENT", which the Allrecipes scraper attached to every
  ingredient line.
- There's no nutrition, timing, servings, ratings or cuisine information in the dataset.

## Known limitations

- Ingredient cleanup is rule-based. It covers the common cases, but some unusual lines end up with
  odd names like "juice" or "greens".
- Allergen and diet checks are keyword-based and only look at what the recipe lists. Packaged
  products like semisweet chocolate can contain milk without saying so, so this is a helper, not a
  medical guarantee.
- Search uses TF-IDF, not embeddings. It works well for dish names and ingredients, and less well
  for vague requests like "something cosy for a rainy day".
- Steps are counted from the line breaks in the original instructions. A lot of Food Network
  recipes are a single paragraph, so they count as one step.

More detail on all of this is in [docs/EVALUATION.md](docs/EVALUATION.md).
