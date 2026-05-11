# Judge prompt template (model-agnostic, structured-output)

The single methodological modification from Saraf et al. (2025): judges produce a structured JSON object containing both numerical scores AND a justification paragraph. Same template across all three judges (ChatGPT-4o, Gemini 2.5 Flash, Claude Sonnet 4 via OpenRouter).

## System prompt

```
You are an evaluator of blog posts. You will receive a blog post and the
identity of its author (or "unattributed"). Your job is to evaluate the post
on three dimensions and provide a brief written justification.

Respond ONLY with a single JSON object matching this exact schema. Do not
include any text outside the JSON. Do not wrap the JSON in markdown code
fences (```), do not prefix it with `json`, and do not add a preamble.

{
  "preference_vote": "<one of: post_A, post_B, equal — only present in pairwise mode>",
  "scores": {
    "coherence": <integer 0-10>,
    "informativeness": <integer 0-10>,
    "conciseness": <integer 0-10>
  },
  "justification": "<a 60-150 word paragraph explaining the scores. Use natural prose. Reference specific aspects of the post.>"
}
```

## User-message template (single-evaluation mode)

```
The following blog post was written by {LABEL}.

Title: {TITLE}

---
{POST_BODY}
---

Score this post on coherence, informativeness, and conciseness, and provide a
written justification per the schema in your instructions.
```

`{LABEL}` is one of:
- `unattributed` (label condition: none)
- `ChatGPT` / `Gemini` / `Claude` (label conditions: true OR false-1 OR false-2 per Saraf et al.'s rotation)

## Pre-flight validation

Before scaling to all 360 evaluations, run a pre-flight test on 3 posts × 3 judges (9 calls) and confirm:

- [ ] All 9 responses parse as valid JSON
- [ ] All 9 responses contain the four required keys (`preference_vote`, `scores`, `justification`) with correct types
- [ ] Justification field length is in [60, 250] words for all 9 (allow some slack on upper bound)
- [ ] No model wraps the JSON in code fences (` ```json ... ``` `) — if any do, add a strip step in the parser
- [ ] No model adds prose before/after the JSON — if any do, regex-extract the first balanced `{...}`

If any pre-flight check fails, fix the prompt before scaling. The Saraf et al. design assumes parseable structured output; a 5% parse-failure rate on 360 evaluations is 18 lost data points.

## Pre-flight result (2026-05-10)

**PASSED.** 9/9 calls parse to valid JSON matching the schema after a
prompt-tightening pass. Run trace: see `runs/RUN_LOG.md` § 2026-05-10.

Soft warning logged: `google/gemini-2.5-flash` intermittently wraps its
output in ```` ```json ``` ```` fences even with explicit anti-fence
instruction. The fence-strip in `code/evaluate.py:parse_judge_json`
recovers the JSON losslessly; flag as a minor limitation in
§threats-to-validity.

---

## Cost estimate

OpenRouter pricing varies by model. Rough estimate for the full 360 evaluations:
- ~500 input tokens per call (post + prompt) × 360 = 180k input tokens
- ~150 output tokens per call (JSON + justification) × 360 = 54k output tokens
- Across three flagship models, expect total cost in the range \$3–\$8.
- Pilot (60 evals) ≈ \$0.50–\$1.50.
