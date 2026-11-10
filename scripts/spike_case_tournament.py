"""Offline comparison of PR #1697 with learned first-match case lists.

    PYTHONPATH=src uv run --with pyarrow python scripts/spike_case_tournament.py \
        --output docs/spikes/ordered_cases_results.json

No production model, leaderboard, ratchet state, or source classifier is changed.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import platform
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from causaganha.analysis.keyword_classifier import KeywordClassifier
from causaganha.analysis.recurso_resolver import resolve_winner_polo
from causaganha.decisoes.regex_tournament import RegexTournament, build_default_tournament

NEGATION = re.compile(r"\bnão\s+(?:\w+\s+){0,3}\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class Document:
    doc_id: str
    text: str
    label: str
    court: str = ""
    recorrente_polo: str | None = None

    @property
    def text_hash(self) -> str:
        normalized = re.sub(r"\s+", " ", self.text).strip()
        return hashlib.sha256(normalized.encode()).hexdigest()


@dataclass(frozen=True)
class Case:
    """An AND of regex predicates, optional NOT(OR(...)), scope and negation guard."""

    case_id: str
    category: str
    all_of: tuple[str, ...]
    none_of: tuple[str, ...] = ()
    scope: str = "full"
    no_negation: bool = False


def catalogue() -> RegexTournament:
    """Exactly the seeds plus five extra candidates in run_regex_tournament.py."""
    t = build_default_tournament()
    for pattern, category, pattern_id in (
        (r"\bcondeno\b", "procedente", "proc_condeno_generico"),
        (r"\bpedido\s+procedente\b", "procedente", "proc_pedido_procedente"),
        (r"\brejeição\s+do\s+pedido\b", "improcedente", "improc_rejeicao_pedido"),
        (r"\bextinção\s+sem\s+resolução\b", "extinto sem mérito", "extinto_sem_res_subst"),
        (r"\bsem\s+julgamento\s+do\s+mérito\b", "extinto sem mérito", "extinto_sem_julg_merito"),
    ):
        t.register(pattern, category, pattern_id)
    return t


def generate_cases(t: RegexTournament) -> list[Case]:
    """Fixed grammar over existing regexes; no document text or labels are consulted."""
    cases = []
    for category, rules in t.categories.items():
        other_ids = tuple(
            r.pattern_id for cat, pool in t.categories.items() if cat != category for r in pool
        )
        for rule in rules:
            for scope, guarded in itertools.product(("full", "dispositivo"), (False, True)):
                cid = f"{rule.pattern_id}:{scope}:neg={guarded}"
                cases.append(Case(cid, category, (rule.pattern_id,), (), scope, guarded))
            for scope in ("full", "dispositivo"):
                cid = f"{rule.pattern_id}:{scope}:no_other_category"
                cases.append(Case(cid, category, (rule.pattern_id,), other_ids, scope, True))
        for a, b in itertools.combinations(rules, 2):
            for scope in ("full", "dispositivo"):
                cid = f"{a.pattern_id}&{b.pattern_id}:{scope}"
                cases.append(Case(cid, category, (a.pattern_id, b.pattern_id), (), scope, True))
    return cases


def match_matrix(docs: list[Document], cases: list[Case], t: RegexTournament) -> np.ndarray:
    """Cache atomic predicates; case composition then uses boolean array operations."""
    rules = {r.pattern_id: r for pool in t.categories.values() for r in pool}
    classifier = KeywordClassifier()
    scopes = {
        "full": [d.text for d in docs],
        "dispositivo": [classifier.extract_dispositivo(d.text) or "" for d in docs],
    }
    cache = {}

    def atom(pid: str, scope: str, guarded: bool) -> np.ndarray:
        key = (pid, scope, guarded)
        if key not in cache:
            pattern = rules[pid].compiled
            cache[key] = np.array(
                [
                    any(
                        not guarded or not NEGATION.search(text[max(0, m.start() - 60) : m.start()])
                        for m in pattern.finditer(text)
                    )
                    for text in scopes[scope]
                ],
                dtype=bool,
            )
        return cache[key]

    columns = []
    for case in cases:
        matches = np.ones(len(docs), dtype=bool)
        for pid in case.all_of:
            matches &= atom(pid, case.scope, case.no_negation)
        for pid in case.none_of:
            matches &= ~atom(pid, case.scope, case.no_negation)
        columns.append(matches)
    return np.column_stack(columns)


def first_match(matrix: np.ndarray, order: tuple[int, ...], actions: np.ndarray) -> np.ndarray:
    """Zero means abstention; the first satisfied case returns immediately."""
    result = np.zeros(len(matrix), dtype=int)
    for index in reversed(order):
        result[matrix[:, index]] = actions[index]
    return result


def utility(pred: np.ndarray, gold: np.ndarray, size: int, penalty: float = 2.0) -> float:
    answered = pred != 0
    correct = np.count_nonzero(answered & (pred == gold))
    wrong = np.count_nonzero(answered & (pred != gold))
    return (correct - penalty * wrong) / len(gold) - 0.001 * size


def optimize_list(
    matrix: np.ndarray,
    gold: np.ndarray,
    actions: np.ndarray,
    *,
    initial: tuple[int, ...] = (),
    fixed_members: bool = False,
    max_cases: int = 10,
    max_steps: int = 20,
) -> tuple[int, ...]:
    """Deterministic local search: insert/delete/swap; training arrays only.

    Fixed-members mode changes order only. Search is heuristic, not globally optimal.
    Constants are fixed before evaluation; test results do not select hyperparameters.
    """
    eligible = tuple(np.flatnonzero(matrix.sum(axis=0) >= 2).tolist())
    order = initial
    score = utility(first_match(matrix, order, actions), gold, len(order))
    for _ in range(max_steps):
        best_order, best_score = order, score

        def consider(candidate: tuple[int, ...]) -> None:
            nonlocal best_order, best_score
            value = utility(first_match(matrix, candidate, actions), gold, len(candidate))
            if value > best_score + 1e-12:
                best_order, best_score = candidate, value

        for i, j in itertools.combinations(range(len(order)), 2):
            swapped = list(order)
            swapped[i], swapped[j] = swapped[j], swapped[i]
            consider(tuple(swapped))
        if not fixed_members:
            for i in range(len(order)):
                consider(order[:i] + order[i + 1 :])
            if len(order) < max_cases:
                for index in eligible:
                    if index not in order:
                        for position in range(len(order) + 1):
                            consider(order[:position] + (index,) + order[position:])
        if best_order == order:
            break
        order, score = best_order, best_score
    return order


def clean_text(text: str) -> str:
    """Reuse the PR runner's HTML cleaning semantics without importing its pipeline."""
    import html

    if re.search(
        r"<(?:b|p|div|html|body|table|tr|td|article|section|span|br|header|footer)\b|&[a-z]{2,8};",
        text,
        re.I,
    ):
        text = html.unescape(text)
        text = re.sub(r"<(?:br|p|div|header|section|footer|h\d|tr)[^>]*>", "\n", text, flags=re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def prepare_gold(rows: list[dict]) -> tuple[list[Document], dict]:
    groups = defaultdict(list)
    for row in rows:
        doc = Document(
            str(row["intimation_id"]),
            clean_text(row["texto"]),
            row["outcome"],
            row.get("court", ""),
            row.get("recorrente_polo"),
        )
        groups[doc.text_hash].append(doc)
    conflicts = [key for key, docs in groups.items() if len({d.label for d in docs}) > 1]
    docs = [group[0] for key, group in sorted(groups.items()) if key not in conflicts]
    return docs, {
        "raw_rows": len(rows),
        "unique_texts": len(groups),
        "conflicting_groups_excluded": len(conflicts),
        "evaluated_rows": len(docs),
        "human_verified_rows": sum(bool(row.get("is_human_verified")) for row in rows),
        "annotation_models": dict(Counter(row.get("llm_model") for row in rows)),
    }


def external_training(rows: list[dict], gold_rows: list[dict]) -> tuple[list[Document], dict]:
    """Exclude every gold identity/text, including duplicates removed from evaluation."""
    hashes = {Document("", clean_text(r["texto"]), "").text_hash for r in gold_rows}
    ids = {str(r["intimation_id"]) for r in gold_rows}
    classifier = KeywordClassifier()
    docs, seen = [], set()
    for row in rows:
        text = clean_text(row["texto"])
        doc = Document(str(row["doc_id"]), text, "", row.get("court", ""))
        if not text or doc.doc_id in ids or doc.text_hash in hashes or doc.text_hash in seen:
            continue
        seen.add(doc.text_hash)
        docs.append(Document(doc.doc_id, text, classifier.classify(text)[0], doc.court))
    if not docs:
        raise ValueError("No disjoint external training documents remain")
    return docs, {
        "raw_rows": len(rows),
        "retained_rows": len(docs),
        "excluded_overlap_empty_or_duplicate": len(rows) - len(docs),
    }


def fold_for(doc: Document, seed: int) -> int:
    digest = hashlib.sha256(f"{seed}:{doc.text_hash}".encode()).hexdigest()
    return int(digest[:8], 16) % 5


def classification_metrics(gold: list[str], pred: list[str], labels: list[str]) -> dict:
    covered = sum(p != "unknown" for p in pred)
    errors = sum(p != "unknown" and p != y for p, y in zip(pred, gold, strict=True))
    per_class = {}
    for label in labels:
        tp = sum(p == y == label for p, y in zip(pred, gold, strict=True))
        fp = sum(p == label and y != label for p, y in zip(pred, gold, strict=True))
        fn = sum(y == label and p != label for p, y in zip(pred, gold, strict=True))
        per_class[label] = {
            "support": gold.count(label),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0,
        }
    return {
        "n": len(gold),
        "covered": covered,
        "coverage": covered / len(gold),
        "correct_answered": covered - errors,
        "errors_answered": errors,
        "selective_precision": (covered - errors) / covered if covered else None,
        "accuracy_including_unknown": sum(p == y for p, y in zip(pred, gold, strict=True))
        / len(gold),
        "macro_f1": sum(m["f1"] for m in per_class.values()) / len(labels),
        "utility_per_document": (covered - errors - 2 * errors) / len(gold),
        "per_class": per_class,
    }


def summarize(docs: list[Document], predictions: list[str], supported: list[str]) -> dict:
    result = {}
    for name, indices in (
        ("all_outcomes", list(range(len(docs)))),
        (
            "supported_plus_unknown",
            [i for i, d in enumerate(docs) if d.label in supported + ["unknown"]],
        ),
    ):
        gold = [docs[i].label for i in indices]
        pred = [predictions[i] for i in indices]
        result[name] = classification_metrics(gold, pred, supported)
    gold_polo = [resolve_winner_polo(d.label, d.recorrente_polo) for d in docs]
    pred_polo = [
        resolve_winner_polo(p, d.recorrente_polo) for d, p in zip(docs, predictions, strict=True)
    ]
    result["winner_polo_diagnostic"] = classification_metrics(
        gold_polo, pred_polo, ["A", "P", "draw"]
    )
    return result


def paired_comparison(
    docs: list[Document], reference: list[str], candidate: list[str], seed: int
) -> dict:
    """Paired bootstrap over documents; descriptive uncertainty, not a promotion gate."""

    def rewards(predictions: list[str]) -> np.ndarray:
        return np.array(
            [
                0 if pred == "unknown" else 1 if pred == doc.label else -2
                for doc, pred in zip(docs, predictions, strict=True)
            ]
        )

    differences = rewards(candidate) - rewards(reference)
    rng = np.random.default_rng(seed)
    samples = rng.integers(0, len(docs), size=(1000, len(docs)))
    deltas = differences[samples].mean(axis=1)
    return {
        "changed_predictions": sum(a != b for a, b in zip(reference, candidate, strict=True)),
        "utility_improved_documents": int(np.count_nonzero(differences > 0)),
        "utility_worsened_documents": int(np.count_nonzero(differences < 0)),
        "mean_utility_delta": float(differences.mean()),
        "bootstrap_95_percentile_interval": np.quantile(deltas, [0.025, 0.975]).tolist(),
        "bootstrap_replicates": 1000,
    }


def run_experiment(gold: list[Document], weak: list[Document], seed: int) -> dict:
    base = catalogue()
    cases = generate_cases(base)
    supported = list(base.categories)
    labels = (
        ["unknown"] + supported + sorted({d.label for d in gold} - set(supported) - {"unknown"})
    )
    encode = {label: i for i, label in enumerate(labels)}
    actions = np.array([encode[c.category] for c in cases])
    raw = tuple(
        i
        for i, c in enumerate(cases)
        if c.scope == "full" and not c.no_negation and not c.none_of and len(c.all_of) == 1
    )
    raw_by_id = {cases[i].all_of[0]: i for i in raw}
    all_docs = gold + weak
    started = time.perf_counter()
    matrix = match_matrix(all_docs, cases, base)
    feature_seconds = time.perf_counter() - started
    keyword = KeywordClassifier()
    baseline = [keyword.classify(d.text)[0] for d in gold]
    experiments = {}
    for training in ("external_weak", "gold_five_fold"):
        predictions = {
            name: ["unknown"] * len(gold)
            for name in (
                "tournament_top3",
                "promoted_order_only",
                "catalogue_ordered",
                "composite_cases",
            )
        }
        models = []
        schedules = [None] if training == "external_weak" else list(range(5))
        for fold in schedules:
            test_ids = [i for i, d in enumerate(gold) if fold is None or fold_for(d, seed) == fold]
            train_ids = (
                list(range(len(gold), len(all_docs)))
                if fold is None
                else [i for i, d in enumerate(gold) if fold_for(d, seed) != fold]
            )
            train_docs = [all_docs[i] for i in train_ids]
            train_labels = np.array([encode[d.label] for d in train_docs])
            train_matrix = matrix[train_ids]
            tournament = catalogue()
            tournament.evaluate_tournament(
                [{"texto": d.text, "desfecho_cpc": d.label} for d in train_docs]
            )
            promoted = sorted(
                [r for cat in tournament.categories for r in tournament.get_top_k(cat)],
                key=lambda r: r.score,
                reverse=True,
            )
            initial = tuple(raw_by_id[r.pattern_id] for r in promoted)
            orders = {}
            search_start = time.perf_counter()
            orders["promoted_order_only"] = optimize_list(
                train_matrix, train_labels, actions, initial=initial, fixed_members=True
            )
            raw_order = optimize_list(train_matrix[:, raw], train_labels, actions[list(raw)])
            orders["catalogue_ordered"] = tuple(raw[i] for i in raw_order)
            orders["composite_cases"] = optimize_list(train_matrix, train_labels, actions)
            search_seconds = time.perf_counter() - search_start
            for i in test_ids:
                predictions["tournament_top3"][i] = tournament.classify_best(gold[i].text)[0]
            for arm, order in orders.items():
                values = first_match(matrix[test_ids], order, actions)
                for i, value in zip(test_ids, values, strict=True):
                    predictions[arm][i] = labels[int(value)]
            # Audit the exact policies and partitions, without publishing document texts.
            models.append(
                {
                    "fold": fold,
                    "train_ids": [d.doc_id for d in train_docs],
                    "test_ids": [gold[i].doc_id for i in test_ids],
                    "search_seconds": search_seconds,
                    "initial_promoted_order": [cases[i].case_id for i in initial],
                    "selected_lists": {
                        arm: [asdict(cases[i]) for i in order] for arm, order in orders.items()
                    },
                    "training_utility": {
                        arm: utility(
                            first_match(train_matrix, order, actions), train_labels, len(order)
                        )
                        for arm, order in orders.items()
                    },
                }
            )
        experiments[training] = {
            "metrics": {arm: summarize(gold, pred, supported) for arm, pred in predictions.items()},
            "models": models,
            "predictions": [
                {
                    "doc_id": d.doc_id,
                    "text_hash": d.text_hash,
                    "gold": d.label,
                    "court": d.court,
                    "fold": fold_for(d, seed) if training == "gold_five_fold" else None,
                    **{arm: pred[i] for arm, pred in predictions.items()},
                }
                for i, d in enumerate(gold)
            ],
        }
        indices = [i for i, d in enumerate(gold) if d.label in supported + ["unknown"]]
        reference = [predictions["tournament_top3"][i] for i in indices]
        experiments[training]["paired_vs_tournament_supported"] = {
            arm: paired_comparison(
                [gold[i] for i in indices], reference, [pred[i] for i in indices], seed
            )
            for arm, pred in predictions.items()
            if arm != "tournament_top3"
        }
    return {
        "seed": seed,
        "candidate_regexes": sum(len(pool) for pool in base.categories.values()),
        "candidate_cases": len(cases),
        "case_grammar": "AND(all_of) AND NOT OR(none_of); full/dispositivo; optional no-negation",
        "feature_seconds": feature_seconds,
        "keyword_baseline": summarize(gold, baseline, supported),
        "experiments": experiments,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, default=ROOT / "data/benchmark/gold_benchmark.parquet")
    parser.add_argument(
        "--weak", type=Path, default=ROOT / "data/benchmark/djen_1000_sample.parquet"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=1697)
    args = parser.parse_args()
    rows = pq.read_table(args.gold).to_pylist()
    gold, gold_audit = prepare_gold(rows)
    weak, weak_audit = external_training(pq.read_table(args.weak).to_pylist(), rows)
    report = run_experiment(gold, weak, args.seed)
    report["provenance"] = {
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "base_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "python": sys.version,
        "platform": platform.platform(),
        "gold_sha256": hashlib.sha256(args.gold.read_bytes()).hexdigest(),
        "weak_sha256": hashlib.sha256(args.weak.read_bytes()).hexdigest(),
        "gold_audit": gold_audit,
        "weak_audit": weak_audit,
        "limitations": [
            "Exploratory outcome comparison, not a production promotion or model retraining.",
            "Gold labels are model annotations, not independently verified human truth.",
            "Exact normalized-text/identity overlap removed; near-duplicate/process leakage remains possible.",
            "Hash five-fold split is not a temporal holdout or an unseen-court evaluation.",
            "External weak labels use KeywordClassifier(full text), not the PR runner's RF-selected snippet CSV.",
            "All arms share only five first-instance output classes; appellate outcomes are reported separately via resolver diagnostics.",
            "Local search is bounded and may miss better lists; constants are fixed, not selected on held-out scores.",
            "Corpus was explored in an earlier review: these are reserved folds, not a pristine final test set.",
            "Feature preprocessing/search times exclude IO; no production end-to-end latency claim.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(f"Gold: {len(gold)}; external weak training: {len(weak)}")
    print("training / arm: covered, correct, wrong, precision, macro-F1")
    for training, experiment in report["experiments"].items():
        for arm, metrics in experiment["metrics"].items():
            m = metrics["supported_plus_unknown"]
            print(
                training,
                arm,
                {
                    k: m[k]
                    for k in (
                        "n",
                        "covered",
                        "correct_answered",
                        "errors_answered",
                        "selective_precision",
                        "macro_f1",
                    )
                },
            )
    print(f"Results: {args.output}")


if __name__ == "__main__":
    main()
