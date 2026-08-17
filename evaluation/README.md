# Evaluation Suite — Agent Pipeline Precision/Recall

Tests the incident memory agent's ability to retrieve relevant past incidents and propose correct root causes.

## Prerequisites

1. CockroachDB running locally with seed incidents loaded
2. Virtual environment activated

## Setup

```bash
# 1. Start CockroachDB (if not already running)
cockroach start-single-node --insecure --store=cockroach-data --listen-addr=localhost:26257 --http-addr=localhost:8080 --background

# 2. Create the table (if first time)
python infra/create_table.py

# 3. Seed the 25 reference incidents
python infra/seed_incidents.py
```

## Run Evaluation

```bash
source venv/bin/activate
python evaluation/run_eval.py
```

This runs 200 test incidents through the full pipeline (embed → retrieve → reason) and outputs:

- **Retrieval Precision@1** — Is the top-1 retrieved incident from the correct service?
- **Retrieval Precision@3** — Is any of the top-3 from the correct service?
- **Root Cause Accuracy** — Do expected keywords appear in the proposed root cause?
- **Per-category breakdown** of all metrics

## Output

Results are saved to `evaluation/eval_results.json` with full per-incident detail.

Console output looks like:

```
  EVALUATION RESULTS
  Total test cases:           200
  Retrieval Precision@1:      XX.XX%
  Retrieval Precision@3:      XX.XX%
  Root Cause Accuracy:        XX.XX%
  Combined Score:             XX.XX%

  Per-Category Breakdown:
  Category                          P@1    P@3   RC Acc
  auth_key_rotation                  75%    88%     63%
  payments_webhook                   50%    75%     50%
  ...
```

## What's Being Tested

- 200 test cases, 8 variations each for 25 seed incident types
- Each test is a rephrased version of a known incident pattern
- Ground truth: expected service match + expected root cause keywords
- Categories: auth, payments, search, notifications, gateway

## Files

- `test_cases.py` — 200 test incidents with ground truth labels
- `run_eval.py` — evaluation runner with metrics computation
- `eval_results.json` — output (generated after running)
