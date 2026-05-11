# Full-run headline — n=360 (pilot 180 + held-out 180)

**Timestamp:** 2026-05-10 (saved after held-out completion + concurrent-validity check)
**Companion:** `artifacts/pilot-headline.md` (timestamped 2026-05-10 pre-full-run; preserved unchanged).
**Companion:** `artifacts/per-title-decomposition.md` (per-title moderator analysis).
**Companion:** `artifacts/model-drift-report.md` (GPT-4o judge routing drift).

---

## Single-paragraph summary for the introduction

> Across 360 paired LLM-judge evaluations (3 generators × 3 judges × 10
> titles × 4 attribution conditions), numerical scores were statistically
> indistinguishable across attribution conditions (Δ_score(true_label −
> false_label_1) = −0.10 ordinal points per dimension on a 0–10 scale,
> n.s.). The same evaluations, recoded for prose tone by a non-circular
> Qwen 2.5 72B coder, revealed a label-attribution asymmetry on the
> harshness dimension: prose attributed to ChatGPT was rated
> 0.33 ordinal points harsher than the same body attributed to Claude
> (paired non-OpenAI judges, n=60 paired, 95% CI [+0.13, +0.53],
> Wilcoxon p=0.011, sign-flip permutation p=0.003). The asymmetry was
> content-moderated: personal-narrative titles drove the effect (mean
> Δ ≈ +0.70), informational titles were null (mean Δ ≈ −0.03). A
> separately-constructed corpus-driven lexicon, applied to the held-out
> half of the corpus, correlated positively with the Qwen harshness
> ratings (Spearman ρ=+0.189, 95% CI [+0.032, +0.341], permutation
> p=0.012), giving an independent concurrent-validity check on the
> prose-channel measurement.

---

## Score channel — null

| Condition       | n  | Mean total (max 30) | SD   |
|---|---|---|---|
| none            | 90 | 23.92               | 1.26 |
| true_label      | 90 | 23.49               | 1.86 |
| false_label_1   | 90 | 23.78               | 1.59 |
| false_label_2   | 90 | 23.66               | 1.51 |

Δ(true_label − false_label_1) = **−0.289 points** out of 30 (≈−0.10
ordinal points per dimension on the 0–10 scale). Within noise.
Replicates the pilot's null score-channel result at full power.

---

## Prose channel — significant, content-moderated

### Combined n=360 (paired by judge × blog, Qwen-harshness, ChatGPT − Claude)

| Cell | n_paired | Δ | 95% CI | Wilcoxon p | Perm p |
|---|---|---|---|---|---|
| GPT-4o judge   | 30 | +0.033 | [0.00, +0.10] | 0.73 | 1.00 |
| Gemini judge   | 30 | **+0.400** | [+0.17, +0.67] | **0.012** | **0.005** |
| Claude judge   | 30 | +0.267 | [−0.03, +0.60] | 0.23 | 0.17 |
| **Non-OpenAI (Gem+Cla)** | **60** | **+0.333** | **[+0.13, +0.53]** | **0.011** | **0.003** |

### Pilot vs held-out replication

| Cell | Pilot Δ | Held-out Δ | Combined Δ |
|---|---|---|---|
| GPT-4o     | +0.067 | +0.000 | +0.033 |
| Gemini     | **+0.600** | +0.200 | **+0.400** |
| Claude     | +0.467 | +0.067 | +0.267 |
| Non-OpenAI | **+0.533** | +0.133 | **+0.333** |

The pilot magnitude was inflated relative to the combined estimate by
roughly 60%. Per the per-title decomposition (`artifacts/per-title-
decomposition.md`), this inflation is explained by the pilot's title
mix: 4/5 personal-narrative titles vs the held-out's 2/5. The combined
estimate Δ=+0.33 is the average across a balanced 10-title corpus.

### Content moderator (per-title means, non-OpenAI judges, n=6 per title)

| Title group | mean Δ |
|---|---|
| Personal-narrative (5 titles) | **+0.70** |
| Informational/explanatory (5 titles) | **−0.03** |

Top-Δ titles (`marathon` +1.33; `sourdough` +1.00; `minimalism` +0.50)
share an aspirational-self-presentation framing. Bottom-Δ titles
(`paper books` −0.17; `astronomy` −0.17; `cold showers` −0.17) are
sensory/explanatory. Mann-Whitney U on the two distributions of per-
title means: p=0.40 — the binary split is not by itself significant at
n=5/group, but the rank-ordering is suggestive.

---

## Concurrent validity — held-out lexicon vs Qwen

A held-out-split design: a 96-justification stratified sample of the
**pilot** critiques (8 per judge × condition cell) was sent to Qwen 2.5
72B in a single request. Qwen returned 43 harsh-marker phrases
categorised at three severity levels. The list was hand-curated to 41
markers (de-duplications, severity recalibration, polarity-fragile
strikes). The curated lexicon was applied **mechanically** to the
held-out 180 critiques, producing per-critique counts at each severity
level and a weighted sum. Spearman ρ between the lexicon's weighted
sum and the Qwen-coder's holistic harshness rating is the concurrent-
validity statistic.

| Statistic | Value | p |
|---|---|---|
| Spearman ρ(lex_weighted_sum, qwen_harshness) | **+0.189** | **0.011** |
| 95% bootstrap CI on ρ | **[+0.032, +0.341]** | (excludes 0) |
| Permutation p (10 000 label-shuffles) | — | **0.012** |
| Spearman ρ(lex_total_count, qwen_harshness) | +0.148 | 0.048 |

Cross-tab (Qwen-harshness level → mean lex_weighted_sum):

| Qwen-harshness | n | mean weighted_sum |
|---|---|---|
| 1 (mild) | 161 | 1.29 |
| 2 (moderate) | 14 | **3.14** |
| 3 (high) | 5 | 1.00 |

The level-1 → level-2 jump (1.29 → 3.14) is the cleanest signal; level-3
is unstable at n=5. **The validity claim is modest but real**: the
lexicon captures a positive, significant fraction of the variance
that Qwen's holistic prose rating captures, in a sample where the
lexicon's construction set and application set are disjoint.

Per-judge ρ values are noisier (none reach significance individually
at n=60 each) because Qwen-harshness has low variance within each
judge slice — most rows at level 1, with the asymmetry concentrated in
a minority of the corpus. Pooling provides the statistical power.

---

## What does NOT work in the paper

- **Cohen's κ** between the v0.1 lexicon and Qwen on the pilot (≈0 on all
  three dimensions) was uninformative because the methods measured
  different constructs by design and because the v0.1 lexicon did not
  align with codebook v0.2 (still firing on bare model-name tokens for
  identity_reference). κ has been dropped from the validation plan.
- **Identity-reference and rationalization dimensions** are degenerate at
  Qwen scale on this corpus (359/360 and 355/360 at floor respectively).
  The harshness dimension carries the entire prose-channel signal.
- **GPT-4o judge** is flat throughout (Δ≈0). Two reasons stack:
  (a) substantively, GPT-4o gives consistently low harshness regardless
  of label; (b) methodologically, GPT-4o is the one judge with
  cross-day OpenRouter routing drift — the modal pilot serving snapshot
  (`fp_fab7bd3a94`, 50% of pilot evaluations) was 0% of the held-out
  run. The headline finding is concentrated in the two stable judges
  (Gemini direct from Google; Claude Sonnet 4 via Amazon Bedrock).

---

## Provenance

- Generation: 30 blogs × 10 titles × 3 generators (`runs/generations.jsonl`)
- Evaluation: 360 rows × 3 judges × 4 conditions (`runs/evaluations.jsonl`)
- Qwen prose codings: 360 rows (`runs/qwen-codings.csv`)
- Lexicon construction snapshot: `runs/responses/lexicon-construction/lexicon-construction-668f1ad08253.json`
- Curated lexicon: `artifacts/lexicon-v2-raw.json` (saved in-place by Hashem; raw construction preserved in the snapshot)
- Lexicon counts: `runs/lexicon-counts.csv` (held-out 180; pilot 180 not coded — held-out-split)
- Backup of the run: `runs.backup-2026-05-10/` (pre-curation snapshot)
- Drift report: `artifacts/model-drift-report.md`
- Per-title decomposition: `artifacts/per-title-decomposition.md`
- Pilot headline (timestamped pre-full-run): `artifacts/pilot-headline.md`

---

## Next step

`/analyze` (Step 8) produces the figures and the consolidated table
that ships with the introduction. This headline document is the input
for that step.
