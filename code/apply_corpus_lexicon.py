"""
apply_corpus_lexicon.py — STAGE 2 of the held-out-split lexicon pipeline.

Apply a curated corpus-driven harshness lexicon to the held-out 180
justifications (titles 6-10). Counts per critique are written to
runs/lexicon-counts.csv. The validity check (Spearman ρ between counts
and Qwen-coded harshness) is run by the analysis stage.

Usage:
    python -m code.apply_corpus_lexicon \
        --evaluations runs/evaluations.jsonl \
        --titles artifacts/titles.json \
        --lexicon artifacts/lexicon-v2-curated.json \
        --output runs/lexicon-counts.csv
"""
from __future__ import annotations
import argparse, csv, hashlib, json, re, sys
from pathlib import Path


def compile_patterns(lexicon: dict) -> dict[str, list[tuple[int, re.Pattern]]]:
    """Return {marker: [(level, pattern), ...]} keyed by surface form.
    A marker that appears in multiple levels gets multiple entries; the
    severity is summed at apply time.
    """
    out: list[tuple[str, int, re.Pattern]] = []
    for key, level in (("level_2_mild", 2),
                        ("level_3_moderate", 3),
                        ("level_5_severe", 5)):
        for marker in lexicon.get(key, []):
            esc = re.escape(marker.lower().strip())
            # Word boundary on each side; permit internal whitespace flexibility.
            pat = re.compile(r"\b" + esc.replace(r"\ ", r"\s+") + r"\b")
            out.append((marker, level, pat))
    return out


def count_markers(text: str, patterns) -> tuple[int, int, int, int]:
    """Returns (count_level_2, count_level_3, count_level_5, weighted_sum)."""
    t = text.lower()
    c2 = c3 = c5 = w = 0
    for marker, level, pat in patterns:
        n = len(pat.findall(t))
        if not n:
            continue
        if level == 2:
            c2 += n; w += 2 * n
        elif level == 3:
            c3 += n; w += 3 * n
        elif level == 5:
            c5 += n; w += 5 * n
    return c2, c3, c5, w


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--evaluations", required=True)
    p.add_argument("--titles", required=True)
    p.add_argument("--lexicon", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--pilot-size", type=int, default=5)
    p.add_argument("--scope", choices=["heldout", "all"], default="heldout",
                   help="heldout = titles 6..N; all = every row in evaluations")
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

    lexicon = json.loads(Path(args.lexicon).read_text())
    patterns = compile_patterns(lexicon)
    print(f"Compiled {len(patterns)} marker patterns")

    rows = []
    skipped = 0
    for line in Path(args.evaluations).read_text().splitlines():
        r = json.loads(line)
        title = blog2title.get(r["blog_id"])
        if args.scope == "heldout" and title not in heldout_titles:
            skipped += 1; continue
        just = r.get("justification") or ""
        c2, c3, c5, w = count_markers(just, patterns)
        rows.append({
            "judge": r["judge"],
            "blog_id": r["blog_id"],
            "condition": r["condition"],
            "true_label": r["true_label"],
            "label_shown": r["label_shown"],
            "lex_count_mild": c2,
            "lex_count_moderate": c3,
            "lex_count_severe": c5,
            "lex_weighted_sum": w,
            "lex_total_count": c2 + c3 + c5,
            "response_id": r.get("response_id", ""),
        })

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as f:
        if not rows:
            f.write("")
        else:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            for r in rows:
                w.writerow(r)
    print(f"Wrote {out}  ({len(rows)} rows; skipped {skipped} non-{args.scope} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
