"""
build_corpus_lexicon.py — held-out-split lexicon construction.

STAGE 1 of the new lexicon pipeline (post-pilot, pre-/analyze):
  Send ALL pilot justifications to Qwen 2.5 72B in a single request and
  ask it to return harsh-marker words/phrases categorised into 2-3
  severity levels, as JSON.

The pilot 180 is the *construction set*; the full-run 180 is the held-out
*test set*. The lexicon produced here is later applied mechanically to
the held-out set by `apply_corpus_lexicon.py` and validated against the
Qwen harshness coding via Spearman ρ.

Usage:
    OPENROUTER_API_KEY=... python -m code.build_corpus_lexicon \
        --evaluations runs/evaluations.jsonl \
        --titles artifacts/titles.json \
        --output artifacts/lexicon-v2-raw.json

Output: a JSON file Hashem manually curates (~15 min) before applying.
"""
from __future__ import annotations
import argparse, json, os, re, sys, time, hashlib
from pathlib import Path

import httpx

from . import _snapshot

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
CODER_MODEL = "qwen/qwen-2.5-72b-instruct"

SYSTEM = """\
You are a corpus linguist. You will be shown a set of paragraphs
("justifications") in which one LLM judge evaluated a blog post written
by another LLM. Your task is to extract a HARSHNESS LEXICON from this
corpus: words and phrases whose presence indicates that the judge is
being harsh, dismissive, or critical in tone (independent of the
numerical scores given).

Rules:
1. Build a lexicon of CONCRETE surface markers (words or short n-grams).
   Avoid abstract concepts; the lexicon will be applied mechanically.
2. Categorise each marker by severity:
   - level 2 (mild): hedged criticism, polite but pointed
     (e.g. "could be improved", "lacks depth", "somewhat verbose")
   - level 3 (moderate): direct, unhedged criticism
     (e.g. "fails to", "weak", "inadequate")
   - level 5 (severe): dismissive, absolutist, or contempt-laden
     (e.g. "completely lacking", "fundamentally flawed", "worthless")
3. Avoid markers that change meaning based on context, sarcasm, or
   negation. Prefer surface forms a regex would match unambiguously.
4. Avoid generic positive/negative words ("good", "bad") — these carry
   too little signal alone.
5. Each marker must appear at least once in the corpus you are shown.
6. Cap the total at ~80 markers across all levels.

Output ONLY a JSON object matching this schema, with no surrounding text
and no markdown fences:

{
  "level_2_mild": ["marker", "marker", ...],
  "level_3_moderate": ["marker", "marker", ...],
  "level_5_severe": ["marker", "marker", ...],
  "notes": "<1-3 sentences on cross-judge regularities you noticed; do not name specific judge models>"
}
"""

USER_TEMPLATE = """\
Below are {n} justifications from the construction corpus, separated by
`---`. Build the harshness lexicon as instructed.

{corpus}
"""


def call_qwen(system: str, user: str, *, api_key: str,
              max_retries: int = 5) -> tuple[str, dict, int]:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": CODER_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        # Headroom for ~80 markers and notes.
        "max_tokens": 4000,
    }
    delay = 2
    for _ in range(max_retries):
        r = httpx.post(OPENROUTER_URL, headers=headers, json=payload, timeout=180)
        if r.status_code == 200:
            body = r.json()
            return body["choices"][0]["message"]["content"], body, r.status_code
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(delay); delay *= 2; continue
        r.raise_for_status()
    raise RuntimeError("lexicon construction call failed after retries")


def parse_json_lenient(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
    start = raw.find("{")
    if start == -1:
        raise ValueError(f"No JSON in response: {raw[:200]}")
    candidate = raw[start:]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        opens, closes = candidate.count("{"), candidate.count("}")
        if opens > closes:
            return json.loads(candidate.rstrip().rstrip(",") + "}" * (opens - closes))
        last = candidate.rfind("}")
        if last != -1:
            return json.loads(candidate[: last + 1])
        raise


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--evaluations", required=True)
    p.add_argument("--titles", required=True,
                   help="artifacts/titles.json (canonical title order)")
    p.add_argument("--pilot-size", type=int, default=5,
                   help="number of titles in the pilot/construction split")
    p.add_argument("--output", required=True)
    p.add_argument("--per-stratum", type=int, default=0,
                   help="if >0, stratified sample N per (judge × condition) cell. "
                        "Default 0 = use all pilot critiques.")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args(argv)

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: set OPENROUTER_API_KEY", file=sys.stderr); return 2

    # Identify pilot blog_ids by title membership in titles.json[:pilot-size].
    titles = json.loads(Path(args.titles).read_text())
    pilot_titles = set(titles[: args.pilot_size])

    # Re-derive blog_id from the same hash function evaluate.py uses.
    # We don't read generations.jsonl here; instead, we filter justifications
    # whose blog_id matches the pilot title set by reading the rows that
    # carry the title... but evaluations.jsonl doesn't carry the title.
    # So we read generations.jsonl to build the blog_id → title map.
    gens_path = Path(args.evaluations).parent / "generations.jsonl"
    if not gens_path.exists():
        print(f"ERROR: needs {gens_path} alongside evaluations", file=sys.stderr); return 2
    blog2title = {}
    for line in gens_path.read_text().splitlines():
        g = json.loads(line)
        bid = hashlib.sha1(f"{g['model']}|{g['title']}".encode()).hexdigest()[:12]
        blog2title[bid] = g["title"]

    # Group pilot critiques by (judge × condition) for optional stratified sampling.
    import random
    by_cell = {}
    for line in Path(args.evaluations).read_text().splitlines():
        r = json.loads(line)
        title = blog2title.get(r["blog_id"])
        if title in pilot_titles and r.get("justification"):
            cell = (r["judge"], r["condition"])
            by_cell.setdefault(cell, []).append(r["justification"])

    if args.per_stratum > 0:
        rng = random.Random(args.seed)
        just = []
        sample_meta = {}
        for cell, items in sorted(by_cell.items()):
            picked = rng.sample(items, min(args.per_stratum, len(items)))
            just.extend(picked)
            sample_meta[f"{cell[0]}|{cell[1]}"] = len(picked)
        print(f"Construction corpus: {len(just)} stratified-sampled (per_stratum={args.per_stratum})")
        for k, v in sample_meta.items():
            print(f"  {k:<46} {v} sampled")
    else:
        just = []
        for items in by_cell.values():
            just.extend(items)
        print(f"Construction corpus: {len(just)} pilot justifications")

    if not just:
        print("ERROR: no justifications matched pilot titles", file=sys.stderr); return 2

    corpus = "\n---\n".join(just)
    user = USER_TEMPLATE.format(n=len(just), corpus=corpus)

    raw, body, status = call_qwen(SYSTEM, user, api_key=api_key)
    parsed = parse_json_lenient(raw)

    # Snapshot the API call.
    rid = _snapshot.save(
        category="lexicon-construction",
        run_dir=Path("runs"),
        request={
            "model": CODER_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content_chars": len(user),
                 "n_justifications": len(just)},
            ],
        },
        response={"status_code": status, "body": body},
        parsed=parsed,
        key_inputs=("pilot-construction", len(just), args.per_stratum, args.seed),
    )

    # Save the parsed lexicon next to the snapshot id.
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "_response_id": rid,
        "_constructed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "_corpus_size": len(just),
        "_per_stratum": args.per_stratum,
        "_seed": args.seed,
        "_pilot_titles": sorted(pilot_titles),
        **parsed,
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")

    levels = [k for k in parsed if k.startswith("level_")]
    counts = {k: len(parsed[k]) for k in levels}
    print(f"Wrote {out}  ({sum(counts.values())} markers across {len(levels)} levels: {counts})")
    print(f"Snapshot: {rid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
