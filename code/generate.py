"""
generate.py — generate 30 blog posts (3 generators × 10 titles) via OpenRouter.

Usage:
    OPENROUTER_API_KEY=... python -m code.generate \
        --config artifacts/run-config.yaml \
        --titles artifacts/titles.json \
        --output runs/generations.jsonl

Idempotent: skips existing (model, title) pairs already in output JSONL.
Retry-safe: per-call exponential backoff on 5xx/timeout, capped at 5 retries.

SNAPSHOT LAYER: every successful API call also writes
    runs/responses/generations/<response_id>.json
containing the full request and response (model version, token usage,
finish reason, request id, etc.). The JSONL row gains a `response_id`
field linking back. See code/_snapshot.py for details.
"""
from __future__ import annotations
import argparse, json, os, sys, time
from pathlib import Path

import yaml
import httpx

from . import _snapshot

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

GENERATION_PROMPT_TEMPLATE = """\
Write a blog post on the topic below. Length: 400-600 words. Include an
introduction, 2-3 substantive paragraphs, and a brief conclusion. Write in
your own natural style; do not include any meta-commentary about the topic
or about being an AI.

Topic: {title}
"""


def call_openrouter(model: str, prompt: str, *, api_key: str, max_retries: int = 5
                    ) -> tuple[str, dict, int]:
    """Single OpenRouter chat completion.

    Returns (content_text, full_response_body_json, status_code).
    """
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    delay = 2
    for _ in range(max_retries):
        try:
            r = httpx.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
            if r.status_code == 200:
                body = r.json()
                content = body["choices"][0]["message"]["content"]
                return content, body, r.status_code
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(delay); delay *= 2; continue
            r.raise_for_status()
        except (httpx.TimeoutException, httpx.RemoteProtocolError):
            time.sleep(delay); delay *= 2
    raise RuntimeError(f"OpenRouter call failed after {max_retries} retries (model={model})")


def already_done(output_path: Path) -> set[tuple[str, str]]:
    if not output_path.exists(): return set()
    seen = set()
    with output_path.open() as f:
        for line in f:
            row = json.loads(line)
            seen.add((row["model"], row["title"]))
    return seen


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True)
    p.add_argument("--titles", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args(argv)

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: set OPENROUTER_API_KEY", file=sys.stderr); return 2

    cfg = yaml.safe_load(Path(args.config).read_text())
    titles = json.loads(Path(args.titles).read_text())

    output_path = Path(args.output)
    run_dir = output_path.parent
    output_path.parent.mkdir(parents=True, exist_ok=True)
    seen = already_done(output_path)

    generators = cfg["experiment"]["factorial"]["generators"]
    total = len(generators) * len(titles)
    done = len(seen)
    print(f"Resuming: {done}/{total} already generated")

    with output_path.open("a") as out:
        for gen in generators:
            model = gen["model"]; label = gen["label"]
            for title in titles:
                if (model, title) in seen:
                    continue
                prompt = GENERATION_PROMPT_TEMPLATE.format(title=title)
                content, full_body, status_code = call_openrouter(model, prompt, api_key=api_key)

                response_id = _snapshot.save(
                    category="generations", run_dir=run_dir,
                    request={"model": model, "url": OPENROUTER_URL,
                             "messages": [{"role": "user", "content": prompt}]},
                    response={"status_code": status_code, "body": full_body},
                    parsed={"body": content},
                    key_inputs=(model, title),
                )

                row = {
                    "model": model, "label": label, "title": title, "body": content,
                    "response_id": response_id,
                    "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                out.write(json.dumps(row) + "\n"); out.flush()
                done += 1
                print(f"[{done}/{total}] {label} — {title[:60]}  →  {response_id}")
    print("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
