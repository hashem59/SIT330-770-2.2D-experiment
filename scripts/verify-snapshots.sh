#!/usr/bin/env bash
# verify-snapshots.sh — audit that every parsed-output row has a snapshot file.
#
# Run from the project root:
#     ./scripts/verify-snapshots.sh
#
# Exit code:
#   0 — every response_id resolves to a file
#   1 — one or more missing snapshots (orphan rows)
#   2 — one or more orphan snapshots (snapshot exists but no row references it)
#
# Used by /verify-cites and the citation-verifier subagent before final compile.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNS="$ROOT/runs"
RESPONSES="$ROOT/audit/snapshots"

if [ ! -d "$RESPONSES" ]; then
  echo "No snapshots directory yet ($RESPONSES). Nothing to verify."
  exit 0
fi

# Collect every response_id mentioned in parsed outputs
referenced_ids=$(mktemp)
{
  if [ -f "$RUNS/generations.jsonl" ]; then
    python3 -c '
import json, sys
for line in open("'"$RUNS/generations.jsonl"'"):
    r = json.loads(line)
    if r.get("response_id"): print(r["response_id"])
'
  fi
  if [ -f "$RUNS/evaluations.jsonl" ]; then
    python3 -c '
import json, sys
for line in open("'"$RUNS/evaluations.jsonl"'"):
    r = json.loads(line)
    if r.get("response_id"): print(r["response_id"])
'
  fi
  if [ -f "$RUNS/qwen-codings.csv" ]; then
    python3 -c '
import csv
for row in csv.DictReader(open("'"$RUNS/qwen-codings.csv"'")):
    if row.get("response_id"): print(row["response_id"])
'
  fi
} | sort -u > "$referenced_ids"

# Collect every snapshot file id on disk
on_disk=$(mktemp)
find "$RESPONSES" -name '*.json' -type f -printf '%f\n' | sed 's/\.json$//' | sort -u > "$on_disk"

# Missing: referenced but not on disk
missing=$(comm -23 "$referenced_ids" "$on_disk")
# Orphans: on disk but not referenced
orphans=$(comm -13 "$referenced_ids" "$on_disk")

n_ref=$(wc -l < "$referenced_ids")
n_disk=$(wc -l < "$on_disk")

echo "Referenced response_ids in parsed outputs: $n_ref"
echo "Snapshot files on disk:                    $n_disk"

rc=0
if [ -n "$missing" ]; then
  echo
  echo "MISSING snapshots (rows reference these but no file exists):"
  echo "$missing" | sed 's/^/  - /'
  rc=1
fi

if [ -n "$orphans" ]; then
  echo
  echo "ORPHAN snapshots (file exists but no row references it; usually a previous interrupted run):"
  echo "$orphans" | sed 's/^/  - /'
  if [ $rc -eq 0 ]; then rc=2; fi
fi

if [ $rc -eq 0 ]; then
  echo "✓ All snapshots accounted for."
fi

rm -f "$referenced_ids" "$on_disk"
exit $rc
