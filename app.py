"""
Flask API server - serves the dashboard UI and handles agent pipeline requests.
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


@app.route("/")
def index():
    return send_from_directory("ui", "index.html")


@app.route("/history")
def history():
    return send_from_directory("ui", "history.html")


@app.route("/api/incidents", methods=["GET"])
def list_incidents():
    """List all past incidents from the database."""
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
                    SELECT id, created_at, service, symptoms, root_cause, fix, resolved
                    FROM incidents
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
                    })
                return jsonify(incidents)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/investigate", methods=["POST"])
def investigate():
    """Run the full agent pipeline and return results."""
    data = request.get_json()
    service = data.get("service", "unknown")
    symptoms = data.get("symptoms", "")

    if not symptoms:
        return jsonify({"error": "symptoms field is required"}), 400

    try:
        # Step 1: Embed
        embedding = embed_symptoms(symptoms)

        # Step 2: Retrieve similar
        similar = retrieve_similar_incidents(embedding)

        # Step 3: Reason
        analysis = reason_incident(service, symptoms, similar)

        # Step 4: Write back
        incident_id = write_incident(
            service=service,
            symptoms=symptoms,
            root_cause=analysis.get("root_cause", ""),
            fix=analysis.get("fix", ""),
            embedding=embedding,
        )

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
            "memory_updated": incident_id is not None,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
