"""
Agent API Server — Receives error reports from the demo app, diagnoses bugs,
and flips heal_flags in CockroachDB to activate fixes.

Runs on port 5000. The demo app (port 5001) calls this when errors occur.

Flow:
  1. Demo app detects error → calls POST /api/investigate
  2. Agent embeds symptoms → searches CockroachDB for similar incidents
  3. Agent reasons → proposes fix
  4. If confidence high → flips the heal_flag → bug is fixed on next request
  5. Writes incident to memory for future reference
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg

from agent.config import COCKROACHDB_URL
from agent.embed import embed_symptoms
from agent.retrieve import retrieve_similar_incidents
from agent.reason import reason_incident
from agent.writeback import write_incident

app = Flask(__name__)
CORS(app)

# Map symptoms keywords to bug_ids for targeted healing
BUG_KEYWORD_MAP = {
    "login": "login_password_check",
    "password": "login_password_check",
    "401": "login_password_check",
    "credentials": "login_password_check",
    "search": "search_column_name",
    "column": "search_column_name",
    "title": "search_column_name",
    "checkout": "checkout_total_calc",
    "total": "checkout_total_calc",
    "calculation": "checkout_total_calc",
    "multiplication": "checkout_total_calc",
}


def identify_bug(symptoms: str) -> str:
    """Identify which bug the symptoms relate to."""
    symptoms_lower = symptoms.lower()
    scores = {"login_password_check": 0, "search_column_name": 0, "checkout_total_calc": 0}

    for keyword, bug_id in BUG_KEYWORD_MAP.items():
        if keyword in symptoms_lower:
            scores[bug_id] += 1

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else None


def heal_bug(bug_id: str, fix_description: str) -> bool:
    """Flip a heal_flag in CockroachDB to mark a bug as fixed."""
    try:
        conn = psycopg.connect(COCKROACHDB_URL)
        cur = conn.cursor()
        cur.execute(
            "UPDATE heal_flags SET healed = true, healed_at = now(), fix_description = %s WHERE bug_id = %s",
            (fix_description, bug_id),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[agent] Failed to heal bug {bug_id}: {e}")
        return False


@app.route("/api/investigate", methods=["POST"])
def investigate():
    """
    Main agent endpoint. Receives error report, diagnoses, heals if confident.
    Called automatically by the demo app when bugs are triggered.
    """
    data = request.get_json()
    service = data.get("service", "demo-app")
    symptoms = data.get("symptoms", "")

    if not symptoms:
        return jsonify({"error": "symptoms required"}), 400

    print(f"\n{'='*50}")
    print(f"[AGENT] Investigating: {symptoms[:80]}...")
    print(f"{'='*50}")

    # Step 1: Embed symptoms
    try:
        embedding = embed_symptoms(symptoms)
        print(f"[AGENT] ✓ Embedded ({len(embedding)} dims)")
    except Exception as e:
        return jsonify({"error": f"Embedding failed: {e}"}), 500

    # Step 2: Search memory for similar incidents
    similar = retrieve_similar_incidents(embedding)
    print(f"[AGENT] ✓ Found {len(similar)} similar incidents")

    # Step 3: Reason
    analysis = reason_incident(service, symptoms, similar)
    print(f"[AGENT] ✓ Diagnosis: {analysis.get('root_cause', 'unknown')[:80]}")
    print(f"[AGENT]   Confidence: {analysis.get('confidence', 'unknown')}")

    # Step 4: Self-heal if confident
    healed = False
    bug_id = identify_bug(symptoms)

    if analysis.get("confidence") == "high" and bug_id:
        healed = heal_bug(bug_id, analysis.get("fix", ""))
        if healed:
            print(f"[AGENT] ✓ HEALED: {bug_id}")
        else:
            print(f"[AGENT] ✗ Failed to heal {bug_id}")
    elif bug_id:
        print(f"[AGENT] Confidence too low ({analysis.get('confidence')}) — not auto-healing")
    else:
        print(f"[AGENT] Could not identify specific bug from symptoms")

    # Step 5: Write to memory
    incident_id = write_incident(
        service=service,
        symptoms=symptoms,
        root_cause=analysis.get("root_cause", ""),
        fix=analysis.get("fix", ""),
        embedding=embedding,
    )
    print(f"[AGENT] ✓ Written to memory: {incident_id}")

    response = {
        "service": service,
        "symptoms": symptoms,
        "proposed_root_cause": analysis.get("root_cause"),
        "proposed_fix": analysis.get("fix"),
        "confidence": analysis.get("confidence"),
        "similar_incidents": len(similar),
        "healed": healed,
        "bug_id": bug_id,
        "incident_id": incident_id,
    }

    print(f"[AGENT] Response: healed={healed}, confidence={analysis.get('confidence')}")
    return jsonify(response)


@app.route("/api/heal", methods=["POST"])
def manual_heal():
    """Manually trigger healing for a specific bug (for demo/testing)."""
    data = request.get_json()
    bug_id = data.get("bug_id")
    fix_description = data.get("fix_description", "Manually healed")

    if not bug_id:
        return jsonify({"error": "bug_id required"}), 400

    healed = heal_bug(bug_id, fix_description)
    return jsonify({"healed": healed, "bug_id": bug_id})


@app.route("/api/reset", methods=["POST"])
def reset():
    """Reset all bugs to unhealed state."""
    try:
        conn = psycopg.connect(COCKROACHDB_URL)
        cur = conn.cursor()
        cur.execute("UPDATE heal_flags SET healed = false, healed_at = NULL, fix_description = NULL")
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "All bugs re-injected"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/status", methods=["GET"])
def status():
    """Get current heal status of all bugs."""
    try:
        conn = psycopg.connect(COCKROACHDB_URL)
        cur = conn.cursor()
        cur.execute("SELECT bug_id, description, healed, healed_at, fix_description FROM heal_flags")
        rows = cur.fetchall()
        conn.close()
        return jsonify({
            "bugs": [{
                "bug_id": r[0],
                "description": r[1],
                "healed": r[2],
                "healed_at": r[3].isoformat() if r[3] else None,
                "fix": r[4],
            } for r in rows]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  Agent API Server running at http://localhost:5000")
    print("  DB: " + (COCKROACHDB_URL[:50] + "..." if COCKROACHDB_URL else "NOT SET"))
    print("=" * 50 + "\n")
    app.run(debug=True, port=5000)
