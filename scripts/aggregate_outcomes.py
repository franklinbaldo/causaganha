#!/usr/bin/env python3
"""Aggregate results from 10 outcome labeling agents."""

import json
from pathlib import Path
from datetime import datetime

# Load all agent results
all_documents = []
total_stats = {
    "total_labeled": 0,
    "high_confidence": 0,
    "medium_confidence": 0,
    "low_confidence": 0,
    "outcome_distribution": {
        "WIN": 0,
        "LOSS": 0,
        "PARTIAL": 0,
        "UNKNOWN": 0
    }
}

data_dir = Path("/home/user/causaganha/data")

print("📊 Aggregating Results from 10 Agents\n")
print("=" * 70)

for agent_id in range(1, 11):
    file_path = data_dir / f"outcome_labels_agent_{agent_id}.json"

    if not file_path.exists():
        print(f"⚠️  Agent {agent_id}: File not found")
        continue

    with open(file_path) as f:
        data = json.load(f)

    agent_docs = data.get("documents", [])
    agent_summary = data.get("summary", {})

    all_documents.extend(agent_docs)

    # Aggregate stats
    total_stats["total_labeled"] += agent_summary.get("total_labeled", 0)
    total_stats["high_confidence"] += agent_summary.get("high_confidence", 0)
    total_stats["medium_confidence"] += agent_summary.get("medium_confidence", 0)
    total_stats["low_confidence"] += agent_summary.get("low_confidence", 0)

    agent_dist = agent_summary.get("outcome_distribution", {})
    for outcome in ["WIN", "LOSS", "PARTIAL", "UNKNOWN"]:
        total_stats["outcome_distribution"][outcome] += agent_dist.get(outcome, 0)

    print(f"Agent {agent_id:2d}: {len(agent_docs):3d} docs, "
          f"{agent_summary.get('high_confidence', 0):2d} HIGH conf, "
          f"WIN:{agent_dist.get('WIN', 0):2d} "
          f"LOSS:{agent_dist.get('LOSS', 0):2d} "
          f"PARTIAL:{agent_dist.get('PARTIAL', 0):2d} "
          f"UNKNOWN:{agent_dist.get('UNKNOWN', 0):2d}")

print("\n" + "=" * 70)
print("📈 AGGREGATE STATISTICS\n")

print(f"Total documents labeled: {total_stats['total_labeled']}")
print(f"\nConfidence distribution:")
print(f"  HIGH:   {total_stats['high_confidence']:3d} "
      f"({total_stats['high_confidence']/total_stats['total_labeled']*100:.1f}%)")
print(f"  MEDIUM: {total_stats['medium_confidence']:3d} "
      f"({total_stats['medium_confidence']/total_stats['total_labeled']*100:.1f}%)")
print(f"  LOW:    {total_stats['low_confidence']:3d} "
      f"({total_stats['low_confidence']/total_stats['total_labeled']*100:.1f}%)")

print(f"\nOutcome distribution:")
for outcome, count in total_stats['outcome_distribution'].items():
    pct = count / total_stats['total_labeled'] * 100
    print(f"  {outcome:8s}: {count:3d} ({pct:.1f}%)")

# Calculate usable documents (non-UNKNOWN)
usable = (total_stats['outcome_distribution']['WIN'] +
          total_stats['outcome_distribution']['LOSS'] +
          total_stats['outcome_distribution']['PARTIAL'])

print(f"\n🎯 Usable for testing: {usable} documents ({usable/total_stats['total_labeled']*100:.1f}%)")
print(f"   Improvement: {usable} vs 18 original ground truth = {usable/18:.1f}x increase!")

# Save aggregated results
output = {
    "aggregation_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "total_agents": 10,
    "total_documents": len(all_documents),
    "documents": all_documents,
    "summary": total_stats
}

output_file = data_dir / "outcome_labels_aggregated.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n💾 Saved aggregated results to: {output_file}")
print("=" * 70)
