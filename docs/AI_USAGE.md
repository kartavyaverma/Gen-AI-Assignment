# AI tools used

## Tools

- **Claude Code** (Anthropic, Claude Opus): I used it as a pair programmer. It set up the uv
  project and wrote most of the Python modules, the evaluation script and the first drafts of the
  docs, based on my requirements and the assignment PDF.
- **Groq API** (`openai/gpt-oss-120b`): this is part of the chatbot itself, not something I used to
  build it. It turns user messages into JSON requests and rewrites recipes after a substitution.

## How I worked with Claude Code

- **Planning.** Before writing any code we went through the assignment and settled on the design:
  the LLM only parses requests and rewrites text, all facts and numbers come from code, Streamlit
  for the UI, uv for packaging.
- **Building.** The code was written one module at a time: data loading, ingredient cleanup,
  search, statistics, matching, substitution, the agent, then the UI. Each module was run on the
  real dataset before moving on to the next.
- **Testing and fixing.** A lot of the design came from running the bot and seeing what went
  wrong. For example:
  - "creamy penne" returned a drink first, so results are now re-ranked by how many query words
    they contain
  - olive oil was suggested as a cream substitute just because it's in every pasta, so a
    substitute now has to be more common in recipes without the ingredient
  - coconut cream was being treated as dairy cream, so matching now uses cleaned ingredient names
  - a "no dairy" rewrite still had half-and-half in it, so every rewrite is now checked against the
    restrictions
  - peanut butter stayed in the pantry after "no peanuts", so excluded items are now removed from
    the pantry

  The full list is in [EVALUATION.md](EVALUATION.md).
- **Docs.** The README, design notes and evaluation report started as generated drafts that were
  then edited.

## What I can explain

- why the LLM is limited to parsing and rewriting, and how that keeps answers grounded
- how ingredient lines are cleaned up, and the family / ends-with / exception rules
- filtering before ranking, TF-IDF scoring and the query-word re-rank
- the step-counting rule and why the duplicated Epicurious instructions matter
- the fixed ranking order in pantry matching, and why I didn't use a weighted score
- the with/without comparison used as evidence for substitutions
- how the evaluation checks the bot's numbers against a separate calculation
