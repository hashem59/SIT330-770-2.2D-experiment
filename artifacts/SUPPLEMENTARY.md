# Supplementary material

This file is the supplementary index for the 2-page introduction in `paper/introduction.pdf`. The paper carries the headline finding and the empirical-motivation paragraph; the four detailed documents below carry the full evidence trail for any reviewer who wants to verify specific numbers or methodology choices.

**If you have ten minutes**, read this file plus `artifacts/codebook.md` and `runs/results-summary.json`. **If you have an hour**, read all four detailed documents below as well.

---

## What's reported where

### Headline numbers and statistical detail
**File:** `artifacts/full-run-headline.md` (169 lines)
**Read for:** the full corpus result (n=360). Per-judge breakdown, 95% confidence intervals, Wilcoxon and permutation tests, concurrent-validity statistic (Spearman ρ between lexicon and Qwen ratings).

### Pilot-stage snapshot (preserved pre-full-run)
**File:** `artifacts/pilot-headline.md` (132 lines)
**Read for:** what the data looked like at n=180, before the held-out half was collected. Preserved with a pre-full-run timestamp so the pilot-vs-held-out comparison in §threats-to-validity can be reproduced.

### Per-title moderator analysis
**File:** `artifacts/per-title-decomposition.md` (109 lines)
**Read for:** why the prose-channel effect is content-conditional. Per-title × per-judge Δ-harshness table; the personal-narrative vs informational split with sample-size split (pilot title-mix vs held-out title-mix).

### Provider routing-drift caveat
**File:** `artifacts/model-drift-report.md` (68 lines)
**Read for:** the OpenRouter system-fingerprint drift between pilot and held-out runs, particularly for the GPT-4o judge. Documents why the headline statistic uses non-OpenAI judges only.

---

## Other supporting artifacts

- `artifacts/codebook.md` — the locked codebook v0.2 (three dimensions, scales, examples, lexicon hints, Qwen-coder prompt fragments). Hand-authored before the experiment ran.
- `artifacts/judge-prompt.template.md` — the modified judge prompt that elicits structured-JSON output (the single methodological modification from Saraf et al.).
- `artifacts/lexicon-v2-raw.json` — the curated 41-marker corpus-driven lexicon.
- `artifacts/run-config.yaml` — canonical experimental design (3 × 3 × 10 × 4 factorial, models, sample-size justifications, validation plan).
- `artifacts/citation-verification-log.md` — every citation in `paper/references.bib` was checked against arxiv and DOI on 2026-05-11.
- `runs/results-summary.json` — machine-readable bundle of every statistic reported in the paper. The single most efficient file to spot-check a number against the paper.
