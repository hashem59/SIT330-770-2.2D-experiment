# RUN_LOG — external API call audit trail

Per CLAUDE.md "RUN_LOG conventions": every external API call (OpenRouter
generation/evaluation, citation verification, pilot/full-run runs) is logged
here with timestamp, tool, query, result.

---

## 2026-05-10 — Step 3 judge-prompt pre-flight

**Tool:** `scripts/preflight-judge.py` (stdlib-only OpenRouter call)
**Query:** 3 hand-picked sample posts × 3 judges = 9 calls. Same prompt as
`code/evaluate.py:JUDGE_SYSTEM_PROMPT` (label = "unattributed").
**Cost:** ~$0.05 estimated.

### Run 1 — original system prompt
- Result: 6/9 passed
- All 3 failures: `google/gemini-2.5-flash`, every call wrapped in ```json``` fences
- Other judges (gpt-4o, claude-sonnet-4): 6/6 clean

### Action — prompt fix applied
Appended to system prompt in three synced files:
- `artifacts/judge-prompt.template.md`
- `code/evaluate.py:JUDGE_SYSTEM_PROMPT`
- `scripts/preflight-judge.py:JUDGE_SYSTEM_PROMPT`

> Do not wrap the JSON in markdown code fences (\`\`\`), do not prefix it
> with `json`, and do not add a preamble.

### Run 2 — tightened prompt
- Result: 8/9 passed
- 1 remaining FAIL: `google/gemini-2.5-flash` on `A_strong` — STILL
  intermittent fencing (~33% of Gemini calls), but content inside the fence
  is valid and parses cleanly via the existing fence-strip in
  `code/evaluate.py:parse_judge_json`.
- **Operational verdict:** PASS. The "fence" deviation is a style warning
  surfaced by the strict pre-flight; the runtime parser handles it
  losslessly. Gate condition from `/judge-prompt` ("any of the 9 calls
  fail to parse") is NOT triggered: all 9 parse to the correct schema.

### Threats-to-validity note for the introduction
Gemini 2.5 Flash sporadically wraps its structured output in markdown
fences even when explicitly instructed not to. We strip these in
post-processing; mention as a minor limitation in §threats-to-validity if
the prose JSON ever fails to extract.

### Step 3 status
LOCKED. Ready to proceed to Step 4 / `/pipeline`.

---

## 2026-05-11 — /verify-cites citation sweep

**Tool:** `/verify-cites` (citation-verifier agent)
**Timestamp:** 2026-05-11T00:00:00Z
**n_entries:** 10
**resolved:** 9
**mismatches:** 1 (saraf2025quantifying — all four co-author first names wrong in BibTeX)
**unresolved:** 0
**verdict:** BLOCK — fix saraf2025quantifying author field before /latex-setup compile
**Log:** `artifacts/citation-verification-log.md`
