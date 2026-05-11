"""
check_model_drift.py — compare OpenRouter model-version metadata between
pilot and held-out snapshots, per judge.

Pilot ran on 2026-05-09; held-out on 2026-05-10. OpenRouter routes to
underlying provider snapshots that can change without notice. We need
to know whether the same `model` string returned the same underlying
version across the two days.

Reads `runs/responses/index.csv` to find evaluation snapshots, partitions
them by (judge × pilot/held-out) using evaluations.jsonl + titles.json,
samples one snapshot per cell, and reports `model`, `provider`, and
`system_fingerprint` from each.

Outputs:
  - prints a comparison table to stdout
  - writes `artifacts/model-drift-report.md` with structured findings
  - exit code:
      0 if no drift detected (all judges match across days)
      1 if drift detected (will need a threats-to-validity note)

Usage:
    python -m code.check_model_drift \
        --evaluations runs/evaluations.jsonl \
        --titles artifacts/titles.json \
        --output artifacts/model-drift-report.md
"""
from __future__ import annotations
import argparse, hashlib, json, sys
from collections import defaultdict
from pathlib import Path


def load_blog_to_title(gens_path: Path) -> dict[str, str]:
    out = {}
    for line in gens_path.read_text().splitlines():
        g = json.loads(line)
        bid = hashlib.sha1(f"{g['model']}|{g['title']}".encode()).hexdigest()[:12]
        out[bid] = g["title"]
    return out


def fields_from_snapshot(path: Path) -> dict:
    snap = json.loads(path.read_text())
    body = (snap.get("response") or {}).get("body") or {}
    return {
        "model": body.get("model"),
        "provider": body.get("provider"),
        "system_fingerprint": body.get("system_fingerprint"),
        "id": body.get("id"),
        "created": body.get("created"),
    }


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--evaluations", required=True)
    p.add_argument("--titles", required=True)
    p.add_argument("--pilot-size", type=int, default=5)
    p.add_argument("--snapshot-dir", default="runs/responses/evaluations")
    p.add_argument("--output", required=True)
    p.add_argument("--samples-per-cell", type=int, default=3,
                   help="number of snapshots to fingerprint per (judge × split)")
    args = p.parse_args(argv)

    titles = json.loads(Path(args.titles).read_text())
    pilot_titles = set(titles[: args.pilot_size])
    heldout_titles = set(titles[args.pilot_size:])

    gens_path = Path(args.evaluations).parent / "generations.jsonl"
    blog2title = load_blog_to_title(gens_path)
    snap_dir = Path(args.snapshot_dir)

    # Bucket: judge → split → list of snapshot paths
    buckets: dict[str, dict[str, list[Path]]] = defaultdict(lambda: defaultdict(list))
    for line in Path(args.evaluations).read_text().splitlines():
        r = json.loads(line)
        title = blog2title.get(r["blog_id"])
        if title in pilot_titles:
            split = "pilot"
        elif title in heldout_titles:
            split = "heldout"
        else:
            continue
        rid = r.get("response_id")
        if not rid:
            continue
        path = snap_dir / f"{rid}.json"
        if path.exists():
            buckets[r["judge"]][split].append(path)

    # Sample N snapshots per cell and fingerprint each
    cells: dict[tuple[str, str], list[dict]] = {}
    for judge, splits in buckets.items():
        for split, paths in splits.items():
            sample = paths[: args.samples_per_cell]
            cells[(judge, split)] = [fields_from_snapshot(p) for p in sample]

    # Compare fields per judge across pilot vs held-out
    judges = sorted({j for j, _ in cells.keys()})
    drift_lines: list[str] = []
    table_lines: list[str] = []
    table_lines.append(f"| {'judge':<28} | {'split':<8} | {'model':<32} | "
                       f"{'provider':<12} | {'system_fingerprint':<22} |")
    table_lines.append("|" + "-" * 30 + "|" + "-" * 10 + "|"
                       + "-" * 34 + "|" + "-" * 14 + "|" + "-" * 24 + "|")

    drift_detected = False
    for judge in judges:
        per_split = {sp: cells.get((judge, sp), []) for sp in ("pilot", "heldout")}
        # Take the first sample per split as the canonical fingerprint
        # (intra-split variation is reported separately if present).
        canon = {sp: (per_split[sp][0] if per_split[sp] else None) for sp in ("pilot", "heldout")}
        for sp, vals in per_split.items():
            for v in vals:
                table_lines.append(
                    f"| {judge:<28} | {sp:<8} | {(v['model'] or '-'):<32} | "
                    f"{(v['provider'] or '-'):<12} | {(v['system_fingerprint'] or '-'):<22} |"
                )
        # Drift checks: model and system_fingerprint
        p_canon, h_canon = canon["pilot"], canon["heldout"]
        if not p_canon or not h_canon:
            drift_lines.append(f"- **{judge}** — INCOMPLETE: pilot={bool(p_canon)} heldout={bool(h_canon)}")
            continue
        diffs = []
        for k in ("model", "provider", "system_fingerprint"):
            if p_canon.get(k) != h_canon.get(k):
                diffs.append(f"{k}: pilot={p_canon.get(k)!r} → heldout={h_canon.get(k)!r}")
        if diffs:
            drift_detected = True
            drift_lines.append(f"- **{judge}** — DRIFT:\n  - " + "\n  - ".join(diffs))
        else:
            drift_lines.append(f"- **{judge}** — match (model={p_canon.get('model')}, "
                               f"system_fingerprint={p_canon.get('system_fingerprint')})")

    print("\n".join(table_lines))
    print()
    print("\n".join(drift_lines))

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "# Model-drift report — pilot vs held-out\n\n"
        f"**Pilot run date:** 2026-05-09 (titles 1–{args.pilot_size})\n"
        f"**Held-out run date:** 2026-05-10 (titles {args.pilot_size + 1}–{len(titles)})\n\n"
        f"**Drift detected:** {'YES — see below' if drift_detected else 'no'}\n\n"
        "## Snapshot fingerprints\n\n"
        + "\n".join(table_lines)
        + "\n\n## Per-judge verdict\n\n"
        + "\n".join(drift_lines)
        + "\n"
    )
    print(f"\nWrote {out}")
    return 1 if drift_detected else 0


if __name__ == "__main__":
    sys.exit(main())
