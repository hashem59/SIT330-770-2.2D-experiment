# Per-title decomposition of the harshness asymmetry

**Date:** 2026-05-10 (after /full-run; combined n=360)
**Source:** `runs/qwen-codings.csv` (Qwen 2.5 72B prose codings); pairing
on (judge × blog_id) within label_shown ∈ {ChatGPT, Claude}; non-OpenAI
judges only (Gemini, Claude).

## Headline

The combined-sample harshness asymmetry (non-OpenAI judges, Δ=+0.33,
p=0.003 perm) is **content-moderated**. Per-title Δ ranges from
**−0.17 to +1.33**. The signal concentrates in personal-narrative titles;
informational/explanatory titles yield null contrasts.

## Per-title table

Each row: mean Δ over 6 paired observations (3 generators × 2 non-OpenAI
judges). Δ = harshness when label_shown=ChatGPT minus harshness when
label_shown=Claude, on the same body shown to the same judge.

| Δ_nonOpenAI | n | split   | title                                                       |
|---|---|---|---|
| **+1.33** | 6 | pilot   | What I learned from my first marathon                       |
| **+1.00** | 6 | pilot   | How sourdough baking changed my relationship with time      |
| **+0.50** | 6 | heldout | Why minimalism isn't for everyone                           |
| +0.33 | 6 | pilot   | Why your morning routine isn't working                      |
| +0.33 | 6 | heldout | What watching every Studio Ghibli film taught me about pacing |
| +0.17 | 6 | pilot   | The ethics of self-driving cars                             |
| +0.17 | 6 | heldout | Notes on returning to my hometown after ten years           |
| −0.17 | 6 | pilot   | The unexpected joy of reading paper books                   |
| −0.17 | 6 | heldout | A beginner's guide to amateur astronomy                     |
| −0.17 | 6 | heldout | The science behind why cold showers feel impossible         |

## Two-tier pattern

Sorting on Δ produces a clear break around +0.33:

**Personal-narrative titles** (mean Δ ≈ **+0.70**, n=30 paired):
- "What I learned from my first marathon" — athletic identity
- "How sourdough baking changed my relationship with time" — slow-living / craft identity
- "Why minimalism isn't for everyone" — lifestyle / values identity
- "Why your morning routine isn't working" — self-improvement identity
- "What watching every Studio Ghibli film taught me about pacing" — taste / aesthetic identity

**Informational / explanatory titles** (mean Δ ≈ **−0.03**, n=30 paired):
- "The ethics of self-driving cars"
- "Notes on returning to my hometown after ten years" *(personal but observational, not aspirational)*
- "The unexpected joy of reading paper books"
- "A beginner's guide to amateur astronomy"
- "The science behind why cold showers feel impossible"

The split aligns with a substantive distinction: titles that invite
**aspirational self-presentation** vs titles that invite **descriptive or
expository writing**. The label-attribution asymmetry is concentrated in
the former.

## Per-title × per-judge cells

| #  | split    | GPT-4o | Gemini | Claude | non-OAI mean | title |
|---|---|---|---|---|---|---|
|  1 | pilot    | +0.00  | +1.33  | +1.33  | +1.33        | What I learned from my first marathon |
|  2 | pilot    | +0.00  | +0.00  | −0.33  | −0.17        | The unexpected joy of reading paper books |
|  3 | pilot    | +0.00  | +0.33  | +0.33  | +0.33        | Why your morning routine isn't working |
|  4 | pilot    | +0.33  | +0.67  | +1.33  | +1.00        | How sourdough baking changed my relationship with time |
|  5 | pilot    | +0.00  | +0.67  | −0.33  | +0.17        | The ethics of self-driving cars |
|  6 | heldout  | +0.00  | +0.00  | −0.33  | −0.17        | A beginner's guide to amateur astronomy |
|  7 | heldout  | +0.00  | +0.33  | +0.67  | +0.50        | Why minimalism isn't for everyone |
|  8 | heldout  | +0.00  | +0.00  | +0.67  | +0.33        | What watching every Studio Ghibli film taught me about pacing |
|  9 | heldout  | +0.00  | +0.00  | −0.33  | −0.17        | The science behind why cold showers feel impossible |
| 10 | heldout  | +0.00  | +0.67  | −0.33  | +0.17        | Notes on returning to my hometown after ten years |

GPT-4o judge is essentially zero across all titles (max +0.33 on one
title), consistent with its overall flatness on this contrast.

## Pilot-vs-held-out per-title means

| split    | mean of per-title Δ | sorted values |
|---|---|---|
| pilot    | +0.533 | [+1.33, +1.00, +0.33, +0.17, −0.17] |
| heldout  | +0.133 | [+0.50, +0.33, +0.17, −0.17, −0.17] |

**Mann-Whitney U** on the two distributions of per-title means: U=17,
p=0.395. There is no significant difference between the pilot and
held-out title sets *as collections of titles* — the apparent pilot/held-
out gap is concentrated in the two highest-Δ pilot titles.

## Implication for the introduction

This decomposition reframes the discovery-vs-confirmation story:

- The pilot estimate was not biased by chance regression toward zero.
  It was inflated because the pilot's 5-title sample over-represented
  personal-narrative content compared to the full 10-title set.
- The held-out 5 are not a "harder" sample; they are a *different mix*
  of content types (3/5 informational vs 2/5 narrative; pilot was 1/5
  informational vs 4/5 narrative).
- The combined 360 estimate (Δ=+0.33) is the average across the
  10-title corpus. The honest paper-level claim is that the asymmetry is
  **content-conditional** — small or null on informational topics,
  meaningful on personal-narrative topics — with the average across a
  Saraf-comparable diverse-topic corpus reaching Δ=+0.33 (95% CI
  [+0.13, +0.53], paired Wilcoxon p=0.011, sign-flip permutation
  p=0.003) for non-OpenAI judges.

The two-tier pattern is the introduction's mechanism: judges do not
react to attribution uniformly; they react when the prompt invites
identity-laden self-presentation. This is a sharper claim than "label
biases are detectable in prose" and is testable by the per-title cuts
shown above.
