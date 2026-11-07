# C7_unsupported_and_reset
**Cross-cutting - refusing unsupported questions**

_Why this test:_ The dataset has no nutrition or time data; the bot must say so instead of guessing.

## Turn 1
**User:** What is the healthiest, lowest-calorie lasagna in the dataset?

<details><summary>Router plan (LLM output)</summary>

```json
{
  "intent": "unsupported",
  "unsupported": {
    "missing": "calories / nutrition"
  }
}
```
</details>

**Bot:**

The Recipe Box dataset doesn't contain **calories / nutrition** — each recipe only has a title, an ingredient list and instructions. I'd rather say that than make up a number.

**Checks:** ✅ all passed

---

## Turn 2
**User:** Start over

<details><summary>Router plan (LLM output)</summary>

```json
{
  "intent": "reset"
}
```
</details>

**Bot:**

Okay, starting fresh — all searches and restrictions cleared.

**Checks:** ✅ all passed

---
