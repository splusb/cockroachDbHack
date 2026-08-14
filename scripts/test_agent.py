"""
Local CLI test script - runs the full agent pipeline with user confirmation.

Usage:
    python scripts/test_agent.py
    python scripts/test_agent.py --service "auth-service" --symptoms "JWT validation failing"
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.embed import embed_symptoms
from agent.retrieve import retrieve_similar_incidents
from agent.reason import reason_incident
from agent.writeback import write_incident


def run_pipeline(service: str, symptoms: str) -> dict:
    """Run the incident investigation pipeline with user confirmation."""

    print(f"\n{'='*60}")
    print(f"  INCIDENT MEMORY AGENT - Investigation")
    print(f"{'='*60}")
    print(f"\n  Service:  {service}")
    print(f"  Symptoms: {symptoms}")
    print(f"\n{'='*60}")

    # Step 1: Embed
    print("\n[1/4] Embedding symptoms...")
    embedding = embed_symptoms(symptoms)
    print(f"       ✓ Generated {len(embedding)}-dim vector")

    # Step 2: Retrieve from CockroachDB
    print("\n[2/4] Searching CockroachDB for similar past incidents...")
    similar = retrieve_similar_incidents(embedding)
    print(f"       ✓ Found {len(similar)} similar incidents")
    for i, inc in enumerate(similar[:3], 1):
        print(f"         {i}. [{inc['service']}] {inc['symptoms'][:60]}... (dist: {inc['distance']:.4f})")

    # Step 3: Reason
    print("\n[3/4] Analyzing incident...")
    analysis = reason_incident(service, symptoms, similar)
    print(f"\n  ┌─────────────────────────────────────────────────────")
    print(f"  │ DIAGNOSIS")
    print(f"  ├─────────────────────────────────────────────────────")
    print(f"  │ Root Cause: {analysis.get('root_cause', 'N/A')}")
    print(f"  │ Fix:        {analysis.get('fix', 'N/A')}")
    print(f"  │ Confidence: {analysis.get('confidence', 'N/A')}")
    print(f"  └─────────────────────────────────────────────────────")

    # Step 4: Ask user for confirmation
    print(f"\n[4/4] Save this incident to memory?")
    confirm = input("       Accept this diagnosis? (y/n): ").strip().lower()

    if confirm in ("y", "yes"):
        incident_id = write_incident(
            service=service,
            symptoms=symptoms,
            root_cause=analysis.get("root_cause", ""),
            fix=analysis.get("fix", ""),
            embedding=embedding,
        )
        if incident_id:
            print(f"\n  ✓ Incident saved to CockroachDB: {incident_id}")
            print(f"  ✓ Future similar alerts will now benefit from this diagnosis.")
        else:
            print(f"\n  ✗ Write failed (logged to fallback)")
    else:
        print(f"\n  ✗ Discarded — not saved to memory.")
        incident_id = None

    # Build response
    response = {
        "service": service,
        "symptoms": symptoms,
        "similar_incidents": [
            {
                "id": inc["id"],
                "service": inc["service"],
                "symptoms": inc["symptoms"],
                "root_cause": inc["root_cause"],
                "distance": inc["distance"],
            }
            for inc in similar
        ],
        "proposed_root_cause": analysis.get("root_cause"),
        "proposed_fix": analysis.get("fix"),
        "confidence": analysis.get("confidence"),
        "memory_updated": incident_id is not None,
        "incident_id": incident_id,
    }

    print(f"\n{'='*60}")
    print("  FULL RESPONSE:")
    print(f"{'='*60}")
    print(json.dumps(response, indent=2))

    return response


def main():
    parser = argparse.ArgumentParser(description="Test the Incident Memory Agent")
    parser.add_argument("--service", default="auth-service")
    parser.add_argument("--symptoms", default="JWT validation failing, 401s spiking, user sessions expiring prematurely")
    args = parser.parse_args()
    run_pipeline(args.service, args.symptoms)


if __name__ == "__main__":
    main()
