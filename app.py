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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.embed import embed_symptoms
from agent.retrieve import retrieve_similar_incidents
from agent.reason import reason_incident
from agent.writeback import write_incident

app = Flask(__name__, static_folder="ui")


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


@app.route("/buggy")
def buggy():
    return send_from_directory("ui", "buggy-app.html")


# ============================================================
# API Routes
# ============================================================

@app.route("/api/incidents", methods=["GET"])
def list_incidents():
    """List only CONFIRMED incidents from the database (the memory)."""
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
                    SELECT id, created_at, service, symptoms, root_cause, fix, resolved, confidence
                    FROM incidents
                    WHERE status = 'confirmed'
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
                    SELECT id, created_at, service, symptoms, root_cause, fix, confidence, reasoning
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
                        "reasoning": row[7],
                    })
                return jsonify(incidents)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/investigate", methods=["POST"])
def investigate():
    """
    Run the agent pipeline (embed → retrieve → reason) and write to DB as 'pending'.
    The incident stays pending until a human accepts or dismisses it.
    """
    data = request.get_json()
    service = data.get("service", "unknown")
    symptoms = data.get("symptoms", "")

    if not symptoms:
        return jsonify({"error": "symptoms field is required"}), 400

    print(f"\n{'='*60}")
    print(f"🚨 INCIDENT REPORTED (status: pending)")
    print(f"{'='*60}")
    print(f"  Service:  {service}")
    print(f"  Symptoms: {symptoms}")
    print(f"{'='*60}")

    try:
        # Step 1: Embed
        print(f"  [1/4] Embedding symptoms...")
        embedding = embed_symptoms(symptoms)
        print(f"  [1/4] ✓ Embedded ({len(embedding)} dimensions)")

        # Step 2: Retrieve similar (only searches confirmed incidents)
        print(f"  [2/4] Retrieving similar confirmed incidents...")
        similar = retrieve_similar_incidents(embedding)
        print(f"  [2/4] ✓ Found {len(similar)} similar incidents")

        # Step 3: Reason
        print(f"  [3/4] Reasoning about root cause...")
        analysis = reason_incident(service, symptoms, similar)
        print(f"  [3/4] ✓ Confidence: {analysis.get('confidence', 'unknown')}")

        # Step 4: Write to DB as 'pending'
        print(f"  [4/4] Writing to DB (status=pending)...")
        incident_id = write_incident(
            service=service,
            symptoms=symptoms,
            root_cause=analysis.get("root_cause", ""),
            fix=analysis.get("fix", ""),
            embedding=embedding,
            status="pending",
            confidence=analysis.get("confidence"),
            reasoning=analysis.get("reasoning"),
        )
        print(f"  [4/4] {'✓ Saved as pending: ' + str(incident_id) if incident_id else '✗ Write failed'}")
        print(f"  → Awaiting human review (Accept / Dismiss)")
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
            "confidence": analysis.get("confidence"),
            "reasoning": analysis.get("reasoning"),
            "status": "pending",
            "message": "Incident saved as pending. Review in New Incidents tab to confirm or dismiss.",
        })

    except Exception as e:
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
    """Mark a confirmed incident as resolved."""
    from agent.config import COCKROACHDB_URL
    from agent.db import get_pool

    if not COCKROACHDB_URL:
        return jsonify({"error": "Database not configured"}), 500

    try:
        pool = get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE incidents SET resolved = true WHERE id = %s AND status = 'confirmed'",
                    (incident_id,),
                )
                conn.commit()

                if cur.rowcount == 0:
                    return jsonify({"error": "Incident not found"}), 404

        return jsonify({
            "status": "resolved",
            "incident_id": incident_id,
            "message": "Incident marked as resolved.",
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
