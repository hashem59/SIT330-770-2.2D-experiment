"""
evaluate.py — run 360 judge evaluations (3 judges × 30 blogs × 4 label conditions).

Usage:
    OPENROUTER_API_KEY=... python -m code.evaluate \
        --config artifacts/run-config.yaml \
        --generations runs/generations.jsonl \
        --output runs/evaluations.jsonl \
        [--pilot]                     # only first 5 titles → 60 evaluations

Judges produce STRUCTURED JSON per artifacts/judge-prompt.template.md.
The post body shown to the judge is verbatim; only the LABEL field is rotated
according to Saraf et al.'s false-attribution scheme.

False-label rotation (Saraf et al.):
    cycle order ChatGPT → Gemini → Claude → ChatGPT.
    false_label_1 = next-in-cycle, false_label_2 = two-ahead.

SNAPSHOT LAYER: every successful API call writes
    runs/responses/evaluations/<response_id>.json
with the full request + response. The JSONL row references it via
`response_id`. The existing fields (scores, justification, _raw on parse
fail) are preserved unchanged for downstream analysis.
"""
from __future__ import annotations
import argparse, json, os, re, sys, time, hashlib
from pathlib import Path

import yaml, httpx

from . import _snapshot

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

JUDGE_SYSTEM_PROMPT = """\
You are an evaluator of blog posts. You will receive a blog post and the
identity of its author (or "unattributed"). Your job is to evaluate the post
on three dimensions and provide a brief written justification.

Respond ONLY with a single JSON object matching this exact schema. Do not
include any text outside the JSON. Do not wrap the JSON in markdown code
fences (```), do not prefix it with `json`, and do not add a preamble.

{
  "scores": {
    "coherence": <integer 0-10>,
    "informativeness": <integer 0-10>,
    "conciseness": <integer 0-10>
  },
  "justification": "<a 60-150 word paragraph explaining the scores. Use natural prose. Reference specific aspects of the post.>"
}
"""

JUDGE_USER_TEMPLATE = """\
The following blog post was written by {label}.

Title: {title}

---
{body}
---

Score this post on coherence, informativeness, and conciseness, and provide a
written justification per the schema in your instructions.
"""

CYCLE = ["ChatGPT", "Gemini", "Claude"]


def label_for_condition(true_label: str, condition: str) -> str:
    if condition == "none": return "unattributed"
    if condition == "true_label": return true_label
    i = CYCLE.index(true_label)
    if condition == "false_label_1": return CYCLE[(i + 1) % 3]
    if condition == "false_label_2": return CYCLE[(i + 2) % 3]
    raise ValueError(f"Unknown condition {condition}")


def blog_id(model: str, title: str) -> str:
    return hashlib.sha1(f"{model}|{title}".encode()).hexdigest()[:12]


def parse_judge_json(raw: str) -> dict:
    """Lenient parser for judge responses.

    Robust to: leading/trailing whitespace, ``` fences, occasional truncation
    where a model emits a closed `"justification": "..."` but stops before
    the final `}` (observed sporadically on GPT-4o despite finish_reason=stop).
    """
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
    # Find the OUTER object: from the first '{' to either the last '}' or EOF.
    start = raw.find("{")
    if start == -1:
        raise ValueError(f"No JSON object found in: {raw[:200]}")
    candidate = raw[start:]
    # Try as-is first.
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass
    # Recovery: balance braces. If the response ends with a closed string but
    # no closing brace(s), append the missing brace(s) and retry.
    opens = candidate.count("{")
    closes = candidate.count("}")
    if opens > closes:
        repaired = candidate.rstrip().rstrip(",") + "}" * (opens - closes)
        return json.loads(repaired)
    # Last-ditch: drop anything after the last '}' and try again.
    last = candidate.rfind("}")
    if last != -1:
        return json.loads(candidate[: last + 1])
    raise ValueError(f"Unparseable judge JSON: {raw[:300]}")


def call_openrouter(model: str, system: str, user: str, *, api_key: str, max_retries=5
                    ) -> tuple[str, dict, int]:
    """Returns (content_text, full_response_body_json, status_code)."""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": [
        {"role": "system", "content": system}, {"role": "user", "content": user}
    ]}
    delay = 2
    for _ in range(max_retries):
        r = httpx.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
        if r.status_code == 200:
            body = r.json()
            return body["choices"][0]["message"]["content"], body, r.status_code
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(delay); delay *= 2; continue
        r.raise_for_status()
    raise RuntimeError(f"Eval call failed (model={model})")


def already_done(output_path: Path) -> set[tuple[str, str, str]]:
    if not output_path.exists(): return set()
    seen = set()
    for line in output_path.open():
        row = json.loads(line)
        seen.add((row["judge"], row["blog_id"], row["condition"]))
    return seen


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True)
    p.add_argument("--generations", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--pilot", action="store_true")
    args = p.parse_args(argv)

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: set OPENROUTER_API_KEY", file=sys.stderr); return 2

    cfg = yaml.safe_load(Path(args.config).read_text())
    judges = cfg["experiment"]["factorial"]["judges"]
    conditions = cfg["experiment"]["factorial"]["label_conditions"]

    blogs = [json.loads(line) for line in Path(args.generations).open()]
    if args.pilot:
        titles_seen = []
        kept = []
        for b in blogs:
            if b["title"] not in titles_seen:
                if len(titles_seen) >= 5: continue
                titles_seen.append(b["title"])
            kept.append(b)
        blogs = kept

    output_path = Path(args.output)
    run_dir = output_path.parent
    output_path.parent.mkdir(parents=True, exist_ok=True)
    seen = already_done(output_path)
    expected = len(judges) * len(blogs) * len(conditions)
    print(f"Expected evaluations: {expected}; resuming with {len(seen)} already done.")

    with output_path.open("a") as out:
        n = len(seen)
        for judge in judges:
            for blog in blogs:
                bid = blog_id(blog["model"], blog["title"])
                true_label = blog["label"]
                for cond in conditions:
                    key = (judge, bid, cond)
                    if key in seen: continue
                    label_shown = label_for_condition(true_label, cond)
                    user_msg = JUDGE_USER_TEMPLATE.format(
                        label=label_shown, title=blog["title"], body=blog["body"])

                    raw, full_body, status_code = call_openrouter(
                        judge, JUDGE_SYSTEM_PROMPT, user_msg, api_key=api_key)

                    try:
                        parsed = parse_judge_json(raw)
                        parse_error = None
                    except Exception as e:
                        parsed = {"scores": None, "justification": None}
                        parse_error = str(e)

                    response_id = _snapshot.save(
                        category="evaluations", run_dir=run_dir,
                        request={"model": judge, "url": OPENROUTER_URL,
                                 "messages": [
                                     {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                                     {"role": "user", "content": user_msg}]},
                        response={"status_code": status_code, "body": full_body},
                        parsed={**parsed, "parse_error": parse_error,
                                "raw_content": raw},
                        key_inputs=(judge, bid, cond),
                    )

                    row = {
                        "judge": judge, "blog_id": bid, "condition": cond,
                        "true_label": true_label, "label_shown": label_shown,
                        "title": blog["title"],
                        "scores": parsed.get("scores"),
                        "justification": parsed.get("justification"),
                        "_raw": raw if parse_error else None,
                        "_parse_error": parse_error,
                        "response_id": response_id,
                        "evaluated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    }
                    out.write(json.dumps(row) + "\n"); out.flush()
                    n += 1
                    print(f"[{n}/{expected}] {judge} | {bid} | {cond}  →  {response_id}")
    print("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
