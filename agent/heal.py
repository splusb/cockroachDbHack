"""
Self-healing module — manages heal_flags in CockroachDB.

Instead of modifying source files, this approach uses a database table (heal_flags)
to toggle between buggy and fixed code paths in the demo app.

The demo app checks: if is_healed("bug_id") → use fixed code, else → use buggy code.
"""

import psycopg
from typing import Optional, List, Dict

from agent.config import COCKROACHDB_URL

# Map symptoms keywords to bug_ids
BUG_KEYWORD_MAP = {
    "login": "login_password_check",
    "password": "login_password_check",
    "401": "login_password_check",
    "credentials": "login_password_check",
    "rejected": "login_password_check",
    "inverted": "login_password_check",
    "search": "search_column_name",
    "column": "search_column_name",
    "title": "search_column_name",
    "results": "search_column_name",
    "checkout": "checkout_total_calc",
    "total": "checkout_total_calc",
    "calculation": "checkout_total_calc",
    "multiplication": "checkout_total_calc",
    "subtotal": "checkout_total_calc",
    "tax": "checkout_total_calc",
}


def identify_bug(symptoms: str) -> Optional[str]:
    """Identify which bug the symptoms relate to based on keywords."""
    symptoms_lower = symptoms.lower()
    scores = {"login_password_check": 0, "search_column_name": 0, "checkout_total_calc": 0}

    for keyword, bug_id in BUG_KEYWORD_MAP.items():
        if keyword in symptoms_lower:
            scores[bug_id] += 1

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else None


def heal_bug(bug_id: str, fix_description: str = None) -> bool:
    """Set a heal_flag to true in CockroachDB, activating the fix."""
    if not COCKROACHDB_URL:
        print("[heal] No DB URL configured")
        return False

    try:
        conn = psycopg.connect(COCKROACHDB_URL)
        cur = conn.cursor()

        if fix_description:
            cur.execute(
                "UPDATE heal_flags SET healed = true, healed_at = now(), fix_description = %s WHERE bug_id = %s AND healed = false",
                (fix_description, bug_id),
            )
        else:
            cur.execute(
                "UPDATE heal_flags SET healed = true, healed_at = now() WHERE bug_id = %s AND healed = false",
                (bug_id,),
            )

        affected = cur.rowcount
        conn.commit()
        conn.close()

        if affected > 0:
            print(f"[heal] ✓ Bug '{bug_id}' healed")
            return True
        else:
            print(f"[heal] Bug '{bug_id}' already healed or not found")
            return False

    except Exception as e:
        print(f"[heal] ERROR: {e}")
        return False


def auto_heal_from_symptoms(symptoms: str) -> Optional[str]:
    """
    Identify and heal a bug based on symptoms text.
    Returns the bug_id that was healed, or None if nothing matched.
    """
    bug_id = identify_bug(symptoms)
    if not bug_id:
        return None

    success = heal_bug(bug_id)
    return bug_id if success else None


def reset_all_bugs() -> bool:
    """Reset all heal_flags to false (re-inject all bugs for demo replay)."""
    if not COCKROACHDB_URL:
        return False

    try:
        conn = psycopg.connect(COCKROACHDB_URL)
        cur = conn.cursor()
        cur.execute("UPDATE heal_flags SET healed = false, healed_at = NULL, fix_description = NULL")
        conn.commit()
        conn.close()
        print("[heal] ✓ All bugs reset (re-injected)")
        return True
    except Exception as e:
        print(f"[heal] ERROR resetting: {e}")
        return False


def get_all_flags() -> List[Dict]:
    """Get the current state of all heal flags."""
    if not COCKROACHDB_URL:
        return []

    try:
        conn = psycopg.connect(COCKROACHDB_URL)
        cur = conn.cursor()
        cur.execute("SELECT bug_id, description, healed, healed_at, fix_description FROM heal_flags ORDER BY bug_id")
        rows = cur.fetchall()
        conn.close()
        return [{
            "bug_id": r[0],
            "description": r[1],
            "healed": r[2],
            "healed_at": r[3].isoformat() if r[3] else None,
            "fix_description": r[4],
        } for r in rows]
    except Exception as e:
        print(f"[heal] ERROR getting flags: {e}")
        return []
