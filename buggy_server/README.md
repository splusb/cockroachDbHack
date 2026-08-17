# ShopBroken — Self-Healing Test Target

A Flask app with 50 real Python bugs. Used to measure precision/recall of the self-healing agent.

## Setup

```bash
source venv/bin/activate
python buggy_server/app.py
```

Runs at http://localhost:7777

## Workflow (once self-healer is ready)

```
Step 1: Start buggy server
    python buggy_server/app.py

Step 2: Confirm everything is broken
    curl http://localhost:7777/metrics
    → shows 50 broken, 0 healed

Step 3: Point self-healing agent at it
    - Agent hits endpoints, sees errors
    - Agent reads buggy_server/app.py
    - Agent patches the code to fix bugs
    - Flask auto-reloads on file save

Step 4: Check results
    curl http://localhost:7777/metrics
    → shows how many are now healed

Step 5: Calculate precision/recall
    - healed / total = recall (how many bugs it fixed)
    - correct_fixes / total_attempts = precision (how many attempts were correct)
```

## What the self-healer needs to do

1. Hit an endpoint (e.g. `GET /api/user/user_1`) → gets 500
2. Read the error or read `buggy_server/app.py` to find the bug
3. Edit `buggy_server/app.py` to fix the bug (real code patch)
4. Flask reloads → endpoint returns 200

## File to patch

All bugs are in one file: `buggy_server/app.py`

Each bug is marked with `# BUG_XXX: description`

## Metrics endpoint

`GET /metrics` tests all 50 routes and returns:

```json
{
  "total": 50,
  "healed": 0,
  "broken": 50,
  "heal_rate": 0.0,
  "results": [...]
}
```

Note: takes ~10s because some bugs (infinite loop, long sleep) need to timeout.
