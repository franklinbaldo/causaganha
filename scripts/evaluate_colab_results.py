import json
from pathlib import Path


def main():
    with open("output/colab_thx02_results.jsonl", encoding="utf-8") as f:
        colab_res = [json.loads(l) for l in f]
    with open("tests/fixtures/thx02_spike.jsonl", encoding="utf-8") as f:
        fixtures = [json.loads(l) for l in f]

    correct_out = 0
    correct_win = 0
    header = f"{'ID':<4} | {'Pred Outcome':<24} | {'Gold Outcome':<24} | {'Pred Win':<8} | {'Gold Win':<8} | {'Latency':<10}"
    print(header)
    print("-" * len(header))
    for c, fix in zip(colab_res, fixtures):
        out = c["outcome"]
        gold_out = fix["gold_outcome"]
        win = c["winner"]
        gold_win = fix["gold_winner"]
        lat = c["latency_ms"]
        m_out = out == gold_out
        m_win = win == gold_win
        if m_out:
            correct_out += 1
        if m_win:
            correct_win += 1
        print(
            f"{c['id']:<4} | {out:<24} | {gold_out:<24} | {win:<8} | {gold_win:<8} | {lat:6.1f} ms"
        )

    print("-" * len(header))
    print(f"Outcome Accuracy: {correct_out}/{len(fixtures)} ({correct_out / len(fixtures):.1%})")
    print(f"Winner Accuracy:  {correct_win}/{len(fixtures)} ({correct_win / len(fixtures):.1%})")

    # Update summary file
    summary_path = Path("output/colab_thx02_summary.json")
    if summary_path.exists():
        with open(summary_path, encoding="utf-8") as f:
            summary = json.load(f)
        summary["outcome_accuracy"] = correct_out / len(fixtures)
        summary["winner_accuracy"] = correct_win / len(fixtures)
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print("Updated output/colab_thx02_summary.json with verified accuracies!")


if __name__ == "__main__":
    main()
