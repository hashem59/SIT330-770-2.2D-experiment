# Codebook v0.2 — SIT330-770 2.2D
**Owner:** Hashem
**Status:** LOCKED. Step 2 of the 10-step lifecycle is complete.

## Grounding observation

When Claude critiques Gemini's reasoning on reinforcement-learning tasks, the harshness and dismissiveness of the prose (word choice, tone, structural choices) often diverges from the numerical score assigned. The same numerical score can carry radically different qualitative weight depending on source-judge identity. This codebook operationalizes that divergence.

---

## Dimension 1 — Critique Harshness (Lexical & Structural)

**Definition.** The severity and dismissiveness conveyed through word choice, negation patterns, and structural choices in the justification prose, *independent* of whether the score is low or high.

**Scale.** Ordinal 1–5.

- **1 (Very gentle):** Critique uses softeners, acknowledges strengths alongside weaknesses, positions critique as minor or contextual.
- **3 (Neutral):** Critique names problems directly without dismissive language or excessive qualification.
- **5 (Very harsh):** Critique uses severe negatives, absolutist language, dismissive framing; presents flaws as fundamental rather than contextual.

**Examples.**

- Level 1: *"This piece has solid structure, though the conclusion could be developed further."*
- Level 3: *"The argument lacks depth in the technical justification section."*
- Level 5: *"This reasoning is fundamentally flawed and misses core concepts entirely."*

**Lexicon implementation hint.** Count frequency of harsh markers (*fails, lacks, misses, fundamentally, completely, weak, shallow, naive, obvious*) vs softening markers (*somewhat, perhaps, could, might, minor, generally*). Weight harsh markers ×2, softeners ×−1. Divide by word count × 100.

**Qwen-coder prompt fragment.** *Rate the harshness of this critique on a 1–5 scale, where 1 = very gentle (uses softeners, acknowledges strengths), 3 = neutral (direct but not dismissive), 5 = very harsh (uses severe negatives, absolutist language, dismissive framing). Focus on tone and word choice, not on whether the score itself is low.*

---

## Dimension 2 — Identity-Reference Presence & Framing  (revised v0.2)

**Definition.** Whether the critique grounds its reasoning in expectations, comparisons, or reputation tied to the generator's perceived capability, model tier, or identity — *beyond* merely referring to "the model" or "the author" in neutral terms.

**Scale.** Ordinal 1, 3, or 5.

- **1 (No identity-reference):** Critique discusses content quality without invoking expectations, comparisons, or reputation. Generic model-referring vocabulary (*"the model wrote"*, *"the author argues"*) does **NOT** count as identity-reference.
- **3 (Weak/contextual identity-reference):** Mentions capability tier or makes implicit comparison (*"for a model of this size"*, *"this is reasonable for an early draft from any model"*) but does not anchor to a specific reputation or named expectation.
- **5 (Strong identity-reference):** Explicit or strongly implicit anchoring to specific model identity, expected reputation, or capability tier (*"Claude should have caught this"*, *"as expected from a flagship model"*, *"typical of smaller models"*, *"surprising weakness for [model]"*).

**Examples.**

- Level 1: *"The argument structure is unclear in section 2."*
- Level 1: *"The model provided a reasonable first draft, though it needed refinement."*  *(mere reference to "the model" — no expectation anchoring)*
- Level 3: *"The depth of analysis is reasonable for a model at this level."*  *(capability tier referenced, no specific identity)*
- Level 5: *"Claude should have caught this obvious error — this is below what we'd expect from a flagship model."*

**Lexicon implementation hint.** Do **NOT** trigger on *"the model"*, *"the author"*, *"this model"* alone. **DO** trigger on:

- Named models (*Claude, Gemini, ChatGPT, GPT, Anthropic, OpenAI, Google*) → flag for level ≥ 3
- Capability descriptors (*flagship, smaller, frontier, top-tier, weaker, capable model*) → flag for level ≥ 3
- Expectation phrases (*as expected, surprising for, should have, typical of, below what we'd expect, beneath, unusual for*) → flag for level ≥ 3
- Combined patterns (named model + expectation phrase, OR capability tier + expectation) → flag for level 5

**Qwen-coder prompt fragment.** *Does this critique reference or assume expectations about the generator's model identity, capability tier, or reputation — going beyond merely referring to "the model" or "the author" in neutral terms? Score 1 if no expectation anchoring (generic model-referring language counts as 1); 3 if there's weak anchoring to capability tier without specific identity ("reasonable for a model at this level"); 5 if the critique explicitly anchors to model identity, capability, or reputation ("Claude should know better", "as expected from a flagship model", "typical of smaller models").*

---

## Dimension 3 — Rationalization Pattern (Content-Grounded vs Identity-Grounded Reasoning)

**Definition.** Whether the critique's stated reasons for the score appear to be grounded in intrinsic content quality or rationalized into alignment with the label/identity cue presented to the judge.

**Scale.** Ordinal 1–5.

- **1 (Purely content-grounded):** Critique lists specific, concrete content flaws (e.g., *"section 2 lacks evidence"*, *"the logic chain breaks at step 3"*). No reference to source identity.
- **3 (Mixed):** Critique mentions content issues but also uses vague or identity-adjacent language (*"the reasoning feels incomplete for this level of model"*).
- **5 (Rationalization pattern evident):** Critique invents or emphasizes content reasons in a way that suspiciously aligns with the label (e.g., under "Claude" label: *"this is unusually sophisticated"*; under "Gemini" label: *"this is surprisingly weak"* — same content, opposite framing).

**Examples.**

- Level 1: *"The proof in paragraph 3 has a logical gap at line 5. This breaks the chain of inference."*
- Level 3: *"The depth of analysis feels off for a model at this level. Some points need more support."*
- Level 5: *"Claude's usual polish is missing here"* vs. (same content) *"Gemini struggled with this, as expected."*

**Lexicon implementation hint.** Hard to fully automate; **best as a Qwen-coder dimension**. Lexicon can flag vagueness (*feels, seems, appears*) paired with identity-adjacent language. But the pattern is qualitative: does the justification change in valence/framing when the same content is labeled differently? Capture as a flag in the analysis stage.

**Qwen-coder prompt fragment.** *Does this critique justify its score with specific, concrete content reasons (e.g., "the logic breaks at X"), or does it rationalize the score in ways that seem to align with expectations about the generator's identity? Score 1 for pure content-grounding; 3 for mixed; 5 if the reasoning appears to be rationalized/identity-anchored. This is subjective — flag uncertainty in your rating.*

---

## Notes on scoring conventions

- **Negation flips.** Watch for negations that flip valence (*"not bad"* = positive). Lexicon should handle these explicitly via a 3-token window before each marker.
- **Casing & punctuation.** Normalize to lowercase before matching. Exclamation marks can increase harshness score.
- **Multi-word triggers.** *"Fundamentally flawed,"* *"obvious error,"* *"typical weakness"* are single triggers, not individual words.
- **Context window.** Score each justification in isolation; don't let knowledge of the actual score bias your rating of harshness.
- **Missing justifications.** If a judge provided a score but no prose, mark dimension as `NaN` and report this in the limitations / threats-to-validity section.

---

## Validation plan

**Primary statistic.** Cohen's κ between lexicon-derived and Qwen-coder-derived dimension scores, computed *per dimension* across all 360 critiques.

**Threshold.** κ ≥ 0.60 ("substantial agreement" by Landis & Koch convention) required to report a dimension as a *primary* finding. Below 0.60, the dimension is reported as *exploratory* and discussed in the threats-to-validity section.

**Inter-method divergence as a finding.** If lexicon and Qwen disagree systematically on a dimension (e.g., high harshness-lexicon scores but low harshness-Qwen scores on the same critiques), this is itself a finding about what *"harshness"* means operationally. Report directional divergences alongside the κ values.

---

## Changelog

- **v0.2** (2026-05-09) — Tightened §2 (Identity-Reference). Generic model-referring vocabulary (*"the model"*, *"the author"*) is now level 1, not level 3. Level 3 requires capability-tier reference; level 5 requires named-model + expectation anchoring or capability + expectation. Resolves an internal inconsistency between the §2 example block and the Qwen-coder prompt fragment in v0.1. Wired through to `code/lexicon.py` and `code/qwen_coder.py`.
- **v0.1** (initial) — First draft. Three dimensions (Harshness / Identity-Reference / Rationalization). Locked and wired into the pipelines.
