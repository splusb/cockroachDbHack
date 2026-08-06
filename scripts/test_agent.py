"""
Local CLI test script - runs the full agent pipeline with a test alert.

Usage:
    python scripts/test_agent.py
    python scripts/test_agent.py --service "auth-service" --symptoms "JWT validation failing, 401s spiking"
"""

import argparse
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.embed import embed_symptoms
from agent.retrieve import retrieve_similar_incidents
from agent.reason import reason_incident
from agent.writeback import write_incident


def run_pipeline(service: str, symptoms: str) -> dict:
    """Run the full incident investigation pipeline."""

    print(f"\n{'='*60}")
    print(f"  INCIDENT MEMORY AGENT - Investigation")
    print(f"{'='*60}")
    print(f"\n  Service:  {service}")
    print(f"  Symptoms: {symptoms}")
    print(f"\n{'='*60}")

    # Step 1: Embed the symptoms
    print("\n[1/4] Embedding symptoms via Bedrock Titan...")
    embedding = embed_symptoms(symptoms)
    print(f"       ✓ Generated {len(embedding)}-dim vector")

    # Step 2: Retrieve similar incidents
    print("\n[2/4] Searching for similar past incidents...")
    similar = retrieve_similar_incidents(embedding)
    print(f"       ✓ Found {len(similar)} similar incidents")
    for i, inc in enumerate(similar, 1):
        print(f"         {i}. [{inc['service']}] {inc['symptoms'][:60]}... (dist: {inc['distance']:.4f})")

    # Step 3: Reason over the matches
    print("\n[3/4] Reasoning via Bedrock LLM...")
    analysis = reason_incident(service, symptoms, similar)
    print(f"       ✓ Root cause: {analysis.get('root_cause', 'N/A')[:80]}")
    print(f"       ✓ Fix: {analysis.get('fix', 'N/A')[:80]}")
    print(f"       ✓ Confidence: {analysis.get('confidence', 'N/A')}")

    # Step 4: Write back to memory
    print("\n[4/4] Writing incident to memory...")
    incident_id = write_incident(
        service=service,
        symptoms=symptoms,
        root_cause=analysis.get("root_cause", ""),
        fix=analysis.get("fix", ""),
        embedding=embedding,
    )
    memory_updated = incident_id is not None
    print(f"       ✓ Memory updated: {memory_updated}")
    if incident_id:
        print(f"       ✓ Incident ID: {incident_id}")

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
        "reasoning": analysis.get("reasoning"),
        "memory_updated": memory_updated,
        "incident_id": incident_id,
    }

    print(f"\n{'='*60}")
    print("  RESPONSE:")
    print(f"{'='*60}")
    print(json.dumps(response, indent=2))

    return response


def main():
    parser = argparse.ArgumentParser(description="Test the Incident Memory Agent pipeline")
    parser.add_argument(
        "--service",
        default="auth-service",
        help="Service name (default: auth-service)",
    )
    parser.add_argument(
        "--symptoms",
        default="JWT validation failing, 401s spiking, user sessions expiring prematurely",
        help="Symptoms/alert text",
    )
    args = parser.parse_args()

    run_pipeline(args.service, args.symptoms)


if __name__ == "__main__":
    main()
