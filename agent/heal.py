"""
Self-healing module — sets heal_flags in CockroachDB to fix bugs at runtime.

Instead of patching files on disk, the agent flips a boolean flag in the database.
The demo-app checks these flags on each request and runs the fixed code path when healed.

Usage:
    from agent.heal import heal_bug, is_healed, reset_all_bugs
"""

import psycopg
from typing import Optional

from agent.config import COCKROACHDB_URL

# Maps symptom keywords to bug_ids in the heal_flags table
BUG_KEYWORD_MAP = {
    "password": "login_password_check",
    "login": "login_password_check",
    "authentication": "login_password_check",
    "inverted": "login_password_check",
    "credential": "login_password_check",
    "search": "search_column_name",
    "title": "search_column_name",
    "column": "search_column_name",
    "undefined_column": "search_column_name",
    "checkout": "checkout_total_calc",
    "total": "checkout_total_calc",
    "calculation": "checkout_total_calc",
    "multiply": "checkout_total_calc",
    "tax": "checkout_total_calc",
    "subtotal": "checkout_total_calc",
}


def heal_bug(bug_id: str) -> bool:
    """
    Mark a bug as healed in the heal_flags table.

    Args:
        bug_id: The bug identifier (e.g., 'login_password_check')

    Returns:
        True if the flag was set successfully, False otherwise.
    """
    if not COCKROACHDB_URL:
        print("[heal] No COCKROACHDB_URL configured")
        return False

    try:
        conn = psycopg.connect(COCKROACHDB_URL)
        cur = conn.cursor()
        cur.execute(
            "UPDATE heal_flags SET healed = true, healed_at = now() WHERE bug_id = %s AND healed = false",
            (bug_id,)
        )
        conn.commit()
        affected = cur.rowcount
        conn.close()

        if affected > 0:
            print(f"[heal] ✓ Bug '{bug_id}' marked as healed in DB")
            return True
        else:
            print(f"[heal] Bug '{bug_id}' was already healed or not found")
            return False
    except Exception as e:
        print(f"[heal] ERROR: {e}")
        return False


def identify_bug(symptoms: str) -> Optional[str]:
    """
    Given symptoms text, identify which bug_id it matches.

    Returns:
        The bug_id string, or None if no match found.
    """
    symptoms_lower = symptoms.lower()
    for keyword, bug_id in BUG_KEYWORD_MAP.items():
        if keyword in symptoms_lower:
            return bug_id
    return None


def auto_heal_from_symptoms(symptoms: str) -> Optional[str]:
    """
    Attempt to auto-heal based on symptoms.
    Identifies the bug and sets the flag in DB.

    Returns:
        Description of what was healed, or None if no match.
    """
    bug_id = identify_bug(symptoms)
    if not bug_id:
        print("[heal] Could not match symptoms to a known bug")
        return None

    success = heal_bug(bug_id)
    if success:
        return f"Healed bug: {bug_id}"
    return None


def is_healed(bug_id: str) -> bool:
    """Check if a bug has been healed."""
    if not COCKROACHDB_URL:
        return False
    try:
        conn = psycopg.connect(COCKROACHDB_URL)
        cur = conn.cursor()
        cur.execute("SELECT healed FROM heal_flags WHERE bug_id = %s", (bug_id,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else False
    except Exception:
        return False


def reset_all_bugs() -> bool:
    """Reset all heal flags to false (re-inject all bugs)."""
    if not COCKROACHDB_URL:
        return False
    try:
        conn = psycopg.connect(COCKROACHDB_URL)
        cur = conn.cursor()
        cur.execute("UPDATE heal_flags SET healed = false, healed_at = NULL")
        conn.commit()
        conn.close()
        print("[heal] ✓ All bugs reset to unhealed")
        return True
    except Exception as e:
        print(f"[heal] ERROR resetting: {e}")
        return False


def get_all_flags() -> list:
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
        print(f"[heal] ERROR: {e}")
        return []
