"""
lexicon.py — Approach 1: rule-based scoring of judge justifications.

Implements the lexicon definitions from artifacts/codebook.md (v0.1).

Reads runs/evaluations.jsonl, applies the three codebook dimensions, writes
runs/lexicon-codings.csv with one row per evaluation.

Three dimensions:
  1. lexicon_harshness         — ordinal 1-5 (per codebook §1)
  2. lexicon_identity_reference — ordinal 1, 3, or 5 (per codebook §2)
  3. lexicon_rationalization   — ordinal 1, 3, or 5; codebook §3 notes
                                 this dimension is "best as a Qwen
                                 dimension"; the lexicon score is a
                                 best-effort proxy. Trust the Qwen
                                 column as primary for this dimension.

Scoring conventions implemented (per codebook):
  - Lowercase normalisation before matching.
  - Multi-word triggers matched before single-token triggers.
  - Negation handling: a 3-token window before each marker is scanned
    for any of {not, no, never, n't, without}; if found, the marker's
    contribution is sign-flipped.
  - Exclamation marks count as a small harshness booster.
  - Missing justification → all dimensions NaN.

Calibration note: the harshness density → ordinal mapping uses initial
fixed thresholds (HARSHNESS_BINS). After the pilot, recalibrate to the
empirical distribution and document the change in code comments + any
analysis output.
"""
from __future__ import annotations
import argparse, csv, json, math, re
from pathlib import Path

# ===========================================================================
# Dimension 1 — Critique Harshness
# ===========================================================================

HARSH_MULTI = [
    "fundamentally flawed", "obvious error", "typical weakness",
    "completely fails", "completely misses", "should not have",
    "below what we", "this is wrong", "fails entirely",
    "embarrassingly", "shockingly bad",
]

HARSH_SINGLE = [
    "fails", "fail", "failed",
    "lacks", "lacking",
    "misses", "missing",
    "fundamentally", "completely", "entirely", "utterly",
    "weak", "shallow", "naive", "obvious", "flawed",
    "wrong", "incorrect", "broken", "poorly",
]

SOFT_MULTI = [
    "could be", "might be", "may be", "to some extent", "in some ways",
    "for the most part", "on the whole",
]

SOFT_SINGLE = [
    "somewhat", "perhaps", "could", "might", "may",
    "minor", "generally", "mostly", "fairly", "slightly",
    "tends to", "arguably", "potentially",
]

NEGATION_TOKENS = {"not", "no", "never", "without"}      # plus n't via suffix check
NEGATION_WINDOW = 3

# density score → ordinal 1-5.
#
# CALIBRATION NOTE. These thresholds are calibrated for typical 60-150 word
# justifications (the prompt asks for that length). They will MIS-CLASSIFY
# very short test sentences (single-clause codebook examples) because one
# harsh marker in 10 words = density 20, which is high purely from the
# normalisation, not because the critique is actually severe.
#
# After the pilot (60 evaluations), recalibrate to the empirical density
# distribution and document the new thresholds in this comment block.
HARSHNESS_BINS = [
    (-math.inf,  0.0, 1),    # very gentle (soft-marker dominant)
    ( 0.0,       3.0, 2),    # gentle (mostly neutral, slight harsh tilt)
    ( 3.0,       8.0, 3),    # neutral (codebook centre)
    ( 8.0,      16.0, 4),    # harsh
    (16.0,  math.inf, 5),    # very harsh
]

# ===========================================================================
# Dimension 2 — Identity-Reference Presence & Framing
# ===========================================================================

MODEL_NAMES = [
    "claude", "gemini", "chatgpt", "gpt", "openai", "anthropic", "google",
]

# Codebook v0.2 §2: capability tiers split into strong-alone vs requires-context.
# Strong-alone descriptors are almost always model-context; phrase descriptors need
# the word "model" or a comparison cue to count.
CAPABILITY_STRONG = [
    "flagship", "frontier", "top-tier", "state-of-the-art", "state of the art",
]
CAPABILITY_PHRASES = [
    "smaller model", "weaker model", "capable model", "limited model",
    "well-known model", "well known model", "advanced model", "leading model",
    "frontier model", "flagship model", "top-tier model",
]
# Comparison patterns that imply capability-tier reasoning without naming a model.
# Detected via regex.
CAPABILITY_PATTERNS = [
    r"\bfor a model (of|at) this\b",   # "for a model of this size", "at this level"
    r"\bfor an? \w+ model\b",           # "for a smaller model", "for an early model"
    r"\bfrom any model\b",
    r"\bof this size\b",
    r"\bat this level\b",
]

EXPECTATION_PHRASES = [
    "as expected", "as one might expect", "as one would expect",
    "as we'd expect", "as we would expect",
    "surprising", "surprisingly", "unsurprising", "unsurprisingly",
    "typical of", "atypical for", "unusual for", "unusual that",
    "should know better", "should have caught", "should have been",
    "below what we", "above what we",
    "out of character", "out-of-character",
]

# ===========================================================================
# Dimension 3 — Rationalization Pattern (lexicon proxy; Qwen primary)
# ===========================================================================

VAGUE_MARKERS = [
    "feels", "seems", "appears", "comes across", "reads as",
    "gives the impression", "has a sense", "sense that",
]

CONTENT_GROUNDING_MARKERS = [
    # Specific structural references = content-grounded
    "section ", "paragraph ", "line ", "sentence ", "step ",
    "logical gap", "logical leap", "missing premise", "fallacy",
    "non sequitur", "evidence", "citation", "data point",
]

# ===========================================================================
# Helpers
# ===========================================================================

def _tokenise(text: str) -> list[str]:
    """Lowercase tokens, preserving negation suffixes."""
    return re.findall(r"[a-zA-Z']+|[!]", text.lower())


def _is_negated(tokens: list[str], idx: int) -> bool:
    """True if any negation token appears in the NEGATION_WINDOW preceding idx."""
    start = max(0, idx - NEGATION_WINDOW)
    for tok in tokens[start:idx]:
        if tok in NEGATION_TOKENS or tok.endswith("n't"):
            return True
    return False


def _count_phrase(text: str, phrases: list[str]) -> int:
    """Case-insensitive count of any phrase in `phrases` appearing in text."""
    t = text.lower()
    n = 0
    for ph in phrases:
        # Word-boundary on both ends for single-token, substring otherwise
        if " " in ph or "-" in ph:
            n += t.count(ph)
        else:
            n += len(re.findall(r"\b" + re.escape(ph) + r"\b", t))
    return n


def _density_score(text: str) -> float:
    """Harshness density from codebook §1 hint:
       (2 × harsh_count) − (1 × soft_count), normalised per 100 words.
       Multi-word triggers matched first; negation flips weights."""
    if not text:
        return 0.0
    t = text.lower()

    # Multi-word triggers first (avoid double-counting via single tokens later)
    harsh = 0
    soft = 0
    consumed_t = t
    for ph in HARSH_MULTI:
        c = consumed_t.count(ph)
        harsh += c
        consumed_t = consumed_t.replace(ph, " " * len(ph))
    for ph in SOFT_MULTI:
        c = consumed_t.count(ph)
        soft += c
        consumed_t = consumed_t.replace(ph, " " * len(ph))

    # Single-token triggers, with negation flip
    tokens = _tokenise(consumed_t)
    for i, tok in enumerate(tokens):
        if tok in HARSH_SINGLE:
            if _is_negated(tokens, i):
                soft += 1
            else:
                harsh += 1
        elif tok in SOFT_SINGLE:
            if _is_negated(tokens, i):
                harsh += 1
            else:
                soft += 1

    n_words = max(1, len(re.findall(r"\b\w+\b", t)))
    raw = (2 * harsh) - (1 * soft)
    density = 100.0 * raw / n_words

    # Exclamation booster
    excl_per_100 = 100.0 * t.count("!") / n_words
    density += 0.5 * excl_per_100

    return density


def harshness_score(text: str) -> int | None:
    """Map density score to ordinal 1-5."""
    if not text:
        return None
    d = _density_score(text)
    for lo, hi, level in HARSHNESS_BINS:
        if lo <= d < hi:
            return level
    return 3  # safety fallback


def identity_reference_score(text: str) -> int | None:
    """Codebook v0.2 §2: ordinal 1, 3, or 5.

    5 — strong: named model + expectation, OR capability + expectation,
        OR named model + capability.
    3 — weak/contextual: any one of {named model, expectation phrase,
        capability descriptor, capability comparison pattern} alone.
    1 — no identity-reference. Generic model-referring vocabulary
        ("the model", "the author") does NOT trigger.
    """
    if not text:
        return None
    t = text.lower()

    has_named_model = any(re.search(r"\b" + re.escape(n) + r"\b", t)
                          for n in MODEL_NAMES)
    has_expect = _count_phrase(text, EXPECTATION_PHRASES) > 0
    has_capability = (
        _count_phrase(text, CAPABILITY_STRONG) > 0
        or _count_phrase(text, CAPABILITY_PHRASES) > 0
        or any(re.search(p, t) for p in CAPABILITY_PATTERNS)
    )

    # Level 5: any two of the three signals
    if (has_named_model and has_expect) or \
       (has_named_model and has_capability) or \
       (has_capability and has_expect):
        return 5
    # Level 3: exactly one signal
    if has_named_model or has_expect or has_capability:
        return 3
    return 1


def rationalization_score(text: str) -> int | None:
    """Codebook §3: lexicon is a PROXY only; Qwen coder is primary.

    5 = vague marker AND identity-adjacent language present
    3 = vague marker alone, OR identity-adjacent without specific content
    1 = specific content-grounding markers dominate"""
    if not text:
        return None
    t = text.lower()
    vague = _count_phrase(text, VAGUE_MARKERS)
    grounding = _count_phrase(text, CONTENT_GROUNDING_MARKERS)
    has_identity_adjacent = identity_reference_score(text) >= 3

    if vague > 0 and has_identity_adjacent:
        return 5
    if vague > 0 or has_identity_adjacent:
        return 3
    if grounding >= 1:
        return 1
    return 3  # neutral default when ambiguous


# ===========================================================================
# Main
# ===========================================================================

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--evaluations", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()

    rows = []
    n_missing = 0
    for line in Path(args.evaluations).open():
        ev = json.loads(line)
        just = ev.get("justification") or ""
        if not just:
            n_missing += 1
        row = {
            "judge": ev["judge"], "blog_id": ev["blog_id"], "condition": ev["condition"],
            "true_label": ev["true_label"], "label_shown": ev["label_shown"],
            "lexicon_harshness": harshness_score(just),
            "lexicon_identity_reference": identity_reference_score(just),
            "lexicon_rationalization": rationalization_score(just),
            "lexicon_density_raw": round(_density_score(just), 3) if just else None,
            "response_id": ev.get("response_id"),
        }
        if ev.get("scores"):
            for k in ("coherence", "informativeness", "conciseness"):
                row[f"score_{k}"] = ev["scores"].get(k)
        rows.append(row)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        # Ensure stable column ordering
        cols = list(rows[0].keys())
        with out.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader(); w.writerows(rows)
    print(f"Wrote {len(rows)} rows to {out}  ({n_missing} with missing justification → NaN dimensions)")


if __name__ == "__main__":
    main()
