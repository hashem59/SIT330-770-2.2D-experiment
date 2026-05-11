# SIT330-770 Distinction Task 2.2D — Experiment Repository

**Hashem ** — Deakin University, Master's Natural Language Processing.

This repository accompanies the 2-page introduction submitted for SIT330-770 Distinction Task 2.2 (problem formulation in NLP). It contains the complete experimental pipeline, the raw + processed data, the full audit trail of every model API call, the curated lexicon, the analysis code, and the LaTeX source of the introduction.

The paper itself is `paper/introduction.pdf`. The pipeline that produced its empirical motivation is reproducible end-to-end from this repository.

---

## The research problem (one paragraph)

LLM-as-judge paradigms increasingly drive evaluation of generated text. Saraf et al. (2025) showed that providing a model-identity label alongside text causes pronounced label-induced bias in judges' _numerical scores_: the "Claude" label inflates scores regardless of authorship and the "Gemini" label depresses them. Their evaluation captured numerical scores only. The limitation this paper identifies is that _prose-level_ bias — whether judges use harsher or gentler critique language when prose is attributed to one model versus another — is invisible to score-level analysis. A 7/10 rendered with a savage prose critique is not the same evaluation as a 7/10 rendered with a gentle one. We extend Saraf et al.'s 3 × 3 × 10 × 4 factorial (3 generators × 3 judges × 10 titles × 4 attribution conditions = 360 evaluations) by adding a structured-justification prompt that elicits a critique paragraph alongside each numerical score, then code the resulting prose on three dimensions (Harshness, Identity-Reference, Rationalization) with both a rule-based lexicon (constructed corpus-driven) and a neutral LLM coder (Qwen 2.5 72B, chosen specifically because it is outside the Anthropic/OpenAI/Google lineage of the judge models).

**Headline finding.** The score-level Saraf effect did not replicate at full power (Δ(true_label − false_label_1) = −0.10 ordinal points per dimension, n.s.). The prose channel revealed an attribution asymmetry that the score channel concealed: non-OpenAI judges rated prose attributed to ChatGPT 0.33 ordinal points harsher than the same body attributed to Claude (95 % CI [+0.13, +0.55], Wilcoxon p = 0.011, sign-flip permutation p = 0.003). The effect is content-conditional: personal-narrative titles drive a mean Δ ≈ +0.70, informational/explanatory titles are effectively null. A separately-constructed corpus-driven lexicon, applied to a held-out subset, correlated positively with the Qwen ratings (Spearman ρ = +0.189, 95 % CI [+0.032, +0.341], permutation p = 0.014), giving an independent concurrent-validity check.

---

## Where to look first

For an efficient review, use this three-tier hierarchy:

| Tier | What | Files |
|---|---|---|
| **Required for marking** | The 2-page submission | `paper/introduction.pdf` |
| **Recommended supplement** | The methodology + headline numbers, ~15 min read | `artifacts/codebook.md`, `artifacts/SUPPLEMENTARY.md`, `runs/results-summary.json` |
| **Full reproducibility evidence** | Open if you want to dig in or verify specific API calls | `runs/`, `audit/`, `code/`, `scripts/` |

The repository contains every API request and response made during the experiment (751 snapshot JSONs in `audit/snapshots/`) and every per-stage log file (`audit/logs/`). This material is for audit-grade transparency only — no reviewer needs to engage with it unless they want to spot-check a specific call. The `paper/introduction.pdf` plus the three supplement files above carry the full empirical story on their own.

---

## Repository layout

```
SIT330-770-2.2D-experiment/
├── README.md                     ← you are here
├── LICENSE                       academic-use notice
├── .gitignore
├── requirements.txt              Python dependencies
│
├── code/                         the pipeline
│   ├── __init__.py
│   ├── _snapshot.py              full-response snapshot helper (audit layer)
│   ├── generate.py               Step 1 — generate 30 blog posts (3 generators × 10 titles)
│   ├── evaluate.py               Step 2 — 360 judge evaluations (3 judges × 30 blogs × 4 conditions)
│   ├── lexicon.py                Step 3a — rule-based lexicon scoring (codebook v0.2)
│   ├── build_corpus_lexicon.py   Step 3b — construct corpus-driven lexicon from a stratified
│   │                                       96-sample of pilot critiques
│   ├── apply_corpus_lexicon.py   Step 3c — apply curated lexicon to held-out 180
│   ├── qwen_coder.py             Step 4 — neutral LLM coder over all 360 critiques (Qwen 2.5 72B)
│   ├── analyze.py                Step 5 — statistics + figures
│   ├── check_model_drift.py      auxiliary — detect provider routing drift between sessions
│   ├── _confirmation_test.py     auxiliary — confirmation analyses on the held-out half
│   └── _pilot_prose_analysis.py  auxiliary — pilot-only prose analyses
│
├── scripts/
│   ├── preflight-judge.py        9-call pre-flight validating structured-JSON output
│   └── verify-snapshots.sh       audit: every parsed row has a corresponding snapshot file
│
├── artifacts/                    locked design + curated knowledge artifacts
│   ├── SUPPLEMENTARY.md          ← top-level supplement index (read this first)
│   ├── codebook.md               codebook v0.2 (three dimensions, scales, examples,
│   │                                            lexicon hints, coder-prompt fragments)
│   ├── judge-prompt.template.md  the modified judge prompt (structured JSON + justification)
│   ├── lexicon-v2-raw.json       the curated 41-marker corpus-driven lexicon
│   ├── run-config.yaml           canonical experimental design (factorial spec)
│   ├── titles.json               10 blog post titles used
│   ├── titles.README.md          editing guidance + rationale for the title set
│   ├── pilot-headline.md         pilot-stage headline (n = 180, preserved pre-full-run)
│   ├── full-run-headline.md      consolidated full-corpus headline (n = 360, with validity check)
│   ├── per-title-decomposition.md per-title × per-judge moderator analysis
│   ├── model-drift-report.md     provider routing-drift analysis (pilot vs held-out)
│   ├── citation-verification-log.md
│   ├── preflight-config.yaml     pre-flight subset of run-config.yaml
│   └── preflight-titles.json     3 sample titles for pre-flight
│
├── runs/                         processed experiment data (the readable parsed tables)
│   ├── RUN_LOG.md                consolidated event log
│   ├── generations.jsonl         30 generated blog posts
│   ├── evaluations.jsonl         360 judge evaluations (scores + justifications, parsed)
│   ├── qwen-codings.csv          Qwen ratings on all 360 critiques
│   ├── lexicon-codings.csv       rule-based lexicon (codebook v0.2 ordinal) on pilot 180
│   ├── lexicon-counts.csv        corpus-driven lexicon counts on held-out 180
│   ├── results-summary.json      machine-readable bundle of every reported statistic
│   └── preflight-*.jsonl         pre-flight outputs
│
├── audit/                        ⚠ open only if verifying specific calls or logs
│   ├── snapshots/                FULL request+response snapshots, indexed (751 files)
│   │   ├── index.csv             one row per call (id, category, timestamp, model, status)
│   │   ├── generations/<id>.json
│   │   ├── evaluations/<id>.json
│   │   ├── qwen-codings/<id>.json
│   │   └── lexicon-construction/<id>.json
│   └── logs/                     per-stage execution logs
│       ├── pilot.log
│       ├── full-run.log
│       ├── qwen-coder.log
│       └── analyze.log
│
└── paper/
    ├── introduction.tex          LaTeX source (ACM sigconf, biblatex authoryear)
    ├── introduction.skel.tex     skeleton scaffold (reference only)
    ├── references.bib            Harvard-style bibliography, every entry verified
    ├── introduction.pdf          THE 2-PAGE SUBMISSION
    ├── Makefile                  pdflatex → biber → pdflatex × 2
    └── figures/
        ├── fig1-score-vs-prose.pdf
        ├── fig2a-per-title-heatmap.pdf
        ├── fig2b-per-title-table.pdf
        ├── fig3-forest-plot.pdf
        └── fig4-validity-scatter.pdf
```

---

## Reproducing the experiment from scratch

Total wall-clock: ~1–2 hours. Total API cost: roughly USD $1–2 on OpenRouter at current rates.

### Prerequisites

- Python 3.10 or newer.
- A [OpenRouter](https://openrouter.ai/) API key with credits enabled for these models:
  - `openai/gpt-4o`
  - `google/gemini-2.5-flash`
  - `anthropic/claude-sonnet-4`
  - `qwen/qwen-2.5-72b-instruct` (for the neutral coder)
- A LaTeX distribution with `acmart`, `biblatex`, `biber` (for compiling the paper). On macOS: `brew install --cask mactex-no-gui` then `tlmgr install acmart biblatex biber`. On Linux: `sudo apt install texlive-publishers texlive-bibtex-extra biber`.

### Setup

```bash
git clone <this repository>
cd SIT330-770-2.2D-experiment

# Recommended: virtual environment
python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

# Required env var (never commit this)
export OPENROUTER_API_KEY="sk-or-v1-..."
```

### Pipeline (end-to-end)

```bash
# Step 0 — pre-flight: validate structured-JSON output across 3 judges × 3 sample posts.
#         If any of the 9 calls fails to parse, fix the prompt before scaling.
python -m scripts.preflight-judge

# Step 1 — generate 30 blog posts (3 generators × 10 titles)
python -m code.generate \
  --config artifacts/run-config.yaml \
  --titles artifacts/titles.json \
  --output runs/generations.jsonl
# idempotent: skips any (model, title) pair already present in the output

# Step 2 — judge evaluations (full factorial, 360 rows)
python -m code.evaluate \
  --config artifacts/run-config.yaml \
  --generations runs/generations.jsonl \
  --output runs/evaluations.jsonl
# idempotent over (judge, blog_id, condition)

# Step 3a — rule-based lexicon (codebook v0.2 ordinal scoring)
python -m code.lexicon \
  --evaluations runs/evaluations.jsonl \
  --output runs/lexicon-codings.csv

# Step 3b — construct corpus-driven lexicon from a stratified subsample of the pilot
python -m code.build_corpus_lexicon \
  --evaluations runs/evaluations.jsonl \
  --pilot-titles 5 \
  --construction-sample 96 \
  --output artifacts/lexicon-v2-raw.json
# the resulting JSON is then hand-curated (see artifacts/codebook.md for the curation process)

# Step 3c — apply curated lexicon to the held-out 180
python -m code.apply_corpus_lexicon \
  --lexicon artifacts/lexicon-v2-raw.json \
  --evaluations runs/evaluations.jsonl \
  --output runs/lexicon-counts.csv

# Step 4 — neutral LLM coder over all 360 critiques
python -m code.qwen_coder \
  --evaluations runs/evaluations.jsonl \
  --output runs/qwen-codings.csv

# Step 5 — statistics + figures
python -m code.analyze \
  --evaluations runs/evaluations.jsonl \
  --lexicon runs/lexicon-counts.csv \
  --qwen runs/qwen-codings.csv \
  --out-summary runs/results-summary.json \
  --out-figure-dir paper/figures
```

### Verify the audit trail

```bash
bash scripts/verify-snapshots.sh
# exit 0: every parsed row has a matching snapshot file (clean)
# exit 1: a row references a snapshot that doesn't exist (severe)
# exit 2: snapshots exist with no row referencing them (informational; usually from an interrupted run)
```

### Build the paper

```bash
cd paper
make
# runs pdflatex → biber → pdflatex × 2
# output: paper/introduction.pdf
```

---

## Methodology highlights

A few choices that matter for any reviewer or replicator:

- **Codebook v0.2 was hand-authored**, then locked before the experiment ran. See `artifacts/codebook.md`. Three dimensions: Harshness (ordinal 1–5), Identity-Reference (ordinal 1/3/5), Rationalization (ordinal 1/3/5). Each dimension has explicit definitions, scoring rules, lexicon implementation hints, and coder-prompt fragments.

- **No circularity in the qualitative coder.** Saraf et al. (2025) showed that Claude, GPT, and Gemini all exhibit systematic label bias when used as judges. Using any of those models in the _coder_ role would re-introduce the same bias the study aims to detect. The neutral coder is Qwen 2.5 72B (Alibaba lineage), explicitly chosen because it is outside the three judge model families.

- **Held-out-split lexicon construction.** The corpus-driven lexicon was built from a stratified 96-row subsample of the pilot critiques and then applied unmodified to the held-out 180. Construction set and application set are disjoint; the reported Spearman ρ is genuinely an out-of-sample validity check.

- **Full audit trail at every API call.** Every generation, evaluation, and coding call writes two artefacts:
  1. A clean row in the relevant JSONL/CSV (parsed, indexed by `response_id`).
  2. A full request+response JSON at `runs/responses/<category>/<response_id>.json` — the complete prompt sent, the complete model response body (including model version actually used, token usage, finish reason, OpenRouter request id). The `runs/responses/index.csv` file lists every snapshot.

  Any specific judgment can be traced back to the verbatim request and response that produced it. `scripts/verify-snapshots.sh` checks integrity.

- **Provider routing drift.** OpenRouter occasionally routes between provider-internal model snapshots (e.g., a specific GPT-4o `system_fingerprint`). Drift between the pilot run and the full-run is documented in `artifacts/model-drift-report.md` and discussed in the introduction's threats-to-validity. Stratifying by judge in the analysis protects against this.

- **Per-judge analysis preferred over marginal.** Because of GPT-4o-specific routing drift and the fact that ChatGPT's prose style differs sharply from Claude's, the headline statistic uses **non-OpenAI judges only** (Gemini + Claude, n = 60 paired). The marginal three-judge contrast is also reported in `runs/results-summary.json` for comparison.

---

## Files reference

| File                                   | Why a reviewer would open it                                                                                                                  |
| -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `paper/introduction.pdf`               | The 2-page submission.                                                                                                                        |
| `artifacts/codebook.md`                | The locked codebook v0.2 — what the three dimensions mean.                                                                                    |
| `artifacts/full-run-headline.md`       | Consolidated findings narrative with all numbers + 95 % CIs + p-values.                                                                       |
| `artifacts/per-title-decomposition.md` | Why the prose-channel effect is content-conditional, with per-title × per-judge tables.                                                       |
| `artifacts/model-drift-report.md`      | The OpenRouter routing-drift caveat that motivated stratifying by judge.                                                                      |
| `runs/results-summary.json`            | Machine-readable bundle of every statistic reported in the paper.                                                                             |
| `runs/responses/`                      | Every API call, requestable and inspectable in full.                                                                                          |
| `runs/RUN_LOG.md`                      | Timestamped event log of the whole pipeline.                                                                                                  |
| `paper/references.bib`                 | Harvard-style bibliography. Every entry was verified against arxiv / DOI; verification log lives at `artifacts/citation-verification-log.md`. |

---

## Citations

The paper builds primarily on:

- **Saraf et al. (2025)** _Quantifying Label-Induced Bias in Large Language Model Self- and Cross-Evaluations._ arXiv:2508.21164. — the anchor paper this work extends.
- **Panickssery, Bowman & Feng (2024)** _LLM Evaluators Recognize and Favor Their Own Generations._ NeurIPS 2024.
- **Wataoka, Takahashi & Ri (2024)** _Self-Preference Bias in LLM-as-a-Judge._ arXiv:2410.21819.
- **Zheng et al. (2023)** _Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena._ NeurIPS 2023.
- **Koo et al. (2024)** _Benchmarking Cognitive Biases in Large Language Models as Evaluators._ Findings of ACL 2024.
- **Ashwin, Chhabra & Rao (2025)** _Using Large Language Models for Qualitative Analysis can Introduce Serious Bias._ Sociological Methods & Research. — methodological justification for the neutral coder choice.

Full bibliography in `paper/references.bib`.

---

## Notes for the tutor

- **The introduction prose is entirely my own writing.** AI assistance was limited to scaffolding (LaTeX template setup, code, statistical computation, figure generation, citation verification). The argument, the framing, the limitation identified, the formal research question, and the contribution statement are mine. The codebook was hand-authored before the experiment ran.
- **The pipeline ran on May 9–10, 2026.** Provider model versions are recorded in every snapshot under `runs/responses/`; the headline numbers reproduce from the data in this repository.
- I'm happy to walk through any step of the pipeline or the analysis in a follow-up meeting.

— Hashem
