# Pilot headline — n=180

**Timestamp:** 2026-05-10 (saved before /full-run begins)
**Purpose:** Lock the pilot finding as a discovery result, separate from any
confirmation produced by the subsequent full run. Per the held-out-split
design, the pilot 180 is the **construction set** for the corpus-driven
lexicon and the **discovery set** for the prose-asymmetry finding; the
full-run 180 is the **test set** for both.

---

## Headline

> Numerical judge scores across label conditions are within noise
> (Δ(true_label − false_label_1) ≈ −0.08 ordinal points per dimension,
> n.s. at n=45/cond). The same evaluations, recoded for prose tone by a
> non-circular Qwen 2.5 72B coder, show a significant asymmetry on the
> harshness dimension: **prose attributed to ChatGPT is rated more
> harshly than the same body attributed to Claude**, by 0.53 ordinal
> points on a 1–5 scale (95% CI [+0.23, +0.87], Wilcoxon p=0.009,
> permutation p=0.005). The asymmetry is concentrated in the two
> non-OpenAI judges (Gemini significant alone, Claude directional);
> GPT-4o judge is flat.

This is the **"Beyond the Score"** finding: a score-only analysis would
report a null; the prose channel surfaces a real attribution effect.

---

## Design of the test

- **Unit of analysis:** within (judge, blog_id) pair, the same blog body
  appears under all four label conditions and therefore under three
  distinct `label_shown` values (one true, two false rotations, plus the
  unattributed condition).
- **Contrast:** for each (judge, blog_id), pair the Qwen-harshness rating
  when `label_shown="ChatGPT"` against the rating when
  `label_shown="Claude"`. Sign convention: Δ = ChatGPT − Claude; positive Δ
  means harsher on ChatGPT-attributed prose.
- **Sample:** 15 paired observations per judge (5 titles × 3 generators ×
  one ChatGPT-shown row × one Claude-shown row). Combined non-OpenAI:
  n=30.
- **Tests:** Wilcoxon signed-rank with `zero_method='zsplit'` for paired
  ordinal data; sign-flip permutation (10 000 reps) on the mean
  difference; bootstrap 95% CI on the mean difference (10 000 reps).

## Results — combined non-OpenAI judges (Gemini + Claude)

| Quantity                          | Value                  |
|---|---|
| Mean Δ (ChatGPT − Claude harshness) | **+0.533** ordinal pts |
| 95% bootstrap CI                  | **[+0.23, +0.87]**     |
| Wilcoxon signed-rank statistic    | W = 109.0              |
| Wilcoxon p                        | **0.0094**             |
| Permutation p (sign-flip, 10 k)   | **0.0051**             |
| Sign breakdown                    | 12 positive, 16 ties, 2 negative |
| n (paired)                        | 30                     |

CI excludes zero. Both inferential tests reject the null at α = 0.01.

## Results — per judge

| Judge   | n  | Mean Δ | 95% CI         | Wilcoxon p | Perm p   |
|---|---|---|---|---|---|
| GPT-4o  | 15 | +0.067 | [0.00, +0.20]  | 0.6374     | 1.0000   |
| Gemini  | 15 | **+0.600** | [+0.27, +1.00] | **0.0148** | **0.0154** |
| Claude  | 15 | +0.467 | [0.00, +1.00]  | 0.2023     | 0.1706   |

## Results — score channel for context

| Condition       | n  | Mean total (max 30) | SD   |
|---|---|---|---|
| none            | 45 | 23.67               | 1.22 |
| true_label      | 45 | 23.24               | 1.96 |
| false_label_1   | 45 | 23.49               | 1.62 |
| false_label_2   | 45 | 23.44               | 1.52 |

Mean(true_label) − Mean(false_label_1) = **−0.244** points (out of 30; ~−0.08
per dimension). |t| ≈ 0.7. Saraf et al.'s direction is true > false; this
pilot is null/slightly inverted, but well within noise.

---

## Why this licenses /full-run as confirmation

1. The pilot answers a discovery question the score channel cannot:
   *do attribution effects appear in prose tone when they do not appear
   in scores?* Answer at n=180: yes, in two of three judges, on one of
   three coded dimensions, in the predicted direction (ChatGPT-out-group
   harsher than Claude-in-group for the non-OpenAI judges).
2. The Claude judge's slice (Δ=+0.47, p=0.17 at n=15) is the cell that
   most needs the full run's additional 15 paired observations. If the
   Claude direction holds at higher n, the asymmetry is a property of
   non-OpenAI judges as a class. If it fails to confirm, the asymmetry
   is Gemini-specific — also a publishable result with a different
   framing.
3. The full run is **not** a fishing trip: the dimension (harshness),
   contrast (label_shown=ChatGPT vs Claude), test (paired Wilcoxon /
   permutation), and prediction (positive Δ for non-OpenAI judges)
   are pre-registered by this document.

## Pre-registration of the lexicon held-out-split design

The lexicon channel is being rebuilt corpus-driven, not from a hand-edited
trigger list:

1. **Construction:** send all 180 pilot justifications to Qwen 2.5 72B in
   a single request and ask for harsh-marker words/phrases categorised
   into 2–3 severity levels, returned as JSON.
2. **Curation:** Hashem manually strikes context-dependent, sarcasm-
   dependent, or ambiguous terms (~15 min).
3. **Application:** apply the cleaned lexicon mechanically to the
   full-run 180 critiques only (the held-out test set), producing a
   count-per-critique table.
4. **Validity check:** compute Spearman ρ between lexicon counts and
   Qwen harshness ratings on the full-run 180. This is the concurrent-
   validity statistic for the prose channel.

The previous v0.1 lexicon (`runs/lexicon-codings.csv`, applied to the
pilot 180) is preserved for audit but is **not** carried into the
analysis stage. Inter-method Cohen's κ is dropped from the validation
plan; the v0.1 lexicon and Qwen measure different constructs and the κ
result was uninformative (≈0 on all three dimensions).

## Files referenced

- `runs/evaluations.jsonl` — 180 judge evaluations (pilot)
- `runs/qwen-codings.csv` — 180 Qwen prose codings (pilot)
- `runs/lexicon-codings.csv` — 180 v0.1-lexicon prose codings (pilot, not used post-pivot)
- `code/_pilot_prose_analysis.py` — the analysis script (per-channel means, κ)
- `artifacts/codebook.md` — codebook v0.2
- `artifacts/run-config.yaml` — locked experimental design
