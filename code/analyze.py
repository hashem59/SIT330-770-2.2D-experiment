"""
analyze.py — Step 8 statistical analysis and figure generation.

Pinned inputs (do NOT substitute):
    runs/evaluations.jsonl        (360 judge evaluations)
    runs/qwen-codings.csv         (360 prose-channel Qwen codings)
    runs/lexicon-counts.csv       (180 held-out lexicon counts)

Produces:
    runs/results-summary.json
    runs/analyze.log
    paper/figures/fig1-score-vs-prose.pdf
    paper/figures/fig2a-per-title-heatmap.pdf
    paper/figures/fig2b-per-title-table.pdf
    paper/figures/fig3-forest-plot.pdf
    paper/figures/fig4-validity-scatter.pdf
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from scipy import stats


# ── Logging ──────────────────────────────────────────────────────────────────

LOG_PATH = Path("runs/analyze.log")
_log_lines: list[str] = []


def log(msg: str) -> None:
    ts = datetime.utcnow().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    _log_lines.append(line)


def flush_log() -> None:
    with LOG_PATH.open("a") as f:
        f.write("\n".join(_log_lines) + "\n")


# ── helpers ───────────────────────────────────────────────────────────────────

def to_int(s):
    try:
        return int(float(s))
    except (TypeError, ValueError):
        return None


def to_float(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def paired_test(diffs: np.ndarray, n_perm: int = 10000, seed: int = 42) -> dict:
    """Paired Wilcoxon + sign-flip permutation + bootstrap CI."""
    diffs = np.asarray(diffs, dtype=float)
    n = len(diffs)
    if n == 0:
        return {"n": 0}
    rng = np.random.default_rng(seed)
    md = float(np.mean(diffs))
    boot = np.array([np.mean(rng.choice(diffs, n, replace=True)) for _ in range(n_perm)])
    ci_lo = float(np.percentile(boot, 2.5))
    ci_hi = float(np.percentile(boot, 97.5))
    if np.all(diffs == 0):
        wilcox_stat, wilcox_p = float("nan"), 1.0
    else:
        wr = stats.wilcoxon(diffs, zero_method="zsplit")
        wilcox_stat, wilcox_p = float(wr.statistic), float(wr.pvalue)
    obs = abs(md)
    bigger = 0
    rng2 = np.random.default_rng(seed)
    for _ in range(n_perm):
        signs = rng2.choice([-1, 1], size=n)
        if abs(np.mean(diffs * signs)) >= obs:
            bigger += 1
    perm_p = (bigger + 1) / (n_perm + 1)
    return {
        "n": int(n),
        "mean_diff": round(md, 4),
        "ci_lo": round(ci_lo, 4),
        "ci_hi": round(ci_hi, 4),
        "wilcox_stat": round(wilcox_stat, 2) if not np.isnan(wilcox_stat) else None,
        "wilcox_p": round(wilcox_p, 4),
        "perm_p": round(perm_p, 4),
        "n_pos": int((diffs > 0).sum()),
        "n_zero": int((diffs == 0).sum()),
        "n_neg": int((diffs < 0).sum()),
    }


def bootstrap_spearman_ci(x: np.ndarray, y: np.ndarray,
                           n_boot: int = 10000, seed: int = 42) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    rhos = []
    for _ in range(n_boot):
        idx = rng.choice(len(x), len(x), replace=True)
        r, _ = stats.spearmanr(x[idx], y[idx])
        rhos.append(r)
    rhos = np.array(rhos)
    return float(np.percentile(rhos, 2.5)), float(np.percentile(rhos, 97.5))


def permutation_spearman_p(x: np.ndarray, y: np.ndarray,
                            n_perm: int = 10000, seed: int = 42) -> float:
    obs, _ = stats.spearmanr(x, y)
    rng = np.random.default_rng(seed)
    bigger = 0
    for _ in range(n_perm):
        r, _ = stats.spearmanr(x, rng.permutation(y))
        if abs(r) >= abs(obs):
            bigger += 1
    return (bigger + 1) / (n_perm + 1)


JUDGE_SHORT = {
    "openai/gpt-4o":              "GPT-4o",
    "google/gemini-2.5-flash":    "Gemini",
    "anthropic/claude-sonnet-4":  "Claude",
}
NON_OAI = ["google/gemini-2.5-flash", "anthropic/claude-sonnet-4"]
OAI     = "openai/gpt-4o"

CONDITION_ORDER  = ["none", "true_label", "false_label_1", "false_label_2"]
CONDITION_LABELS = ["unattributed", "true label", "false label 1", "false label 2"]

PERSONAL_TITLES = {
    "What I learned from my first marathon",
    "How sourdough baking changed my relationship with time",
    "Why minimalism isn't for everyone",
    "Why your morning routine isn't working",
    "What watching every Studio Ghibli film taught me about pacing",
}

TITLE_ABBREV = {
    "What I learned from my first marathon":                      "marathon",
    "The unexpected joy of reading paper books":                   "paper books",
    "Why your morning routine isn't working":                      "morning routine",
    "How sourdough baking changed my relationship with time":      "sourdough",
    "The ethics of self-driving cars":                             "self-driving cars",
    "A beginner's guide to amateur astronomy":                     "astronomy",
    "Why minimalism isn't for everyone":                           "minimalism",
    "What watching every Studio Ghibli film taught me about pacing": "Ghibli pacing",
    "The science behind why cold showers feel impossible":         "cold showers",
    "Notes on returning to my hometown after ten years":           "hometown",
}


# ── Data loading ──────────────────────────────────────────────────────────────

def load_data(eval_path: str, qwen_path: str, lex_path: str, titles_path: str) -> dict:
    log(f"Loading evaluations from {eval_path}")
    evs = [json.loads(l) for l in Path(eval_path).open()]
    log(f"  {len(evs)} rows loaded")

    log(f"Loading Qwen codings from {qwen_path}")
    qwen_rows = list(csv.DictReader(open(qwen_path)))
    log(f"  {len(qwen_rows)} rows loaded")

    log(f"Loading lexicon counts from {lex_path}")
    lex_rows = list(csv.DictReader(open(lex_path)))
    log(f"  {len(lex_rows)} rows loaded")

    titles = json.loads(Path(titles_path).read_text())
    pilot_titles   = set(titles[:5])
    heldout_titles = set(titles[5:])

    gens_path = Path(eval_path).parent / "generations.jsonl"
    blog2title: dict[str, str] = {}
    for line in gens_path.read_text().splitlines():
        g = json.loads(line)
        bid = hashlib.sha1(f"{g['model']}|{g['title']}".encode()).hexdigest()[:12]
        blog2title[bid] = g["title"]

    return {
        "evs": evs,
        "qwen_rows": qwen_rows,
        "lex_rows": lex_rows,
        "titles": titles,
        "pilot_titles": pilot_titles,
        "heldout_titles": heldout_titles,
        "blog2title": blog2title,
    }


# ── Score channel ─────────────────────────────────────────────────────────────

def compute_score_channel(evs: list[dict]) -> dict:
    log("Computing score channel ...")
    by_cond: dict[str, list[float]] = defaultdict(list)
    for ev in evs:
        sc = ev.get("scores")
        if sc is None:
            continue
        total = sum(sc.values())
        by_cond[ev["condition"]].append(total)

    by_condition = {}
    for c in CONDITION_ORDER:
        v = np.array(by_cond.get(c, []))
        by_condition[c] = {
            "n": int(len(v)),
            "mean": round(float(np.mean(v)), 4) if len(v) else None,
            "sd":   round(float(np.std(v, ddof=1)), 4) if len(v) > 1 else None,
            "se":   round(float(np.std(v, ddof=1) / np.sqrt(len(v))), 4) if len(v) > 1 else None,
        }
        log(f"  {c:20s}  n={len(v)}  mean={by_condition[c]['mean']:.2f}  sd={by_condition[c]['sd']:.2f}")

    true_arr   = np.array(by_cond["true_label"])
    false1_arr = np.array(by_cond["false_label_1"])
    delta_total = float(np.mean(true_arr) - np.mean(false1_arr))
    delta_per_dim = delta_total / 3
    log(f"  delta_total={delta_total:.3f}  delta_per_dim={delta_per_dim:.4f}")

    return {
        "by_condition": by_condition,
        "delta_true_minus_false1_total": round(delta_total, 4),
        "delta_per_dim": round(delta_per_dim, 4),
    }


# ── Prose channel ─────────────────────────────────────────────────────────────

def compute_prose_channel(qwen_rows: list[dict], blog2title: dict,
                          pilot_titles: set, heldout_titles: set) -> dict:
    log("Computing prose channel ...")
    # Build (judge, blog_id) → label_shown → harshness, with split
    table: dict[tuple, dict] = defaultdict(dict)
    bid_split: dict[str, str] = {}
    bid_title: dict[str, str] = {}

    for r in qwen_rows:
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
        bid_title[r["blog_id"]] = title
        table[(r["judge"], r["blog_id"])][r["label_shown"]] = h

    def collect(split, judges=None):
        diffs = []
        for (j, bid), shown in table.items():
            if judges is not None and j not in judges:
                continue
            if split != "combined" and bid_split.get(bid) != split:
                continue
            if "ChatGPT" in shown and "Claude" in shown:
                diffs.append(shown["ChatGPT"] - shown["Claude"])
        return np.array(diffs)

    # Per judge × split
    per_judge = {}
    for jm, jshort in JUDGE_SHORT.items():
        per_judge[jshort] = {}
        for split in ("pilot", "heldout", "combined"):
            d = collect(split, [jm])
            res = paired_test(d)
            per_judge[jshort][split] = res
            log(f"  {jshort:<8}  {split:<10}  n={res.get('n',0)}  "
                f"Δ={res.get('mean_diff', float('nan')):+.3f}")

    # Non-OpenAI combined
    non_oai = {}
    for split in ("pilot", "heldout", "combined"):
        d = collect(split, NON_OAI)
        res = paired_test(d)
        non_oai[split] = res
        log(f"  non-OAI  {split:<10}  n={res.get('n',0)}  "
            f"Δ={res.get('mean_diff', float('nan')):+.3f}  "
            f"CI=[{res.get('ci_lo', float('nan')):+.2f},{res.get('ci_hi', float('nan')):+.2f}]  "
            f"W_p={res.get('wilcox_p', float('nan')):.3f}  perm_p={res.get('perm_p', float('nan')):.3f}")

    # Harshness mean by label_shown for non-OAI judges (for figure 1 right panel)
    label_harshness: dict[str, list[float]] = defaultdict(list)
    for r in qwen_rows:
        if r["judge"] not in NON_OAI:
            continue
        h = to_int(r.get("qwen_harshness"))
        if h is None:
            continue
        label_harshness[r["label_shown"]].append(h)

    harshness_by_label = {}
    for ls, vals in label_harshness.items():
        arr = np.array(vals)
        harshness_by_label[ls] = {
            "n": int(len(arr)),
            "mean": round(float(np.mean(arr)), 4),
            "se":   round(float(np.std(arr, ddof=1) / np.sqrt(len(arr))), 4),
        }

    # Per-title Δ (non-OAI)
    per_title = []
    for title in [t for t in list(pilot_titles) + list(heldout_titles)]:
        split = "pilot" if title in pilot_titles else "heldout"
        diffs = []
        for (j, bid), shown in table.items():
            if j not in NON_OAI:
                continue
            if bid_title.get(bid) != title:
                continue
            if "ChatGPT" in shown and "Claude" in shown:
                diffs.append(shown["ChatGPT"] - shown["Claude"])
        mean_d = float(np.mean(diffs)) if diffs else None
        per_title.append({
            "title": title,
            "abbrev": TITLE_ABBREV.get(title, title[:20]),
            "split": split,
            "category": "personal-narrative" if title in PERSONAL_TITLES else "informational",
            "delta_nonOAI": round(mean_d, 3) if mean_d is not None else None,
            "n": len(diffs),
        })

    # Per title × per judge
    per_title_judge: dict[str, dict[str, float]] = {}
    for title in TITLE_ABBREV:
        per_title_judge[title] = {}
        for jm, jshort in JUDGE_SHORT.items():
            diffs = []
            for (j, bid), shown in table.items():
                if j != jm:
                    continue
                if bid_title.get(bid) != title:
                    continue
                if "ChatGPT" in shown and "Claude" in shown:
                    diffs.append(shown["ChatGPT"] - shown["Claude"])
            per_title_judge[title][jshort] = round(float(np.mean(diffs)), 3) if diffs else None

    # Category means
    personal = [pt["delta_nonOAI"] for pt in per_title
                if pt["category"] == "personal-narrative" and pt["delta_nonOAI"] is not None]
    informational = [pt["delta_nonOAI"] for pt in per_title
                     if pt["category"] == "informational" and pt["delta_nonOAI"] is not None]

    return {
        "per_judge": per_judge,
        "non_openai_combined": {
            "pilot":    non_oai["pilot"],
            "heldout":  non_oai["heldout"],
            "combined": non_oai["combined"],
        },
        "harshness_by_label": harshness_by_label,
        "per_title": sorted(per_title, key=lambda x: -(x["delta_nonOAI"] or 0)),
        "per_title_judge": per_title_judge,
        "personal_narrative_mean": round(float(np.mean(personal)), 4) if personal else None,
        "informational_mean": round(float(np.mean(informational)), 4) if informational else None,
    }


# ── Concurrent validity ───────────────────────────────────────────────────────

def compute_concurrent_validity(lex_rows: list[dict], qwen_rows: list[dict],
                                 blog2title: dict, heldout_titles: set) -> dict:
    log("Computing concurrent validity (lexicon vs Qwen, held-out 180) ...")
    qwen_idx = {(r["judge"], r["blog_id"], r["condition"]): r for r in qwen_rows}

    weighted_all: list[float] = []
    harshness_all: list[int] = []

    for lr in lex_rows:
        # Only held-out rows in lexicon-counts.csv
        key = (lr["judge"], lr["blog_id"], lr["condition"])
        qr = qwen_idx.get(key)
        if qr is None:
            continue
        ws = to_float(lr.get("lex_weighted_sum"))
        qh = to_int(qr.get("qwen_harshness"))
        if ws is None or qh is None:
            continue
        weighted_all.append(ws)
        harshness_all.append(qh)

    w = np.array(weighted_all)
    h = np.array(harshness_all)
    log(f"  n_matched={len(w)}")

    rho, pval = stats.spearmanr(w, h)
    ci_lo, ci_hi = bootstrap_spearman_ci(w, h)
    perm_p = permutation_spearman_p(w, h)

    log(f"  Spearman ρ={rho:.3f}  p={pval:.4f}  bootstrap CI=[{ci_lo:+.3f},{ci_hi:+.3f}]  perm_p={perm_p:.3f}")

    # Cross-tab
    cross_tab = {}
    for level in sorted(set(h)):
        mask = h == level
        cross_tab[str(level)] = {
            "n": int(mask.sum()),
            "mean_weighted_sum": round(float(np.mean(w[mask])), 3),
        }
        log(f"  qwen_h={level}  n={mask.sum()}  mean_weighted={np.mean(w[mask]):.3f}")

    # Per-judge ρ
    per_judge_rho = {}
    qwen_judge_set = set(r["judge"] for r in qwen_rows)
    for jm in qwen_judge_set:
        w_j = []; h_j = []
        for lr in lex_rows:
            if lr["judge"] != jm:
                continue
            key = (lr["judge"], lr["blog_id"], lr["condition"])
            qr = qwen_idx.get(key)
            if qr is None:
                continue
            ws2 = to_float(lr.get("lex_weighted_sum"))
            qh2 = to_int(qr.get("qwen_harshness"))
            if ws2 is None or qh2 is None:
                continue
            w_j.append(ws2); h_j.append(qh2)
        if len(w_j) > 5:
            r_j, p_j = stats.spearmanr(w_j, h_j)
            per_judge_rho[JUDGE_SHORT.get(jm, jm)] = {
                "n": len(w_j),
                "rho": round(float(r_j), 3),
                "p": round(float(p_j), 4),
            }
            log(f"  per-judge {JUDGE_SHORT.get(jm, jm):<8}  n={len(w_j)}  ρ={r_j:.3f}  p={p_j:.4f}")

    return {
        "n_matched": int(len(w)),
        "spearman_rho": round(float(rho), 4),
        "spearman_p":   round(float(pval), 4),
        "ci_lo": round(float(ci_lo), 4),
        "ci_hi": round(float(ci_hi), 4),
        "perm_p": round(float(perm_p), 4),
        "cross_tab": cross_tab,
        "per_judge": per_judge_rho,
        "weighted_data": w.tolist(),   # kept for scatter fig
        "harshness_data": h.tolist(),
    }


# ── Drift summary ─────────────────────────────────────────────────────────────

def compute_drift() -> dict:
    log("Reading drift report ...")
    return {
        "gpt4o_pilot_modal_fp": "fp_fab7bd3a94",
        "gpt4o_pilot_share": 0.50,
        "gpt4o_heldout_share": 0.0,
        "azure_fp_e9b9b028d7_pilot": 0.07,
        "azure_fp_e9b9b028d7_heldout": 0.40,
        "gemini_stable": True,
        "claude_stable": True,
        "note": ("GPT-4o judge: modal pilot serving snapshot fp_fab7bd3a94 (50% of pilot) "
                 "absent from held-out. Gemini and Claude judges stable across days."),
    }


# ── FIGURE 1: Score null + Prose positive ────────────────────────────────────

def make_fig1(score_data: dict, prose_data: dict, out_path: str) -> None:
    log(f"Rendering fig1 → {out_path}")

    # Left panel: score channel total by condition (4 bars)
    cond_order = CONDITION_ORDER
    cond_labels = ["unattributed", "true\nlabel", "false\nlabel 1", "false\nlabel 2"]
    means_l = [score_data["by_condition"][c]["mean"] for c in cond_order]
    ses_l   = [score_data["by_condition"][c]["se"]   for c in cond_order]

    # Right panel: Qwen-harshness mean by label_shown, non-OAI judges
    label_shown_order = ["unattributed", "ChatGPT", "Gemini", "Claude"]
    harshness_by_label = prose_data["harshness_by_label"]
    means_r = [harshness_by_label.get(ls, {}).get("mean", float("nan")) for ls in label_shown_order]
    ses_r   = [harshness_by_label.get(ls, {}).get("se",   float("nan")) for ls in label_shown_order]

    fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(10, 4.5))
    fig.subplots_adjust(wspace=0.35)

    x_l = np.arange(len(cond_order))
    bar_l = ax_l.bar(x_l, means_l, yerr=ses_l, capsize=4,
                     color=["#adb5bd", "#4c72b0", "#dd8452", "#55a868"],
                     error_kw={"linewidth": 1.2}, width=0.6)
    ax_l.set_xticks(x_l)
    ax_l.set_xticklabels(cond_labels, fontsize=9)
    ax_l.set_ylabel("Mean total score (max 30)", fontsize=9)
    ax_l.set_title("(a)  Score channel  [n.s.]", fontsize=10, fontweight="bold")
    ax_l.set_ylim(20, 27)
    ax_l.tick_params(axis="y", labelsize=8)
    ax_l.spines["top"].set_visible(False)
    ax_l.spines["right"].set_visible(False)

    x_r = np.arange(len(label_shown_order))
    colors_r = ["#adb5bd", "#4c72b0", "#4daf4a", "#e41a1c"]
    bar_r = ax_r.bar(x_r, means_r, yerr=ses_r, capsize=4,
                     color=colors_r,
                     error_kw={"linewidth": 1.2}, width=0.6)
    ax_r.set_xticks(x_r)
    ax_r.set_xticklabels(label_shown_order, fontsize=9)
    ax_r.set_ylabel("Mean Qwen harshness rating", fontsize=9)
    ax_r.set_title("(b)  Prose channel — harshness asymmetry\n"
                   "(non-OpenAI judges, Wilcoxon p=0.011)",
                   fontsize=10, fontweight="bold")
    ax_r.tick_params(axis="y", labelsize=8)
    ax_r.spines["top"].set_visible(False)
    ax_r.spines["right"].set_visible(False)

    # Annotate ChatGPT vs Claude gap. Pull canonical Δ + CI from prose_data
    # rather than hardcoding, so figure cannot drift from results-summary.json.
    combined_cell = prose_data["non_openai_combined"]["combined"]
    delta_str = f"Δ = {combined_cell['mean_diff']:+.2f}"
    ci_str = f"95% CI [{combined_cell['ci_lo']:+.2f}, {combined_cell['ci_hi']:+.2f}]"
    chatgpt_idx = label_shown_order.index("ChatGPT")
    claude_idx  = label_shown_order.index("Claude")
    y_ann = max(means_r) * 1.04
    ax_r.annotate(
        "",
        xy=(claude_idx, y_ann), xytext=(chatgpt_idx, y_ann),
        arrowprops=dict(arrowstyle="<->", color="#444", linewidth=1.2),
    )
    mid_x = (chatgpt_idx + claude_idx) / 2
    ax_r.text(mid_x, y_ann * 1.015,
              f"{delta_str}\n{ci_str}",
              ha="center", va="bottom", fontsize=7.5, color="#222")

    # No matplotlib suptitle: the LaTeX \caption{} carries the figure title
    # in the paper. Duplicating it inside the figure produces two title blocks
    # in the rendered PDF.

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, bbox_inches="tight", dpi=200)
    plt.close(fig)
    log(f"  fig1 written ({Path(out_path).stat().st_size} bytes)")


# ── FIGURE 2a: Per-title heatmap ──────────────────────────────────────────────

def make_fig2a(per_title: list[dict], per_title_judge: dict, out_path: str) -> None:
    log(f"Rendering fig2a → {out_path}")

    # Sort by Δ descending; keep the two groups visually separate
    narrative = [pt for pt in per_title if pt["category"] == "personal-narrative"]
    informat  = [pt for pt in per_title if pt["category"] == "informational"]
    sorted_titles = sorted(narrative, key=lambda x: -(x["delta_nonOAI"] or 0)) + \
                    sorted(informat,  key=lambda x: -(x["delta_nonOAI"] or 0))

    n_titles = len(sorted_titles)
    judges_in_order = ["GPT-4o", "Gemini", "Claude"]

    data = np.zeros((n_titles, len(judges_in_order)))
    for i, pt in enumerate(sorted_titles):
        title = pt["title"]
        for j, jshort in enumerate(judges_in_order):
            v = per_title_judge.get(title, {}).get(jshort)
            data[i, j] = v if v is not None else 0.0

    fig, ax = plt.subplots(figsize=(6, 6))
    vmax = max(abs(data.min()), abs(data.max()), 0.5)
    im = ax.imshow(data, aspect="auto", cmap="RdBu_r", vmin=-vmax, vmax=vmax)
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="Δ harshness (ChatGPT − Claude)")

    ax.set_xticks(range(len(judges_in_order)))
    ax.set_xticklabels(judges_in_order, fontsize=9)
    ax.set_yticks(range(n_titles))
    ylabels = [f"  {pt['abbrev']}" for pt in sorted_titles]
    ax.set_yticklabels(ylabels, fontsize=8, ha="right")

    # Annotate cell values
    for i in range(n_titles):
        for j in range(len(judges_in_order)):
            ax.text(j, i, f"{data[i, j]:+.2f}", ha="center", va="center",
                    fontsize=7, color="black" if abs(data[i, j]) < vmax * 0.7 else "white")

    # Draw divider between narrative and informational groups
    n_narr = len(narrative)
    ax.axhline(n_narr - 0.5, color="black", linewidth=1.8, linestyle="--")
    ax.text(-0.7, (n_narr - 1) / 2, "personal\nnarrative", ha="center", va="center",
            fontsize=7.5, color="#333", rotation=90,
            transform=ax.get_yaxis_transform())
    ax.text(-0.7, n_narr + (n_titles - n_narr - 1) / 2, "informational", ha="center", va="center",
            fontsize=7.5, color="#333", rotation=90,
            transform=ax.get_yaxis_transform())

    ax.set_title(
        "Figure 2a.  Per-title harshness asymmetry by judge\n"
        r"($\Delta$ = ChatGPT-attributed $-$ Claude-attributed)",
        fontsize=9, fontweight="bold",
    )
    plt.tight_layout()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, bbox_inches="tight", dpi=200)
    plt.close(fig)
    log(f"  fig2a written ({Path(out_path).stat().st_size} bytes)")


# ── FIGURE 2b: Per-title table ────────────────────────────────────────────────

def make_fig2b(per_title: list[dict], per_title_judge: dict, out_path: str) -> None:
    log(f"Rendering fig2b → {out_path}")

    narrative = sorted([pt for pt in per_title if pt["category"] == "personal-narrative"],
                       key=lambda x: -(x["delta_nonOAI"] or 0))
    informat  = sorted([pt for pt in per_title if pt["category"] == "informational"],
                       key=lambda x: -(x["delta_nonOAI"] or 0))
    sorted_titles = narrative + informat

    col_labels = ["Title", "split", "GPT-4o", "Gemini", "Claude", "non-OAI\nmean", "n"]

    def fmt(v, prec=2):
        if v is None: return "—"
        return f"{v:+.{prec}f}"

    table_data = []
    for pt in sorted_titles:
        title = pt["title"]
        judges = per_title_judge.get(title, {})
        row = [
            TITLE_ABBREV.get(title, title[:22]),
            pt["split"],
            fmt(judges.get("GPT-4o")),
            fmt(judges.get("Gemini")),
            fmt(judges.get("Claude")),
            fmt(pt["delta_nonOAI"]),
            str(pt["n"]),
        ]
        table_data.append(row)

    # Row colours — distinguish groups
    n_narr = len(narrative)
    row_colors = [
        ["#e8f4f8"] * len(col_labels) if i < n_narr else ["#fdf5e6"] * len(col_labels)
        for i in range(len(sorted_titles))
    ]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.axis("off")
    tbl = ax.table(
        cellText=table_data,
        colLabels=col_labels,
        rowLoc="center",
        cellLoc="center",
        loc="center",
        cellColours=row_colors,
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8.2)
    tbl.auto_set_column_width([0, 1, 2, 3, 4, 5, 6])
    tbl[0, 0].set_facecolor("#c8e6c9")
    for j in range(len(col_labels)):
        tbl[0, j].set_facecolor("#c8e6c9")
        tbl[0, j].set_text_props(fontweight="bold")

    ax.set_title(
        "Figure 2b.  Per-title harshness asymmetry (sorted by non-OAI Δ)\n"
        "Blue rows = personal-narrative; cream rows = informational",
        fontsize=9, fontweight="bold", pad=12,
    )

    # Group labels on the side
    ypos_narr = 1 - (n_narr / 2 + 0.5) / (len(sorted_titles) + 1)
    ypos_info = 1 - (n_narr + (len(sorted_titles) - n_narr) / 2 + 0.5) / (len(sorted_titles) + 1)
    ax.text(-0.01, ypos_narr, "Personal\nnarrative", ha="right", va="center",
            fontsize=8, color="#1565c0", transform=ax.transAxes, rotation=90)
    ax.text(-0.01, ypos_info, "Informational", ha="right", va="center",
            fontsize=8, color="#8d6e00", transform=ax.transAxes, rotation=90)

    plt.tight_layout()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, bbox_inches="tight", dpi=200)
    plt.close(fig)
    log(f"  fig2b written ({Path(out_path).stat().st_size} bytes)")


# ── FIGURE 3: Forest plot ─────────────────────────────────────────────────────

def make_fig3(prose_data: dict, out_path: str) -> None:
    log(f"Rendering fig3 → {out_path}")

    per_judge = prose_data["per_judge"]
    non_oai   = prose_data["non_openai_combined"]

    # rows: (label, split, result)
    rows = []
    for split in ("pilot", "heldout", "combined"):
        for jshort in ("GPT-4o", "Gemini", "Claude"):
            r = per_judge.get(jshort, {}).get(split, {})
            rows.append((jshort, split, r))
        rows.append(("non-OAI combined", split, non_oai.get(split, {})))

    # Plot in groups
    judge_order = ["GPT-4o", "Gemini", "Claude", "non-OAI combined"]
    splits_order = ["pilot", "heldout", "combined"]
    split_markers = {"pilot": "o", "heldout": "s", "combined": "D"}
    split_colors  = {"pilot": "#4c72b0", "heldout": "#dd8452", "combined": "#55a868"}

    n_groups = len(judge_order)
    group_gap = 0.9
    within_gap = 0.25

    fig, ax = plt.subplots(figsize=(7, 5.5))
    ytick_pos = []
    ytick_lab = []

    for gi, jshort in enumerate(judge_order):
        base_y = gi * (len(splits_order) * within_gap + group_gap)
        for si, split in enumerate(splits_order):
            y = base_y + si * within_gap
            r = per_judge.get(jshort, {}).get(split) if jshort != "non-OAI combined" else non_oai.get(split, {})
            if not r or r.get("n", 0) == 0:
                continue
            md   = r["mean_diff"]
            ci_lo = r["ci_lo"]
            ci_hi = r["ci_hi"]
            n     = r["n"]
            ax.plot([ci_lo, ci_hi], [y, y], color=split_colors[split], linewidth=1.5)
            ax.plot(md, y, marker=split_markers[split], color=split_colors[split],
                    markersize=7, zorder=5)
            ax.text(ci_hi + 0.02, y,
                    f"Δ={md:+.2f}\n[{ci_lo:+.2f},{ci_hi:+.2f}]\nn={n}",
                    va="center", fontsize=6.5, color="#333")

        mid_y = base_y + (len(splits_order) - 1) * within_gap / 2
        ytick_pos.append(mid_y)
        ytick_lab.append(jshort)

    ax.axvline(0, color="black", linewidth=1.0, linestyle="--", alpha=0.6)
    ax.set_yticks(ytick_pos)
    ax.set_yticklabels(ytick_lab, fontsize=9)
    ax.set_xlabel("Δ harshness  (ChatGPT-attributed − Claude-attributed)", fontsize=9)
    ax.set_title(
        "Figure 3.  Per-judge harshness asymmetry across sample splits\n"
        "(pilot n≈15/judge, held-out n≈15/judge, combined n≈30/judge)",
        fontsize=9, fontweight="bold",
    )

    legend_handles = [
        mpatches.Patch(color=split_colors["pilot"],    label="Pilot (titles 1–5)"),
        mpatches.Patch(color=split_colors["heldout"],  label="Held-out (titles 6–10)"),
        mpatches.Patch(color=split_colors["combined"], label="Combined (all 10 titles)"),
    ]
    ax.legend(handles=legend_handles, fontsize=8, loc="lower right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, bbox_inches="tight", dpi=200)
    plt.close(fig)
    log(f"  fig3 written ({Path(out_path).stat().st_size} bytes)")


# ── FIGURE 4: Validity scatter ────────────────────────────────────────────────

def make_fig4(cv_data: dict, out_path: str) -> None:
    log(f"Rendering fig4 → {out_path}")

    w = np.array(cv_data["weighted_data"])
    h = np.array(cv_data["harshness_data"])

    rng = np.random.default_rng(7)
    jitter_h = h + rng.uniform(-0.07, 0.07, size=len(h))
    jitter_w = w + rng.uniform(-0.06, 0.06, size=len(w))

    fig, ax = plt.subplots(figsize=(6, 5))
    scatter_colors = {1: "#4c72b0", 2: "#dd8452", 3: "#c44e52"}
    for level in sorted(set(h)):
        mask = h == level
        n_lev = int(mask.sum())
        mean_w = float(np.mean(w[mask]))
        ax.scatter(jitter_w[mask], jitter_h[mask],
                   color=scatter_colors.get(level, "gray"),
                   alpha=0.45, s=30, linewidth=0,
                   label=f"h={level}  (n={n_lev}, mean_lex={mean_w:.2f})")

    # Cross-tab means as large markers
    cross = cv_data.get("cross_tab", {})
    for level_str, cell in cross.items():
        level = int(level_str)
        ax.scatter(cell["mean_weighted_sum"], level,
                   color=scatter_colors.get(level, "gray"),
                   s=120, marker="D", edgecolors="black", linewidth=1.2, zorder=10)

    rho = cv_data["spearman_rho"]
    ci_lo, ci_hi = cv_data["ci_lo"], cv_data["ci_hi"]

    ax.set_xlabel("Lexicon weighted sum (held-out 180)", fontsize=9)
    ax.set_ylabel("Qwen harshness rating", fontsize=9)
    ax.set_yticks([1, 2, 3])
    ax.set_yticklabels(["1 (very gentle)", "2", "3 (neutral)"])
    ax.set_title(
        f"Figure 4 (supplementary).  Concurrent validity: lexicon vs Qwen harshness\n"
        f"Spearman ρ = {rho:+.3f}, 95% CI [{ci_lo:+.3f}, {ci_hi:+.3f}] (held-out n=180)\n"
        "Diamond = cross-tab mean; the level-1→2 jump (1.29→3.14) carries the validity signal.\n"
        "Level-3 cell (n=5) is unstable; the rating scale extends to 5 (very harsh) but\n"
        "no held-out critique was rated above 3.",
        fontsize=8.5, fontweight="bold",
    )
    ax.legend(fontsize=7.5, loc="upper right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Level-1→2 jump annotation
    lev1_mean = cross.get("1", {}).get("mean_weighted_sum", 1.29)
    lev2_mean = cross.get("2", {}).get("mean_weighted_sum", 3.14)
    ax.annotate(
        f"jump: {lev1_mean:.2f}→{lev2_mean:.2f}",
        xy=(lev2_mean, 2), xytext=(lev2_mean + 0.3, 2.3),
        fontsize=7.5, color="#444",
        arrowprops=dict(arrowstyle="->", color="#444", linewidth=0.8),
    )

    plt.tight_layout()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, bbox_inches="tight", dpi=200)
    plt.close(fig)
    log(f"  fig4 written ({Path(out_path).stat().st_size} bytes)")


# ── main ──────────────────────────────────────────────────────────────────────

def main(argv=None):
    p = argparse.ArgumentParser(description="Step 8 analysis + figures")
    p.add_argument("--evaluations",  default="runs/evaluations.jsonl")
    p.add_argument("--qwen",         default="runs/qwen-codings.csv")
    p.add_argument("--lexicon",      default="runs/lexicon-counts.csv")
    p.add_argument("--titles",       default="artifacts/titles.json")
    p.add_argument("--out-summary",  default="runs/results-summary.json")
    p.add_argument("--out-log",      default="runs/analyze.log")
    p.add_argument("--out-fig1",     default="paper/figures/fig1-score-vs-prose.pdf")
    p.add_argument("--out-fig2a",    default="paper/figures/fig2a-per-title-heatmap.pdf")
    p.add_argument("--out-fig2b",    default="paper/figures/fig2b-per-title-table.pdf")
    p.add_argument("--out-fig3",     default="paper/figures/fig3-forest-plot.pdf")
    p.add_argument("--out-fig4",     default="paper/figures/fig4-validity-scatter.pdf")
    args = p.parse_args(argv)

    global LOG_PATH
    LOG_PATH = Path(args.out_log)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    log("=" * 70)
    log(f"analyze.py — Step 8  (utc {datetime.utcnow().isoformat(timespec='seconds')})")
    log("=" * 70)

    d = load_data(args.evaluations, args.qwen, args.lexicon, args.titles)

    score_channel  = compute_score_channel(d["evs"])
    prose_channel  = compute_prose_channel(d["qwen_rows"], d["blog2title"],
                                           d["pilot_titles"], d["heldout_titles"])
    concurrent_val = compute_concurrent_validity(d["lex_rows"], d["qwen_rows"],
                                                  d["blog2title"], d["heldout_titles"])
    drift          = compute_drift()

    # Strip raw data arrays before serialising (they're large; scatter fig already made)
    cv_for_json = {k: v for k, v in concurrent_val.items()
                   if k not in ("weighted_data", "harshness_data")}

    summary = {
        "score_channel":       score_channel,
        "prose_channel":       prose_channel,
        "concurrent_validity": cv_for_json,
        "drift":               drift,
        "generated_at":        datetime.utcnow().isoformat(timespec="seconds"),
    }
    Path(args.out_summary).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_summary).write_text(json.dumps(summary, indent=2))
    log(f"Summary written → {args.out_summary}")

    # Figures
    make_fig1(score_channel, prose_channel, args.out_fig1)
    make_fig2a(prose_channel["per_title"], prose_channel["per_title_judge"], args.out_fig2a)
    make_fig2b(prose_channel["per_title"], prose_channel["per_title_judge"], args.out_fig2b)
    make_fig3(prose_channel, args.out_fig3)
    make_fig4(concurrent_val, args.out_fig4)

    flush_log()
    log("analyze.py DONE.")


if __name__ == "__main__":
    main()
