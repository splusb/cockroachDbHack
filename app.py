"""
Flask API server - serves the dashboard UI and handles agent pipeline requests.

Flow:
  1. POST /api/investigate — runs embed + retrieve + reason, writes to DB with status='pending'
  2. GET /api/pending — list all pending (unconfirmed) incidents from DB
  3. POST /api/confirm/<incident_id> — updates status to 'confirmed' in DB
  4. DELETE /api/pending/<incident_id> — deletes the pending row from DB
  5. GET /api/incidents — list only confirmed incidents (history)
"""

import os
import sys
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.embed import embed_symptoms
from agent.retrieve import retrieve_similar_incidents
from agent.reason import reason_incident
from agent.writeback import write_incident
from agent.heal import heal_bug, identify_bug, auto_heal_from_symptoms, reset_all_bugs, get_all_flags

app = Flask(__name__, static_folder="ui")
CORS(app)


# ============================================================
# UI Routes
# ============================================================

@app.route("/")
def index():
    return send_from_directory("ui", "index.html")


@app.route("/history")
def history():
    return send_from_directory("ui", "history.html")


@app.route("/pending")
def pending_page():
    return send_from_directory("ui", "pending.html")


# ============================================================
# API Routes
# ============================================================

@app.route("/api/incidents", methods=["GET"])
def list_incidents():
    """List only CONFIRMED + AUTO_HEALED incidents from the database (the memory)."""
    from agent.config import COCKROACHDB_URL
    from agent.db import get_pool

    if not COCKROACHDB_URL:
        return jsonify({"error": "Database not configured"}), 500

    try:
        pool = get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, created_at, service, symptoms, root_cause, fix, resolved, confidence, status
                    FROM incidents
                    WHERE status IN ('confirmed', 'auto_healed')
                    ORDER BY created_at DESC
                    LIMIT 100
                    """
                )
                rows = cur.fetchall()
                incidents = []
                for row in rows:
                    incidents.append({
                        "id": str(row[0]),
                        "created_at": row[1].isoformat() if row[1] else None,
                        "service": row[2],
                        "symptoms": row[3],
                        "root_cause": row[4],
                        "fix": row[5],
                        "resolved": row[6],
                        "confidence": row[7],
                        "status": row[8],
                        "resolution": "Auto-Resolved" if row[8] == "auto_healed" else "Manual",
                    })
                return jsonify(incidents)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/pending", methods=["GET"])
def list_pending():
    """List all PENDING incidents from the database (awaiting review)."""
    from agent.config import COCKROACHDB_URL
    from agent.db import get_pool

    if not COCKROACHDB_URL:
        return jsonify({"error": "Database not configured"}), 500

    try:
        pool = get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, created_at, service, symptoms, root_cause, fix, confidence
                    FROM incidents
                    WHERE status = 'pending'
                    ORDER BY created_at DESC
                    LIMIT 100
                    """
                )
                rows = cur.fetchall()
                incidents = []
                for row in rows:
                    incidents.append({
                        "id": str(row[0]),
                        "created_at": row[1].isoformat() if row[1] else None,
                        "service": row[2],
                        "symptoms": row[3],
                        "proposed_root_cause": row[4],
                        "proposed_fix": row[5],
                        "confidence": row[6],
                    })
                return jsonify(incidents)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/investigate", methods=["POST"])
def investigate():
    """
    Run the agent pipeline:
      1. Embed symptoms
      2. Retrieve similar past incidents (vector search)
      3. Read the source code of the affected app
      4. Send symptoms + similar incidents + source code to LLM
      5. LLM returns root_cause, fix, confidence, and code_patch
      6. If code_patch is provided → apply it to disk (self-heal)
      7. Write incident to DB
    """
    data = request.get_json()
    service = data.get("service", "unknown")
    symptoms = data.get("symptoms", "")
    source = data.get("source", "dashboard")  # "demo-app" or "dashboard"

    if not symptoms:
        return jsonify({"error": "symptoms field is required"}), 400

    print(f"\n{'='*60}")
    print(f"🚨 INCIDENT REPORTED")
    print(f"{'='*60}")
    print(f"  Service:  {service}")
    print(f"  Symptoms: {symptoms}")
    print(f"{'='*60}")

    try:
        # Step 1: Embed
        print(f"  [1/5] Embedding symptoms...")
        embedding = embed_symptoms(symptoms)
        print(f"  [1/5] ✓ Embedded ({len(embedding)} dimensions)")

        # Step 2: Retrieve similar (only searches confirmed incidents)
        print(f"  [2/5] Retrieving similar confirmed incidents...")
        similar = retrieve_similar_incidents(embedding)
        print(f"  [2/5] ✓ Found {len(similar)} similar incidents")

        # Step 3: Read source code of the demo app
        print(f"  [3/5] Reading source code...")
        code_context = None  # No longer needed for file patching
        print(f"  [3/5] ✓ Using DB-flag approach (no file patching)")

        # Step 4: Reason (LLM analyzes symptoms + similar incidents)
        print(f"  [4/5] Calling LLM for analysis...")
        analysis = reason_incident(service, symptoms, similar, code_context)
        confidence = analysis.get("confidence", "low")
        print(f"  [4/5] ✓ Confidence: {confidence}")

        # Step 5: Self-heal — set heal_flag in DB if confidence is high
        healed = False
        heal_action = None
        if confidence == "high":
            print(f"  [5/5] Attempting auto-heal via DB flag...")
            heal_action = auto_heal_from_symptoms(symptoms)
            if heal_action:
                healed = True
                print(f"  [5/5] ✓ AUTO-HEALED: {heal_action}")
            else:
                print(f"  [5/5] ✗ Could not match symptoms to a known bug")
        else:
            print(f"  [5/5] ⏸ No auto-heal (confidence={confidence})")

        # Write to DB
        incident_id = None
        if healed:
            incident_id = write_incident(
                service=service,
                symptoms=symptoms,
                root_cause=analysis.get("root_cause", ""),
                fix=analysis.get("fix", ""),
                embedding=embedding,
                status="auto_healed",
                confidence=confidence,
            )
            print(f"  → Saved to memory (auto-healed): {incident_id}")
        elif source == "demo-app":
            # From demo app but NOT auto-healed → save as pending with LOW confidence label
            incident_id = write_incident(
                service=service,
                symptoms=symptoms,
                root_cause=analysis.get("root_cause", ""),
                fix=analysis.get("fix", ""),
                embedding=embedding,
                status="pending",
                confidence="low",
            )
            print(f"  → Saved as PENDING (low confidence): {incident_id}")
        else:
            # From investigate tab — don't log anywhere
            print(f"  → Not saved (investigate tab only)")
        print(f"{'='*60}\n")

        return jsonify({
            "incident_id": incident_id,
            "service": service,
            "symptoms": symptoms,
            "similar_incidents": [
                {
                    "service": inc["service"],
                    "symptoms": inc["symptoms"],
                    "root_cause": inc["root_cause"],
                    "fix": inc["fix"],
                    "distance": inc["distance"],
                }
                for inc in similar
            ],
            "proposed_root_cause": analysis.get("root_cause"),
            "proposed_fix": analysis.get("fix"),
            "confidence": confidence,
            "reasoning": analysis.get("reasoning"),
            "auto_healed": healed,
            "heal_action": heal_action,
            "status": "auto_healed" if healed else "pending",
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/confirm/<incident_id>", methods=["POST"])
def confirm_incident(incident_id):
    """
    User accepts the diagnosis — update status to 'confirmed' in CockroachDB.
    This incident now enters the memory and will be found by future vector searches.
    """
    from agent.config import COCKROACHDB_URL
    from agent.db import get_pool

    if not COCKROACHDB_URL:
        return jsonify({"error": "Database not configured"}), 500

    # Allow user to override root_cause / fix before confirming
    data = request.get_json() or {}
    root_cause_override = data.get("root_cause")
    fix_override = data.get("fix")

    try:
        pool = get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                # Build update query
                if root_cause_override or fix_override:
                    updates = ["status = 'confirmed'"]
                    params = []
                    if root_cause_override:
                        updates.append("root_cause = %s")
                        params.append(root_cause_override)
                    if fix_override:
                        updates.append("fix = %s")
                        params.append(fix_override)
                    params.append(incident_id)
                    cur.execute(
                        f"UPDATE incidents SET {', '.join(updates)} WHERE id = %s AND status = 'pending'",
                        params,
                    )
                else:
                    cur.execute(
                        "UPDATE incidents SET status = 'confirmed' WHERE id = %s AND status = 'pending'",
                        (incident_id,),
                    )
                conn.commit()

                if cur.rowcount == 0:
                    return jsonify({"error": "Incident not found or already confirmed"}), 404

        print(f"\n{'='*60}")
        print(f"✅ INCIDENT CONFIRMED: {incident_id}")
        print(f"  → Now part of memory. Future searches will find it.")
        print(f"{'='*60}\n")

        return jsonify({
            "status": "confirmed",
            "incident_id": incident_id,
            "message": "Incident confirmed and saved to memory. Future investigations will benefit.",
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/pending/<incident_id>", methods=["DELETE"])
def dismiss_incident(incident_id):
    """User dismisses the incident — delete from DB entirely."""
    from agent.config import COCKROACHDB_URL
    from agent.db import get_pool

    if not COCKROACHDB_URL:
        return jsonify({"error": "Database not configured"}), 500

    try:
        pool = get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM incidents WHERE id = %s AND status = 'pending'",
                    (incident_id,),
                )
                conn.commit()

                if cur.rowcount == 0:
                    return jsonify({"error": "Incident not found or already processed"}), 404

        print(f"\n{'='*60}")
        print(f"🗑️  INCIDENT DISMISSED: {incident_id}")
        print(f"  → Deleted from DB. Not saved to memory.")
        print(f"{'='*60}\n")

        return jsonify({
            "status": "dismissed",
            "message": "Incident dismissed and deleted. Not saved to memory.",
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/incidents/<incident_id>/resolve", methods=["PATCH"])
def resolve_incident(incident_id):
    """Mark an incident as manually resolved. Optionally update the fix text."""
    from agent.config import COCKROACHDB_URL
    from agent.db import get_pool

    if not COCKROACHDB_URL:
        return jsonify({"error": "Database not configured"}), 500

    data = request.get_json() or {}
    fix_text = data.get("fix")

    try:
        pool = get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                if fix_text:
                    cur.execute(
                        "UPDATE incidents SET resolved = true, status = 'confirmed', fix = %s WHERE id = %s",
                        (fix_text, incident_id),
                    )
                else:
                    cur.execute(
                        "UPDATE incidents SET resolved = true, status = 'confirmed' WHERE id = %s",
                        (incident_id,),
                    )
                conn.commit()

                if cur.rowcount == 0:
                    return jsonify({"error": "Incident not found"}), 404

        return jsonify({
            "status": "resolved",
            "incident_id": incident_id,
            "message": "Incident marked as manually resolved.",
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/heal/<incident_id>", methods=["POST"])
def heal_incident(incident_id):
    """
    Manually trigger self-healing for a pending incident.
    Identifies the bug from symptoms and sets the heal flag in DB.
    """
    from agent.config import COCKROACHDB_URL
    from agent.db import get_pool

    if not COCKROACHDB_URL:
        return jsonify({"error": "Database not configured"}), 500

    try:
        # Get the incident symptoms
        pool = get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT service, symptoms FROM incidents WHERE id = %s",
                    (incident_id,),
                )
                row = cur.fetchone()
                if not row:
                    return jsonify({"error": "Incident not found"}), 404
                service, symptoms = row[0], row[1]

        # Try to heal based on symptoms
        bug_id = identify_bug(symptoms)
        if not bug_id:
            return jsonify({"success": False, "error": "Could not match symptoms to a known bug"}), 400

        healed = heal_bug(bug_id)
        if not healed:
            return jsonify({"success": False, "error": f"Bug '{bug_id}' is already healed or not found"}), 400

        # Update incident status
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE incidents SET status = 'auto_healed', resolved = true WHERE id = %s",
                    (incident_id,),
                )
                conn.commit()

        return jsonify({
            "success": True,
            "incident_id": incident_id,
            "bug_id": bug_id,
            "message": f"Bug '{bug_id}' healed. The fix is now active.",
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/heal-flags", methods=["GET"])
def get_heal_flags():
    """Return the current state of all heal flags."""
    return jsonify({"success": True, "flags": get_all_flags()})


@app.route("/api/reset-bugs", methods=["POST"])
def reset_bugs():
    """Reset all bugs to unhealed AND clear non-seed incidents (full demo reset)."""
    from agent.db import get_pool

    success = reset_all_bugs()

    # Also delete any auto_healed or pending incidents (keep only seed data)
    try:
        pool = get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM incidents WHERE status IN ('auto_healed', 'pending')")
                deleted = cur.rowcount
                conn.commit()
        print(f"[reset] Deleted {deleted} non-seed incidents from memory")
    except Exception as e:
        print(f"[reset] Error clearing incidents: {e}")

    if success:
        return jsonify({"success": True, "message": "All bugs re-injected and incident memory cleared for demo."})
    return jsonify({"success": False, "error": "Failed to reset bugs"}), 500


@app.route("/api/toggle-bug", methods=["POST"])
def toggle_bug():
    """Toggle a specific bug's heal state."""
    data = request.get_json()
    bug_id = data.get("bug_id")
    healed = data.get("healed")

    if not bug_id or healed is None:
        return jsonify({"error": "bug_id and healed are required"}), 400

    try:
        from agent.db import get_pool
        pool = get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                if healed:
                    cur.execute(
                        "UPDATE heal_flags SET healed = true, healed_at = now() WHERE bug_id = %s",
                        (bug_id,)
                    )
                else:
                    cur.execute(
                        "UPDATE heal_flags SET healed = false, healed_at = NULL WHERE bug_id = %s",
                        (bug_id,)
                    )
                conn.commit()
                if cur.rowcount == 0:
                    return jsonify({"success": False, "error": "Bug not found"}), 404

        return jsonify({"success": True, "bug_id": bug_id, "healed": healed})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
