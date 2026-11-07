# AI tools disclosure

> ✏️ **Please review and edit this file so it accurately describes your own process before submitting.**

## Tools used

| Tool | Used for |
|---|---|
| **Claude Code** (Anthropic, Claude Opus) | Pair-programming: scaffolding the uv project, writing most of the Python modules, the evaluation harness, and first drafts of the documentation, based on my requirements and the assignment PDF. |
| **Groq API** (openai/gpt-oss-120b) | Part of the product itself, not a development tool: it parses user messages into JSON plans and rewrites recipes after a substitution. |

## How I used Claude Code

- **Planning:** went through the assignment PDF and agreed the architecture before any code was
  written: LLM only for parsing and rewriting, all facts and numbers computed in code, Streamlit for
  the UI, uv for packaging.
- **Code:** generated module by module (data loading → normalisation → search → analytics →
  matching → substitution → agent → UI). Each module was run against the real dataset before
  moving on.
- **Debugging through testing:** several design decisions came from running the code and seeing
  what went wrong:
  - "creamy penne" returned a drink first → added the query-coverage re-rank;
  - olive oil was suggested as a cream substitute just because it's in every pasta → added the
    "more common without the target" evidence rule;
  - "coconut cream" counted as dairy cream → target detection switched to normalised names;
  - a "no dairy" rewrite left half-and-half in the recipe → added the final restriction check;
  - "peanut butter" stayed in the pantry under "no peanuts" → exclusions now remove conflicting
    pantry items.
- **Docs:** first drafts of the README, design notes and evaluation report were generated, then
  edited.

## What I'm expected to understand (and can explain)

- Why the LLM is restricted to routing and rewriting, and how that prevents ungrounded answers.
- The ingredient normalisation pipeline and the family/ends-with/blocklist rules.
- Filter-then-rank retrieval, TF-IDF scoring and the coverage re-rank.
- The step-counting rule and why the Epicurious duplicates matter.
- The lexicographic ranking in pantry matching, and why I didn't use a weighted score.
- The with/without-target evidence test for substitutions.
- How the evaluation checks the bot's numbers against an independent recomputation.
