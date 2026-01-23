#!/usr/bin/env python3
"""Test procedural document filter accuracy against labeled ground truth.

This script validates the ProceduralDocumentFilter against the 500 documents
labeled by 10 subagents (agents 1-10).
"""

import json
import sys
from pathlib import Path

import duckdb

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from causaganha.analysis.procedural_doc_filter import ProceduralDocumentFilter
from causaganha.config import settings


def load_agent_data(agent_id: int) -> list[dict]:
    """Load labeled data from a specific agent."""
    file_path = settings.DATA_DIR / f"ground_truth_rich_agent_{agent_id}.json"
    if not file_path.exists():
        print(f"⚠️  Agent {agent_id} file not found: {file_path}")
        return []

    with open(file_path) as f:
        data = json.load(f)
        return data.get("documents", [])


def main():
    """Test filter accuracy on all 500 labeled documents."""
    print("🔍 Testing Procedural Document Filter\n")
    print("=" * 70)

    filter_obj = ProceduralDocumentFilter()

    # Load all agent data
    all_docs = []
    for agent_id in range(1, 11):
        docs = load_agent_data(agent_id)
        all_docs.extend(docs)
        print(f"✓ Loaded {len(docs)} docs from Agent {agent_id}")

    if not all_docs:
        print("\n❌ No documents loaded. Ensure agent JSON files exist in data/")
        return

    print(f"\n📊 Total documents: {len(all_docs)}")

    # Connect to database to fetch texto
    db_path = settings.DATA_DIR / "causaganha_real.duckdb"
    print(f"📂 Loading texto from: {db_path}")
    db = duckdb.connect(str(db_path))

    print("=" * 70)

    # Test filter
    results = {
        "correct": 0,
        "incorrect": 0,
        "true_positives": 0,  # Correctly identified procedural
        "false_positives": 0,  # Said procedural, was merit
        "true_negatives": 0,  # Correctly identified merit
        "false_negatives": 0,  # Said merit, was procedural
    }

    misclassifications = []

    for doc in all_docs:
        doc_id = doc.get("doc_id")
        intimation_id = doc.get("intimation_id")

        # Get ground truth label
        decision_class = doc.get("decision_classification", {})
        decision_type = decision_class.get("decision_type", "")

        # Ground truth: is this procedural?
        is_procedural_gt = decision_type in [
            "ATO_ORDINATORIO",
            "DESPACHO",
            "INTIMACAO",
            "PROCEDURAL_ORDER",
        ]

        # Fetch texto from database
        result = db.execute(
            "SELECT texto FROM intimations WHERE id = ?",
            [intimation_id],
        ).fetchone()

        if not result or not result[0]:
            continue

        texto = result[0]

        # Classify with filter
        classification = filter_obj.classify(texto)
        is_procedural_pred = not classification.should_analyze

        # Compare
        if is_procedural_gt == is_procedural_pred:
            results["correct"] += 1
            if is_procedural_gt:
                results["true_positives"] += 1
            else:
                results["true_negatives"] += 1
        else:
            results["incorrect"] += 1
            if is_procedural_pred and not is_procedural_gt:
                results["false_positives"] += 1
            else:
                results["false_negatives"] += 1

            # Track misclassifications
            misclassifications.append(
                {
                    "doc_id": doc_id,
                    "intimation_id": intimation_id,
                    "ground_truth": "PROCEDURAL" if is_procedural_gt else "MERIT",
                    "predicted": classification.doc_type,
                    "confidence": classification.confidence,
                    "reasoning": classification.reasoning,
                    "actual_type": decision_type,
                }
            )

    # Calculate metrics
    total = results["correct"] + results["incorrect"]
    accuracy = results["correct"] / total if total > 0 else 0

    tp = results["true_positives"]
    fp = results["false_positives"]
    tn = results["true_negatives"]
    fn = results["false_negatives"]

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    # Print results
    print("\n📊 RESULTS\n")
    print(f"Total Tested:     {total}")
    print(f"Correct:          {results['correct']} ({accuracy:.1%})")
    print(f"Incorrect:        {results['incorrect']}")
    print()
    print(f"True Positives:   {tp} (correctly identified procedural)")
    print(f"True Negatives:   {tn} (correctly identified merit)")
    print(f"False Positives:  {fp} (said procedural, was merit)")
    print(f"False Negatives:  {fn} (said merit, was procedural)")
    print()
    print(f"Precision:        {precision:.1%} (of predicted procedural, how many correct)")
    print(f"Recall:           {recall:.1%} (of actual procedural, how many found)")
    print(f"F1 Score:         {f1:.1%}")
    print("=" * 70)

    # Show misclassifications
    if misclassifications:
        print(f"\n❌ Misclassifications ({len(misclassifications)}):\n")
        for i, miss in enumerate(misclassifications[:10], 1):
            print(f"{i}. Doc {miss['doc_id']} (ID: {miss['intimation_id']})")
            print(f"   Ground Truth: {miss['ground_truth']}")
            print(f"   Predicted:    {miss['predicted']} ({miss['confidence']:.0%})")
            print(f"   Actual Type:  {miss['actual_type']}")
            print(f"   Reasoning:    {miss['reasoning']}")
            print()

        if len(misclassifications) > 10:
            print(f"   ... and {len(misclassifications) - 10} more")

    # Recommendations
    print("\n💡 RECOMMENDATIONS\n")
    if accuracy >= 0.95:
        print("✅ Excellent accuracy! Filter is production-ready.")
    elif accuracy >= 0.90:
        print("✓ Good accuracy. Consider reviewing false positives.")
    elif accuracy >= 0.80:
        print("⚠️  Moderate accuracy. Review patterns and tune thresholds.")
    else:
        print("❌ Low accuracy. Significant tuning needed.")

    if fp > 0:
        print(f"   - {fp} merit decisions incorrectly filtered (missed opportunities)")
    if fn > 0:
        print(f"   - {fn} procedural docs marked for analysis (wasted compute)")

    print(f"\n✓ Filter can skip ~{recall * 100:.0f}% of procedural documents")
    print(f"✓ Saves {recall * 85:.0f}% of total compute (assuming 85% procedural rate)")
    print("=" * 70)

    db.close()


if __name__ == "__main__":
    main()
