#!/usr/bin/env python3
"""
preflight-judge.py — Step 3 pre-flight validator.

Hits OpenRouter 9 times (3 sample posts × 3 judges) using the EXACT prompt
from artifacts/judge-prompt.template.md (also embedded in code/evaluate.py),
parses each response, and validates against the schema.

Stdlib-only on purpose — avoid forcing a venv install just for a 9-call
diagnostic. The full pipeline (code/evaluate.py) uses httpx + pyyaml.

Output is printed to stdout. Nothing is written under runs/.

Usage:
    OPENROUTER_API_KEY=... python3 scripts/preflight-judge.py

Exit codes:
    0  all 9 passed
    1  at least one parse / schema / word-count failure
    2  OPENROUTER_API_KEY not set
"""
from __future__ import annotations
import json, os, re, sys, time, urllib.request, urllib.error
from textwrap import shorten

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# ---- Identical to code/evaluate.py:JUDGE_SYSTEM_PROMPT ---------------------
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

# Three hand-picked sample posts of varying quality — kept short to control
# token cost. Same trio sent to every judge; label is "unattributed" so we
# isolate prompt-format compliance from label-induced effects.
SAMPLES = [
    {
        "id": "A_strong",
        "title": "Why Type Hints Make Python Code Easier to Refactor",
        "body": (
            "Type hints in Python are not enforced at runtime, but they are not "
            "decorative either. A well-typed function signature gives a refactoring "
            "tool — or a careful human reader — enough information to trace data flow "
            "across modules without running the program. The payoff compounds in "
            "larger codebases. When you rename a field, mypy will surface every "
            "downstream caller that relied on its old shape; without hints, you are "
            "left grepping for variable names and hoping the tests are thorough. "
            "The cost is low: most editors infer hints automatically, and gradual "
            "typing means you can adopt them one module at a time. The real friction "
            "is cultural — convincing a team that the small upfront cost trades for "
            "fewer 3am production incidents and faster onboarding for new engineers."
        ),
    },
    {
        "id": "B_mediocre",
        "title": "Five Habits of Highly Productive People",
        "body": (
            "Productive people share certain habits. They wake up early, they exercise, "
            "and they prioritise their most important tasks first. Many of them keep a "
            "journal, and almost all of them say they limit social media. If you want to "
            "be more productive, you should try to adopt these habits one at a time. "
            "Don't try to change everything at once — that rarely works. Start small, "
            "build momentum, and remember that consistency matters more than intensity. "
            "Productivity is a journey, not a destination. Everyone has different "
            "rhythms, so what works for one person may not work for another, but the "
            "broad principles tend to hold. The most important thing is to start today, "
            "even imperfectly, because tomorrow always feels like a better starting point."
        ),
    },
    {
        "id": "C_weak",
        "title": "AI and the Future",
        "body": (
            "AI is changing the future. AI is everywhere now. Many companies are using "
            "AI for many things. AI can write, AI can draw, AI can talk. The future of "
            "AI is bright. AI will keep getting better. AI will help people in many ways. "
            "But AI also has problems. Some people are worried about AI. AI can make "
            "mistakes. AI can be biased. We need to be careful with AI. AI is a tool, "
            "and like any tool, it depends on how we use it. The future of AI depends on "
            "us. We must use AI wisely. AI will continue to grow and change. The future "
            "is AI, and AI is the future. Everyone should learn about AI."
        ),
    },
]

JUDGES = [
    "openai/gpt-4o",
    "google/gemini-2.5-flash",
    "anthropic/claude-sonnet-4",
]


def post_openrouter(model: str, system: str, user: str, *, api_key: str
                    ) -> tuple[int, str]:
    body = json.dumps({"model": model, "messages": [
        {"role": "system", "content": system},
        {"role": "user",   "content": user},
    ]}).encode("utf-8")
    req = urllib.request.Request(
        OPENROUTER_URL, data=body,
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"})
    delay = 2
    for _ in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                resp_json = json.loads(r.read().decode("utf-8"))
                return 200, resp_json["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(delay); delay *= 2; continue
            return e.code, e.read().decode("utf-8", errors="replace")[:500]
        except urllib.error.URLError as e:
            return -1, f"URLError: {e.reason}"
    return -1, "max retries exceeded"


def parse_judge_json(raw: str) -> dict:
    raw = raw.strip()
    fenced = raw.startswith("```")
    if fenced:
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
    m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not m:
        raise ValueError(f"No JSON object found in: {raw[:200]}")
    parsed = json.loads(m.group(0))
    parsed["__fenced__"] = fenced
    parsed["__preamble__"] = bool(re.match(r"\S", raw[: m.start()]))
    return parsed


def validate(parsed: dict) -> list[str]:
    """Return list of failure messages (empty = pass)."""
    fails = []
    if "scores" not in parsed or not isinstance(parsed["scores"], dict):
        fails.append("missing or non-object 'scores' key")
    else:
        for k in ("coherence", "informativeness", "conciseness"):
            v = parsed["scores"].get(k)
            if not isinstance(v, int) or not (0 <= v <= 10):
                fails.append(f"scores.{k} not int-in-[0,10]: {v!r}")
    just = parsed.get("justification")
    if not isinstance(just, str):
        fails.append("missing or non-string 'justification' key")
    else:
        wc = len(just.split())
        if wc < 60 or wc > 250:
            fails.append(f"justification word count {wc} not in [60,250]")
    if parsed.get("__fenced__"):
        fails.append("output wrapped in ``` code fences (parser strips, flag for prompt fix)")
    if parsed.get("__preamble__"):
        fails.append("output has prose preamble before JSON (parser regex-extracts, flag)")
    return fails


def main() -> int:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not set", file=sys.stderr)
        return 2

    print(f"Pre-flight: {len(SAMPLES)} posts × {len(JUDGES)} judges = "
          f"{len(SAMPLES)*len(JUDGES)} calls")
    print("=" * 78)

    rows = []
    for sample in SAMPLES:
        user_msg = JUDGE_USER_TEMPLATE.format(
            label="unattributed", title=sample["title"], body=sample["body"])
        for judge in JUDGES:
            t0 = time.time()
            status, content = post_openrouter(
                judge, JUDGE_SYSTEM_PROMPT, user_msg, api_key=api_key)
            elapsed = time.time() - t0
            verdict, fails, parsed = "FAIL", [], {}
            if status != 200:
                fails = [f"http {status}: {shorten(content, 200)}"]
            else:
                try:
                    parsed = parse_judge_json(content)
                    fails = validate(parsed)
                    verdict = "PASS" if not fails else "FAIL"
                except Exception as e:
                    fails = [f"parse error: {e}"]
            rows.append({
                "judge": judge, "sample": sample["id"], "verdict": verdict,
                "elapsed_s": round(elapsed, 1), "fails": fails,
                "scores": parsed.get("scores") if verdict == "PASS" else None,
                "raw_excerpt": shorten(content, 220, placeholder="…"),
            })
            mark = "OK " if verdict == "PASS" else "FX "
            print(f"  {mark} {sample['id']:<11}  {judge:<32}  "
                  f"{elapsed:5.1f}s  {verdict}")
            for f in fails:
                print(f"      - {f}")

    print("=" * 78)
    n_pass = sum(1 for r in rows if r["verdict"] == "PASS")
    n_fail = len(rows) - n_pass
    print(f"SUMMARY: {n_pass}/{len(rows)} passed, {n_fail} failed")

    if n_fail:
        print("\nFailure breakdown by judge:")
        for judge in JUDGES:
            judge_fails = [r for r in rows if r["judge"] == judge
                           and r["verdict"] != "PASS"]
            if judge_fails:
                print(f"  {judge}: {len(judge_fails)} fail(s)")
                for r in judge_fails:
                    print(f"    [{r['sample']}] {' | '.join(r['fails'])}")
                    print(f"      raw: {r['raw_excerpt']}")
        print("\nSuggested prompt fixes (apply only those matching the pattern):")
        print("  - 'fenced' / 'preamble' on one judge:")
        print("      append 'Output ONLY the JSON, no preamble, no code fences.'")
        print("      to the system prompt; or add a one-shot example output.")
        print("  - Gemini ignores system prompt:")
        print("      prepend the schema to the user message instead of system.")
        print("  - word-count failures are systematic:")
        print("      tighten range in the prompt: '90-130 word paragraph (strict)'.")

    print("\nFull dump (json):")
    print(json.dumps(rows, indent=2, default=str))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
