# titles.json — 10 blog post titles for the factorial

## Structure

A flat JSON array of 10 strings. Each string is a blog post title. Order matters:

- **Indices 0–4** are the pilot subset. `code/evaluate.py --pilot` consumes these only (5 titles × 3 judges × 4 conditions = 60 evaluations).
- **Indices 5–9** are full-run titles. The full run uses all 10 (30 generations × 12 evaluation cells = 360 evaluations).

## Editing

The titles shipped above are reasonable starters but they're **suggestions, not commitments**. Edit them freely. Constraints:

1. **Keep 10 titles.** Saraf et al.'s factorial assumes 10; the cost estimates in `run-config.yaml` assume 10.
2. **Topic diversity** — span different domains (lifestyle, science, ethics, narrative, hobby, opinion). The whole point is that label bias should generalise across topic, not be confounded with domain.
3. **Avoid politically loaded topics.** Some judge models will refuse, others will hedge — both reduce the data quality. The default starter titles deliberately stay clear of politics.
4. **Titles should admit a 400–600 word blog post.** Too narrow ("the syntax of the Python walrus operator") and the post becomes a single fact restated; too broad ("the meaning of life") and you get vague mush. Aim for the middle.
5. **No proper-noun model names in titles.** Avoid "What Claude thinks of..." or similar — that biases the generators before the labels even appear.

## Why these specific starter titles

- Spread across personal narrative, ethics, hobby, science, cultural commentary
- Each admits a 500-word piece without research effort
- All three flagship LLMs can write them without filtering
- No two titles are in the same micro-domain (avoids accidental clustering)

If you replace any, keep the spread.
