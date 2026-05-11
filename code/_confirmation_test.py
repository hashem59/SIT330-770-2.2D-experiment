"""
_confirmation_test.py — confirmation analysis for the prose-asymmetry
finding. Replicates the pilot's paired Wilcoxon / permutation test on
the held-out 180, then computes the full-power point estimate on the
combined 360.

Sample stratification:
  - pilot:    titles 1-5 in artifacts/titles.json (n=15 paired per judge)
  - heldout:  titles 6-10 (n=15 paired per judge)
  - combined: all 10 titles (n=30 paired per judge)

Contrast: per (judge, blog_id) pair the Qwen-harshness rating when
label_shown="ChatGPT" vs label_shown="Claude". Sign convention:
Δ = ChatGPT − Claude. Positive Δ means harsher on ChatGPT-attributed prose.

Usage:
    python -m code._confirmation_test \
        --evaluations runs/evaluations.jsonl \
        --qwen runs/qwen-codings.csv \
        --titles artifacts/titles.json
"""
from __future__ import annotations
import argparse, csv, hashlib, json, sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

JUDGE_SHORT = {
    "openai/gpt-4o": "GPT-4o",
    "google/gemini-2.5-flash": "Gemini",
    "anthropic/claude-sonnet-4": "Claude",
}


def to_int(s):
    try:
        return int(float(s))
    except (TypeError, ValueError):
        return None


def paired_test(diffs: np.ndarray, *, n_perm: int = 10000, seed: int = 42):
    n = len(diffs)
    if n == 0:
        return {"n": 0}
    rng = np.random.default_rng(seed)
    md = float(np.mean(diffs))
    boot = np.array([np.mean(rng.choice(diffs, n, replace=True)) for _ in range(n_perm)])
    ci_lo = float(np.percentile(boot, 2.5))
    ci_hi = float(np.percentile(boot, 97.5))
    if np.all(diffs == 0):
        wilcox_stat = float("nan"); wilcox_p = 1.0
    else:
        wr = stats.wilcoxon(diffs, zero_method="zsplit")
        wilcox_stat = float(wr.statistic); wilcox_p = float(wr.pvalue)
    obs = abs(md); bigger = 0
    for _ in range(n_perm):
        signs = rng.choice([-1, 1], size=n)
        if abs(np.mean(diffs * signs)) >= obs:
            bigger += 1
    perm_p = (bigger + 1) / (n_perm + 1)
    return {
        "n": int(n),
        "mean_diff": md,
        "ci_lo": ci_lo,
        "ci_hi": ci_hi,
        "wilcox_stat": wilcox_stat,
        "wilcox_p": wilcox_p,
        "perm_p": float(perm_p),
        "n_pos": int((diffs > 0).sum()),
        "n_zero": int((diffs == 0).sum()),
        "n_neg": int((diffs < 0).sum()),
    }


def report(name, res):
    if res.get("n", 0) == 0:
        print(f"  {name:<28} NO PAIRS")
        return
    print(f"  {name:<28} n={res['n']:>3}  Δ={res['mean_diff']:+.3f}  "
          f"CI=[{res['ci_lo']:+.2f},{res['ci_hi']:+.2f}]  "
          f"W={res['wilcox_stat']:.1f}  p_w={res['wilcox_p']:.4f}  "
          f"p_perm={res['perm_p']:.4f}  signs={res['n_pos']}/{res['n_zero']}/{res['n_neg']}")


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--evaluations", required=True)
    p.add_argument("--qwen", required=True)
    p.add_argument("--titles", required=True)
    p.add_argument("--pilot-size", type=int, default=5)
    args = p.parse_args(argv)

    titles = json.loads(Path(args.titles).read_text())
    pilot_titles = set(titles[: args.pilot_size])
    heldout_titles = set(titles[args.pilot_size:])

    gens_path = Path(args.evaluations).parent / "generations.jsonl"
    blog2title = {}
    for line in gens_path.read_text().splitlines():
        g = json.loads(line)
        bid = hashlib.sha1(f"{g['model']}|{g['title']}".encode()).hexdigest()[:12]
        blog2title[bid] = g["title"]

    # Build (judge, blog_id) → label_shown → Qwen harshness, with split tag.
    table = defaultdict(dict)
    bid_split = {}
    for r in csv.DictReader(open(args.qwen)):
        h = to_int(r.get("qwen_harshness"))
        if h is None:
            continue
        title = blog2title.get(r["blog_id"])
        if title in pilot_titles:
            split = "pilot"
        elif title in heldout_titles:
            split = "heldout"
        else:
            continue
        bid_split[r["blog_id"]] = split
        table[(r["judge"], r["blog_id"])][r["label_shown"]] = h

    def collect(split, judge=None):
        diffs = []
        for (j, bid), shown in table.items():
            if judge is not None and j != judge:
                continue
            if bid_split.get(bid) != split and split != "combined":
                continue
            if "ChatGPT" in shown and "Claude" in shown:
                diffs.append(shown["ChatGPT"] - shown["Claude"])
        return np.array(diffs)

    # Collect per (split × judge) and combined non-OpenAI per split
    print("=" * 100)
    print("PROSE-ASYMMETRY CONFIRMATION TEST")
    print("Contrast: Qwen-harshness, label_shown=ChatGPT − label_shown=Claude (paired by judge × blog)")
    print("=" * 100)

    for split in ("pilot", "heldout", "combined"):
        print(f"\n--- {split.upper()} ---")
        for jm, jshort in JUDGE_SHORT.items():
            res = paired_test(collect(split, jm))
            report(jshort, res)
        # combined non-OpenAI
        diffs = []
        for jm in JUDGE_SHORT:
            if jm == "openai/gpt-4o":
                continue
            diffs.extend(list(collect(split, jm)))
        res = paired_test(np.array(diffs))
        report("non-OpenAI (Gem+Cla)", res)

    # Held-out vs pilot replication delta (per judge)
    print("\n" + "=" * 100)
    print("REPLICATION CHECK (held-out − pilot point estimates)")
    print("=" * 100)
    for jm, jshort in JUDGE_SHORT.items():
        p_res = paired_test(collect("pilot", jm))
        h_res = paired_test(collect("heldout", jm))
        if p_res.get("n", 0) and h_res.get("n", 0):
            print(f"  {jshort:<10}  pilot Δ={p_res['mean_diff']:+.3f}  "
                  f"held-out Δ={h_res['mean_diff']:+.3f}  "
                  f"shift={h_res['mean_diff'] - p_res['mean_diff']:+.3f}")


if __name__ == "__main__":
    main()
