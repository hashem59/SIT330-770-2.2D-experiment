# Model-drift report — pilot vs held-out

**Pilot run:** 2026-05-09 (titles 1–5; 180 evaluations)
**Held-out run:** 2026-05-10 (titles 6–10; 180 evaluations)
**Drift detected:** YES — on GPT-4o judge only (distributional, not clean-swap)

---

## Per-judge verdict

- **anthropic/claude-sonnet-4** — match. Both days: 60/60 routed via Amazon
  Bedrock; system_fingerprint not surfaced by Bedrock (this is normal).
- **google/gemini-2.5-flash** — match. Both days: 60/60 direct from Google;
  system_fingerprint not surfaced by Google's API.
- **openai/gpt-4o** — DRIFT (distributional). Same nominal model
  identifier, but OpenRouter's routing distribution between underlying
  serving snapshots shifted between pilot and held-out:

| provider / system_fingerprint | pilot (n=60) | held-out (n=60) |
|---|---|---|
| OpenAI / fp_fab7bd3a94 | **30 (50%)** | **0 (0%)** |
| OpenAI / fp_c0f910b5dd | 24 (40%) | 34 (57%) |
| OpenAI / fp_395c203642 | 2 (3%) | 2 (3%) |
| Azure  / fp_e9b9b028d7 | 4 (7%) | **24 (40%)** |

The largest shifts:
- `fp_fab7bd3a94` was the **modal snapshot** in the pilot (50%) and is
  **absent** from the held-out run.
- `fp_e9b9b028d7` (Azure-hosted) grew from 7% to 40% between days.

Total snapshots seen across both days: **4** distinct OpenAI/Azure
serving versions, all returning under the `openai/gpt-4o` model id.

---

## Implication for the headline

The pilot finding (Δ_harshness(ChatGPT − Claude) = +0.53, p=0.005 perm) is
**concentrated in the two stable judges**:

- Gemini judge (n=15 paired): Δ=+0.60, p=0.015 — cleanly attributable.
- Claude judge (n=15 paired): Δ=+0.47, p=0.17 — cleanly attributable
  (directional, underpowered).
- **GPT-4o judge (n=15 paired): Δ=+0.07, p=0.64** — flat. This was already
  the noisiest judge in the pilot; we can now report that its underlying
  serving-snapshot mix was also unstable across days.

Confirmation analysis on the held-out 180 will be partitioned by judge,
so the GPT-4o-judge cell is testable separately at n=30 paired in the
combined 360-row analysis. If GPT-4o-judge results remain flat in the
held-out and stable-judge cells continue to show the asymmetry, the
headline strengthens; if held-out GPT-4o flips, the drift report
localises the cause.

---

## Threats-to-validity language for the introduction (draft)

> Across the two OpenRouter calls (pilot, 2026-05-09; held-out, 2026-05-10),
> two of the three judge models routed identically: Anthropic Claude
> Sonnet 4 served entirely through Amazon Bedrock, and Google Gemini 2.5
> Flash served directly from Google. The third judge, OpenAI's GPT-4o,
> was distributed across four distinct underlying serving snapshots
> visible via OpenRouter's `system_fingerprint`; the modal pilot snapshot
> (`fp_fab7bd3a94`, 50% of pilot evaluations) did not appear in the
> held-out run. We report results stratified by judge for this reason and
> do not over-interpret pooled findings that mix stable-judge and
> drifting-judge cells.
