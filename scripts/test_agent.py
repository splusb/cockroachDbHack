"""
Self-Healing Agent CLI - investigates bugs and auto-fixes code when confident.

Usage:
    python scripts/test_agent.py --service "auth-service" --symptoms "login fails with correct password"
    python scripts/test_agent.py --service "payments" --symptoms "checkout total is wrong" --file app.py
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
from agent.heal import read_app_file, apply_patch, list_app_files


def run_pipeline(service: str, symptoms: str, filename: str = None) -> dict:
    """Run the full self-healing pipeline."""

    print(f"\n{'='*60}")
    print(f"  SELF-HEALING MEMORY AGENT")
    print(f"{'='*60}")
    print(f"\n  Service:  {service}")
    print(f"  Symptoms: {symptoms}")
    if filename:
        print(f"  File:     {filename}")
    print(f"\n{'='*60}")

    # Step 1: Embed
    print("\n[1/5] Embedding symptoms...")
    embedding = embed_symptoms(symptoms)
    print(f"       ✓ Generated {len(embedding)}-dim vector")

    # Step 2: Retrieve from CockroachDB
    print("\n[2/5] Searching CockroachDB for similar past incidents...")
    similar = retrieve_similar_incidents(embedding)
    print(f"       ✓ Found {len(similar)} similar incidents")
    for i, inc in enumerate(similar[:3], 1):
        print(f"         {i}. [{inc['service']}] {inc['symptoms'][:50]}... (dist: {inc['distance']:.4f})")

    # Step 3: Read code context (if file specified)
    code_context = None
    if filename:
        print(f"\n[3/5] Reading source code: {filename}")
        code_context = read_app_file(filename)
        if code_context:
            print(f"       ✓ Loaded {len(code_context)} chars")
        else:
            print(f"       ✗ File not found")
    else:
        print(f"\n[3/5] No source file specified (skipping code analysis)")
        print(f"       Available files: {list_app_files()}")

    # Step 4: Reason (with code context for self-healing)
    print("\n[4/5] Analyzing with LLM...")
    analysis = reason_incident(service, symptoms, similar, code_context)

    print(f"\n  ┌─────────────────────────────────────────────────────")
    print(f"  │ DIAGNOSIS")
    print(f"  ├─────────────────────────────────────────────────────")
    print(f"  │ Root Cause:  {analysis.get('root_cause', 'N/A')}")
    print(f"  │ Fix:         {analysis.get('fix', 'N/A')}")
    print(f"  │ Confidence:  {analysis.get('confidence', 'N/A')}")
    print(f"  │ Reasoning:   {analysis.get('reasoning', 'N/A')[:100]}")
    if analysis.get("code_patch"):
        print(f"  │ Code Patch:  ✓ Available")
    print(f"  └─────────────────────────────────────────────────────")

    # Step 5: Self-healing — auto-apply if confidence is high
    patch_applied = False
    if analysis.get("confidence") == "high" and analysis.get("code_patch"):
        print(f"\n[5/5] SELF-HEALING: Confidence is HIGH — applying fix automatically...")
        patch_applied = apply_patch(analysis["code_patch"])
        if patch_applied:
            print(f"       ✓ Code fixed! Reload the app to see the fix in action.")
        else:
            print(f"       ✗ Patch could not be applied (manual fix needed)")
    elif analysis.get("code_patch"):
        print(f"\n[5/5] Confidence is {analysis.get('confidence')} — asking for confirmation...")
        confirm = input("       Apply the suggested fix? (y/n): ").strip().lower()
        if confirm in ("y", "yes"):
            patch_applied = apply_patch(analysis["code_patch"])
    else:
        print(f"\n[5/5] No code patch available — manual investigation needed.")

    # Write to memory (always, regardless of patch success)
    print(f"\n  Writing incident to CockroachDB memory...")
    incident_id = write_incident(
        service=service,
        symptoms=symptoms,
        root_cause=analysis.get("root_cause", ""),
        fix=analysis.get("fix", ""),
        embedding=embedding,
    )
    if incident_id:
        print(f"  ✓ Saved to memory: {incident_id}")
    else:
        print(f"  ✗ Write failed")

    # Response
    response = {
        "service": service,
        "symptoms": symptoms,
        "proposed_root_cause": analysis.get("root_cause"),
        "proposed_fix": analysis.get("fix"),
        "confidence": analysis.get("confidence"),
        "self_healed": patch_applied,
        "memory_updated": incident_id is not None,
        "similar_incidents_found": len(similar),
    }

    print(f"\n{'='*60}")
    print(json.dumps(response, indent=2))
    return response


def main():
    parser = argparse.ArgumentParser(description="Self-Healing Memory Agent")
    parser.add_argument("--service", default="demo-app")
    parser.add_argument("--symptoms", default="login fails with correct password, returns 401")
    parser.add_argument("--file", default=None, help="Source file to analyze (e.g., app.py)")
    args = parser.parse_args()
    run_pipeline(args.service, args.symptoms, args.file)


if __name__ == "__main__":
    main()
