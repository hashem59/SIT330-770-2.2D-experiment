"""
Full-response snapshot layer. Every API call writes a complete
request+response JSON beside the existing readable outputs, so any future
audit can answer "exactly what did we send, what did the model return,
which version, with what token usage" without re-running anything.

Snapshot files:
    runs/responses/<category>/<response_id>.json

Index (one row per snapshot, lookup-friendly):
    runs/responses/index.csv
    columns: id, category, timestamp_utc, model, key_inputs, status_code

The existing JSONL/CSV outputs are unchanged in schema except for a new
`response_id` field that points at the snapshot file.

Categories used by this project:
    generations    — code/generate.py
    evaluations    — code/evaluate.py
    qwen-codings   — code/qwen_coder.py
"""
from __future__ import annotations
import csv, hashlib, json, time
from pathlib import Path
from typing import Any

INDEX_FIELDS = ["id", "category", "timestamp_utc", "model", "key_inputs", "status_code"]


def _hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]


def save(*,
         category: str,
         run_dir: Path | str,
         request: dict,
         response: dict,
         parsed: dict | None = None,
         key_inputs: tuple[Any, ...] = ()) -> str:
    """Write a snapshot file and append to the index. Return the response_id.

    Args:
        category: One of "generations" | "evaluations" | "qwen-codings".
        run_dir: The runs/ directory (Path or str).
        request: Dict with keys at minimum {"model", "messages"}; may include "url".
        response: Dict with at minimum {"status_code", "body"}; "body" is the full
            JSON returned by OpenRouter (id, model, choices, usage, ...).
        parsed: Whatever structured extraction was made from the response (for
            cross-reference). Optional.
        key_inputs: Tuple of business-key values (e.g. (judge, blog_id, condition))
            used to make the snapshot id deterministic-enough to reason about.

    Returns:
        response_id like "evaluations-a3f8b2c1".
    """
    run_dir = Path(run_dir)
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    model = request.get("model", "unknown")
    key_part = "|".join((category, model, timestamp, *map(str, key_inputs)))
    rid = f"{category}-{_hash(key_part)}"

    snap_dir = run_dir / "responses" / category
    snap_dir.mkdir(parents=True, exist_ok=True)
    snap_file = snap_dir / f"{rid}.json"

    payload = {
        "id": rid,
        "timestamp_utc": timestamp,
        "category": category,
        "request": request,
        "response": response,
        "parsed": parsed,
    }
    snap_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    index_path = run_dir / "responses" / "index.csv"
    new_idx = not index_path.exists()
    with index_path.open("a", newline="") as f:
        w = csv.writer(f)
        if new_idx:
            w.writerow(INDEX_FIELDS)
        w.writerow([
            rid, category, timestamp, model,
            "|".join(map(str, key_inputs)),
            response.get("status_code", ""),
        ])
    return rid


def load(run_dir: Path | str, response_id: str) -> dict:
    """Round-trip helper for analysis scripts that want to re-parse a response."""
    run_dir = Path(run_dir)
    category = response_id.split("-", 1)[0]
    snap_file = run_dir / "responses" / category / f"{response_id}.json"
    return json.loads(snap_file.read_text())
