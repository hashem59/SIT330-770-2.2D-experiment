"""
_pilot_prose_analysis.py — one-shot analysis to characterise the prose channel
on the 180-row pilot subset.

Reads runs/lexicon-codings.csv and runs/qwen-codings.csv, joins on
(judge, blog_id, condition), and reports:

  1. Per-dimension means by (judge × label_shown)
  2. Per-dimension means by (judge × condition)
  3. Inter-method Cohen's kappa per dimension (lexicon vs Qwen)

Per-dimension means are reported for both the lexicon and Qwen channels.

This is a pilot-read tool, not the analysis-stage tool. /analyze (Step 8)
remains the canonical analysis entry point.
"""
from __future__ import annotations
import csv
import sys
from collections import defaultdict
from statistics import mean, stdev

DIMENSIONS = ["harshness", "identity_reference", "rationalization"]
LEX_KEY = lambda d: f"lexicon_{d}"
QWEN_KEY = lambda d: f"qwen_{d}"

CONDITIONS = ["none", "true_label", "false_label_1", "false_label_2"]
LABELS = ["unattributed", "ChatGPT", "Gemini", "Claude"]
JUDGES_SHORT = {
    "openai/gpt-4o": "GPT-4o",
    "google/gemini-2.5-flash": "Gemini",
    "anthropic/claude-sonnet-4": "Claude",
}


def load_csv(path):
    return list(csv.DictReader(open(path)))


def to_int(s):
    try:
        if s == "" or s is None:
            return None
        return int(float(s))
    except ValueError:
        return None


def join(lex_rows, qwen_rows):
    qwen_by_key = {(r["judge"], r["blog_id"], r["condition"]): r for r in qwen_rows}
    out = []
    for lr in lex_rows:
        k = (lr["judge"], lr["blog_id"], lr["condition"])
        qr = qwen_by_key.get(k)
        if not qr:
            continue
        merged = dict(lr)
        for d in DIMENSIONS:
            merged[QWEN_KEY(d)] = qr.get(QWEN_KEY(d), "")
        out.append(merged)
    return out


def cohens_kappa(a, b):
    """Weighted (linear) kappa for ordinal scales 1..5."""
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if not pairs:
        return float("nan"), 0
    n = len(pairs)
    cats = sorted({x for x, _ in pairs} | {y for _, y in pairs})
    K = len(cats)
    idx = {c: i for i, c in enumerate(cats)}
    obs = [[0] * K for _ in range(K)]
    for x, y in pairs:
        obs[idx[x]][idx[y]] += 1
    row_tot = [sum(r) for r in obs]
    col_tot = [sum(obs[i][j] for i in range(K)) for j in range(K)]
    # Linear weights w_ij = 1 - |i - j| / (K - 1)
    if K == 1:
        return 1.0, n  # degenerate but trivially perfect
    def w(i, j):
        return 1 - abs(i - j) / (K - 1)
    obs_sum = sum(w(i, j) * obs[i][j] for i in range(K) for j in range(K)) / n
    exp_sum = sum(w(i, j) * row_tot[i] * col_tot[j] for i in range(K) for j in range(K)) / (n * n)
    if exp_sum >= 1.0:
        return float("nan"), n
    return (obs_sum - exp_sum) / (1 - exp_sum), n


def fmt_mean(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return "  -- "
    if len(vals) == 1:
        return f"{vals[0]:4.2f}"
    return f"{mean(vals):4.2f}±{stdev(vals):3.2f}"


def main():
    lex = load_csv("runs/lexicon-codings.csv")
    qwen = load_csv("runs/qwen-codings.csv")
    print(f"Lexicon rows: {len(lex)}  Qwen rows: {len(qwen)}")
    rows = join(lex, qwen)
    print(f"Joined rows: {len(rows)}")
    print()

    # 1. Means by (judge × label_shown), per dimension, per channel
    print("=" * 90)
    print("1. PER-DIMENSION MEANS BY (JUDGE × LABEL SHOWN)")
    print("=" * 90)
    for channel, key_fn in (("LEXICON", LEX_KEY), ("QWEN", QWEN_KEY)):
        print(f"\n--- {channel} ---")
        for d in DIMENSIONS:
            print(f"\n  {d}:")
            print(f"    {'judge':<10} {'unattrib':>10} {'ChatGPT':>10} {'Gemini':>10} {'Claude':>10}")
            for jm, jshort in JUDGES_SHORT.items():
                cells = []
                for lab in LABELS:
                    vals = [to_int(r[key_fn(d)]) for r in rows
                            if r["judge"] == jm and r["label_shown"] == lab]
                    cells.append(fmt_mean(vals))
                print(f"    {jshort:<10} " + " ".join(f"{c:>10}" for c in cells))

    # 2. Means by (judge × condition)
    print("\n" + "=" * 90)
    print("2. PER-DIMENSION MEANS BY (JUDGE × CONDITION)")
    print("=" * 90)
    for channel, key_fn in (("LEXICON", LEX_KEY), ("QWEN", QWEN_KEY)):
        print(f"\n--- {channel} ---")
        for d in DIMENSIONS:
            print(f"\n  {d}:")
            print(f"    {'judge':<10} " + " ".join(f"{c:>14}" for c in CONDITIONS))
            for jm, jshort in JUDGES_SHORT.items():
                cells = []
                for c in CONDITIONS:
                    vals = [to_int(r[key_fn(d)]) for r in rows
                            if r["judge"] == jm and r["condition"] == c]
                    cells.append(fmt_mean(vals))
                print(f"    {jshort:<10} " + " ".join(f"{c:>14}" for c in cells))

    # 3. Inter-method Cohen's kappa per dimension (linear-weighted, ordinal)
    print("\n" + "=" * 90)
    print("3. INTER-METHOD COHEN'S KAPPA (lexicon vs Qwen, linear-weighted ordinal)")
    print("=" * 90)
    print(f"\n  {'dimension':<22} {'kappa':>8} {'n':>6}  {'agreement':<25}")
    for d in DIMENSIONS:
        a = [to_int(r[LEX_KEY(d)]) for r in rows]
        b = [to_int(r[QWEN_KEY(d)]) for r in rows]
        kappa, n = cohens_kappa(a, b)
        if kappa != kappa:  # NaN
            agr = "n/a"
        elif kappa < 0:
            agr = "worse than chance"
        elif kappa < 0.20:
            agr = "slight"
        elif kappa < 0.40:
            agr = "fair"
        elif kappa < 0.60:
            agr = "moderate"
        elif kappa < 0.80:
            agr = "substantial"
        else:
            agr = "almost perfect"
        print(f"  {d:<22} {kappa:>8.3f} {n:>6}  {agr}")

    # 4. Direction check on the prose channel: does ANY dimension show
    #    a true_label vs false_label_1 contrast > 0.3 ordinal points?
    print("\n" + "=" * 90)
    print("4. PROSE CHANNEL DIRECTION CHECK (true_label − false_label_1, both channels)")
    print("=" * 90)
    print(f"\n  {'dimension':<22} {'channel':<10} {'Δ(true−false_1)':>18}")
    for d in DIMENSIONS:
        for channel, key_fn in (("LEXICON", LEX_KEY), ("QWEN", QWEN_KEY)):
            t_vals = [to_int(r[key_fn(d)]) for r in rows if r["condition"] == "true_label"]
            f_vals = [to_int(r[key_fn(d)]) for r in rows if r["condition"] == "false_label_1"]
            t_vals = [v for v in t_vals if v is not None]
            f_vals = [v for v in f_vals if v is not None]
            if not t_vals or not f_vals:
                print(f"  {d:<22} {channel:<10} {'--':>18}")
                continue
            delta = mean(t_vals) - mean(f_vals)
            print(f"  {d:<22} {channel:<10} {delta:>+18.3f}")


if __name__ == "__main__":
    main()
