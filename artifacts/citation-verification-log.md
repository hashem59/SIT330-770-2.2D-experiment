# Citation Verification Log

**Verified at:** 2026-05-11T00:00:00Z
**Total entries:** 10
**RESOLVED:** 9
**RESOLVED-MISMATCH:** 1
**UNRESOLVED:** 0

## Per-entry results

| bibkey | status | arxiv | s2/web | doi | notes |
|---|---|---|---|---|---|
| saraf2025quantifying | RESOLVED-MISMATCH | title match | title match | n/a | author mismatch: all four co-authors differ — see detail below |
| panickssery2024llm | RESOLVED | title match | title match | n/a | NeurIPS 2024 confirmed |
| wataoka2024selfpreference | RESOLVED | title match | title match | n/a | match |
| wang2023large | RESOLVED | title match | title match | n/a | preprint year 2023 correct; published ACL 2024 (not in bib field) |
| chen2025do | RESOLVED | title match | title match | n/a | bib uses "and others"; full list is Wei-Lin Chen, Zhepei Wei, Xinyu Zhu, Shi Feng, Yu Meng — pre-existing C-flag acknowledged |
| zheng2023judging | RESOLVED | title match | title match | n/a | NeurIPS 2023 confirmed |
| koo2024benchmarking | RESOLVED | title match | title match | n/a | ACL 2024 Findings confirmed; CoBBLEr note in bib is correct |
| ashwin2025using | RESOLVED | n/a (preprint 2309.17147 matches note) | title/author match | 403 (publisher wall) | Sagepub DOI confirmed by search; authors Ashwin/Chhabra/Rao match |
| vallejovera2025llms | RESOLVED | n/a (preprint 2408.15895 matches note) | title/author match | Nature page match | title matches published version; authors Vallejo Vera/Driggers confirmed |
| stephan2024from | RESOLVED | title match | title match | n/a | venue = GEM2 @ ACL 2025 confirmed; year=2024 is arxiv submission year, consistent with bib note |

---

## Mismatch detail — saraf2025quantifying

This is the primary anchor citation. The four co-author names in the BibTeX entry do not match the names on the actual arxiv paper.

**BibTeX claims:**
```
author = {Saraf, Muskan and Boroujeni, Mohammad-Reza and Beaudry, Andrew and Abedi, Sasan and Bush, Hannah}
```

**arxiv HTML v1 (2508.21164) confirms:**
```
Muskan Saraf, Sajjad Rezvani Boroujeni, Justin Beaudry, Hossein Abedi, Tom Bush
```

Field-by-field diff:

| Position | BibTeX | Actual |
|---|---|---|
| 1st author | Saraf, Muskan | Muskan Saraf — MATCH |
| 2nd author | Boroujeni, Mohammad-Reza | Sajjad Rezvani Boroujeni — MISMATCH (first name wrong; "Rezvani" is middle/second name absent in bib) |
| 3rd author | Beaudry, Andrew | Justin Beaudry — MISMATCH (first name wrong) |
| 4th author | Abedi, Sasan | Hossein Abedi — MISMATCH (first name wrong) |
| 5th author | Bush, Hannah | Tom Bush — MISMATCH (first name wrong) |

**Action required:** Hashem must manually update the `author` field of `saraf2025quantifying` to:
```bibtex
author = {Saraf, Muskan and Rezvani Boroujeni, Sajjad and Beaudry, Justin and Abedi, Hossein and Bush, Tom}
```
Do not correct this automatically — the human author field is what appears in citations.

---

## Summary

- **9 RESOLVED** — all metadata (title, authors, year, venue) confirmed against at least one authoritative source.
- **1 RESOLVED-MISMATCH** — `saraf2025quantifying`: paper exists and title is correct, but all four co-author first names are wrong in the BibTeX entry.
- **0 UNRESOLVED** — no phantom citations detected.

## Go/no-go verdict for /latex-setup

**BLOCK on saraf2025quantifying.**

Fix the author field (see diff above) before compiling. All other 9 entries are clear to proceed. Once the author field is corrected and re-saved, rerun `/verify-cites` to confirm, then proceed to `/latex-setup`.
