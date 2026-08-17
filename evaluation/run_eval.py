"""
Evaluation runner — feeds 200 test incidents through the agent pipeline
and measures retrieval + reasoning accuracy.

Metrics computed:
  - Retrieval Precision@1: Does the top-1 retrieved incident match the expected service?
  - Retrieval Precision@3: Is the expected service in the top-3 results?
  - Root Cause Accuracy: Do expected keywords appear in the proposed root cause?
  - Per-category breakdown of all metrics

Prerequisites:
  - CockroachDB running with seed incidents loaded (run infra/seed_incidents.py first)
  - .env configured

Usage:
    python evaluation/run_eval.py
"""

import sys
import os
import time
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.embed import embed_symptoms
from agent.retrieve import retrieve_similar_incidents
from agent.reason import reason_incident
from evaluation.test_cases import TEST_CASES


def check_keywords(text, keywords):
    """Check if any of the expected keywords appear in the text (case-insensitive)."""
    if not text:
        return False
    text_lower = text.lower()
    matches = sum(1 for kw in keywords if kw.lower() in text_lower)
    return matches >= len(keywords) / 2  # At least half the keywords must match


def run_evaluation():
    """Run all 200 test cases through the pipeline and compute metrics."""
    print(f"\n{'='*70}")
    print(f"  EVALUATION RUN — {len(TEST_CASES)} test incidents")
    print(f"  Started: {datetime.now().isoformat()}")
    print(f"{'='*70}\n")

    results = []
    category_stats = {}

    for i, test in enumerate(TEST_CASES, 1):
        symptoms = test["symptoms"]
        expected_service = test["expected_service"]
        expected_keywords = test["expected_root_cause_keywords"]
        category = test["expected_category"]

        if category not in category_stats:
            category_stats[category] = {
                "total": 0, "retrieval_p1": 0, "retrieval_p3": 0, "root_cause_match": 0
            }
        category_stats[category]["total"] += 1

        print(f"  [{i:3d}/200] {category:30s} | {symptoms[:50]}...")

        try:
            # Step 1: Embed
            embedding = embed_symptoms(symptoms)

            # Step 2: Retrieve
            similar = retrieve_similar_incidents(embedding, top_k=5)

            # Step 3: Reason
            analysis = reason_incident(expected_service, symptoms, similar)

            # Evaluate retrieval
            retrieval_p1 = False
            retrieval_p3 = False
            if similar:
                if similar[0].get("service") == expected_service:
                    retrieval_p1 = True
                if any(s.get("service") == expected_service for s in similar[:3]):
                    retrieval_p3 = True

            # Evaluate root cause
            proposed_root_cause = analysis.get("root_cause", "")
            proposed_fix = analysis.get("fix", "")
            combined_text = f"{proposed_root_cause} {proposed_fix}"
            root_cause_match = check_keywords(combined_text, expected_keywords)

            # Record result
            result = {
                "test_index": i,
                "category": category,
                "symptoms": symptoms[:80],
                "expected_service": expected_service,
                "retrieval_p1": retrieval_p1,
                "retrieval_p3": retrieval_p3,
                "root_cause_match": root_cause_match,
                "top_retrieved_service": similar[0]["service"] if similar else None,
                "top_retrieved_distance": similar[0]["distance"] if similar else None,
                "proposed_root_cause": proposed_root_cause[:100],
                "confidence": analysis.get("confidence"),
            }
            results.append(result)

            # Update category stats
            if retrieval_p1:
                category_stats[category]["retrieval_p1"] += 1
            if retrieval_p3:
                category_stats[category]["retrieval_p3"] += 1
            if root_cause_match:
                category_stats[category]["root_cause_match"] += 1

            status = "✓" if (retrieval_p1 and root_cause_match) else "✗"
            print(f"           {status} P@1={retrieval_p1} P@3={retrieval_p3} RC={root_cause_match} "
                  f"dist={similar[0]['distance']:.4f}" if similar else f"           {status} no results")

        except Exception as e:
            print(f"           ✗ ERROR: {e}")
            results.append({
                "test_index": i,
                "category": category,
                "symptoms": symptoms[:80],
                "expected_service": expected_service,
                "retrieval_p1": False,
                "retrieval_p3": False,
                "root_cause_match": False,
                "error": str(e)[:100],
            })

        # Small delay to avoid overwhelming embeddings
        time.sleep(0.1)

    # ================================================================
    # Compute aggregate metrics
    # ================================================================
    total = len(results)
    retrieval_p1_total = sum(1 for r in results if r.get("retrieval_p1"))
    retrieval_p3_total = sum(1 for r in results if r.get("retrieval_p3"))
    root_cause_total = sum(1 for r in results if r.get("root_cause_match"))

    metrics = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": total,
        "aggregate": {
            "retrieval_precision_at_1": round(retrieval_p1_total / total, 4) if total else 0,
            "retrieval_precision_at_3": round(retrieval_p3_total / total, 4) if total else 0,
            "root_cause_accuracy": round(root_cause_total / total, 4) if total else 0,
            "combined_score": round((retrieval_p1_total + root_cause_total) / (2 * total), 4) if total else 0,
        },
        "counts": {
            "retrieval_p1_correct": retrieval_p1_total,
            "retrieval_p3_correct": retrieval_p3_total,
            "root_cause_correct": root_cause_total,
        },
        "per_category": {},
        "results": results,
    }

    # Per-category metrics
    for cat, stats in sorted(category_stats.items()):
        t = stats["total"]
        metrics["per_category"][cat] = {
            "total": t,
            "retrieval_p1": round(stats["retrieval_p1"] / t, 4) if t else 0,
            "retrieval_p3": round(stats["retrieval_p3"] / t, 4) if t else 0,
            "root_cause_accuracy": round(stats["root_cause_match"] / t, 4) if t else 0,
        }

    # Print summary
    print(f"\n{'='*70}")
    print(f"  EVALUATION RESULTS")
    print(f"{'='*70}")
    print(f"  Total test cases:           {total}")
    print(f"  Retrieval Precision@1:      {metrics['aggregate']['retrieval_precision_at_1']:.2%}")
    print(f"  Retrieval Precision@3:      {metrics['aggregate']['retrieval_precision_at_3']:.2%}")
    print(f"  Root Cause Accuracy:        {metrics['aggregate']['root_cause_accuracy']:.2%}")
    print(f"  Combined Score:             {metrics['aggregate']['combined_score']:.2%}")
    print(f"\n  Per-Category Breakdown:")
    print(f"  {'Category':<32} {'P@1':>6} {'P@3':>6} {'RC Acc':>8}")
    print(f"  {'-'*32} {'-'*6} {'-'*6} {'-'*8}")
    for cat, stats in sorted(metrics["per_category"].items()):
        print(f"  {cat:<32} {stats['retrieval_p1']:>5.0%} {stats['retrieval_p3']:>5.0%} {stats['root_cause_accuracy']:>7.0%}")
    print(f"{'='*70}\n")

    # Save results to file
    output_path = os.path.join(os.path.dirname(__file__), "eval_results.json")
    with open(output_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"  Results saved to: {output_path}\n")

    return metrics


if __name__ == "__main__":
    run_evaluation()
