"""Exploratory THX-02 judicial-outcome classifier; never used in production.

Offline (default): inspect request shape without sending documents.
Live: explicitly opt in, and use only public/redacted documents.

    python scripts/spike_thx02.py
    python scripts/spike_thx02.py --live --output /tmp/thx02-results.jsonl
    python scripts/spike_thx02.py --gold-dir data/benchmark/decisions --live \
      --permit-third-party --limit 12 --output /tmp/thx02-gold.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_URL = "https://api.hal-x.ai/v1/decide/batch"
MODEL = "thx-02"
MAX_FREE_ITEMS = 12  # 4 questions each; 48 of the 60 decisions/minute per IP.
OUTCOME_LABELS = {
    "procedente": "procedente",
    "improcedente": "improcedente",
    "parcialmente_procedente": "parcialmente procedente",
    "acordo": "acordo",
    "extinto_sem_merito": "extinto sem mérito",
    "provido": "provido",
    "nao_provido": "não provido",
    "parcialmente_provido": "parcialmente provido",
    "nao_conhecido": "não conhecido",
    "prejudicado": "prejudicado",
    "unknown": "unknown",
}
QUESTIONS = {
    "decision_type": {
        "type": "choice",
        "instructions": (
            "Classifique o tipo do ato JUDICIAL efetivamente proferido neste documento, "
            "não as decisões citadas em relatório ou fundamentação."
        ),
        "criteria": {
            "sentenca": "Sentença: juiz decide definitivamente um pedido "
            "ou extingue o processo no grau.",
            "acordao": "Acórdão: julgamento colegiado de recurso ou ação originária.",
            "interlocutoria": "Decisão interlocutória: resolve questão incidental, "
            "não encerra o mérito da causa.",
            "despacho": "Despacho de mero expediente, sem julgamento de pedido ou recurso.",
            "outro": "Ato diferente, peça incompleta ou documento sem decisão identificável.",
        },
    },
    "outcome": {
        "type": "choice",
        "instructions": (
            "Determine exclusivamente o resultado OPERATIVO deste ato, "
            "não pedidos das partes nem decisões anteriores. "
            "Na sentença, classifique o pedido; no acórdão recursal, classifique o RECURSO. "
            "Se não houver dispositivo suficiente, use unknown."
        ),
        "criteria": {
            "procedente": "Pedido inicial julgado integralmente procedente no dispositivo.",
            "improcedente": "Pedido inicial julgado improcedente no dispositivo.",
            "parcialmente_procedente": "Pedido inicial julgado parcialmente procedente "
            "no dispositivo.",
            "acordo": "Acordo ou transação homologados judicialmente.",
            "extinto_sem_merito": "Extinção do processo sem resolução do mérito, "
            "por motivo processual.",
            "provido": "Recurso conhecido e integralmente provido no dispositivo.",
            "nao_provido": "Recurso conhecido e não provido (desprovido) no dispositivo.",
            "parcialmente_provido": "Recurso conhecido e parcialmente provido no dispositivo.",
            "nao_conhecido": "Recurso não conhecido (inadmissibilidade).",
            "prejudicado": "Recurso julgado prejudicado ou perda superveniente de objeto.",
            "unknown": "Não há julgamento conclusivo do pedido/recurso, "
            "ou é impossível determinar o resultado.",
        },
    },
    "recorrente_polo": {
        "type": "choice",
        "instructions": (
            "Qual polo interpôs o recurso OBJETO do dispositivo? "
            "Autor/requerente do pedido inicial = A; réu/requerido = P. "
            "Não confunda recorrente com parte vencedora."
        ),
        "criteria": {
            "A": "Somente o autor/parte ativa interpôs o recurso analisado.",
            "P": "Somente o réu/parte passiva interpôs o recurso analisado.",
            "ambos": "Ambos os polos interpuseram recursos analisados em conjunto.",
            "nao_aplicavel": "Não há recurso, trata-se de sentença ou outro ato não recursal.",
            "unknown": "Não é possível identificar com segurança o polo recorrente.",
        },
    },
    "winner_direct": {
        "type": "choice",
        "instructions": (
            "Considerando pedido inicial, polo recorrente e dispositivo atual, "
            "qual polo venceu materialmente a controvérsia? "
            "Sem decisão de mérito, vitória parcial ambígua ou dados insuficientes: unknown."
        ),
        "criteria": {
            "A": "Polo ativo/autor venceu integralmente o pedido "
            "ou preservou essa vitória em recurso.",
            "P": "Polo passivo/réu venceu integralmente o pedido "
            "ou preservou essa vitória em recurso.",
            "draw": "Acordo homologado, sem polo vencedor unilateral.",
            "unknown": "Sem vencedor material unívoco, decisão incidental, "
            "resultado parcial ou texto insuficiente.",
        },
    },
}
RECURSAL = {"provido", "não provido", "parcialmente provido", "não conhecido", "prejudicado"}


def resolve_winner(outcome: str, recorrente_polo: str | None) -> str:
    """Conservative, intentionally partial mapping; does not infer from proceedings alone.

    Appealed cases only resolve an *unambiguous* winner for full provimento or
    não provimento and a single known appellant. Partial outcomes abstain.
    Not a replacement for a future, complete domain-specific resolver.
    """
    if outcome == "procedente":
        return "A"
    if outcome == "improcedente":
        return "P"
    if outcome == "acordo":
        return "draw"
    if outcome in {"provido", "não provido"} and recorrente_polo in {"A", "P"}:
        if outcome == "provido":
            return recorrente_polo
        return "P" if recorrente_polo == "A" else "A"
    return "unknown"


def make_item(doc: dict[str, Any], *, think: bool, tta: int) -> dict[str, Any]:
    text = doc["text"]
    if not isinstance(text, str) or not text.strip():
        error_message = "Each document needs a nonempty string 'text'"
        raise ValueError(error_message)
    if len(text.encode("utf-8")) > 250_000:
        error_message = "Text above 250 KB: segment it first; no silent truncation"
        raise ValueError(error_message)
    return {"state": text, "questions": QUESTIONS, "think": "auto" if think else False, "tta": tta}


def decode_choice(answer: Any, allowed: set[str]) -> tuple[str, float]:
    """Validate response and use the winner *probability*, not vendor confidence."""
    if not isinstance(answer, dict) or answer.get("type") != "choice":
        error_message = "Expected THX-02 choice answer"
        raise ValueError(error_message)
    choice, probabilities = answer.get("choice"), answer.get("probabilities")
    if choice not in allowed or not isinstance(probabilities, dict):
        error_message = "Unknown THX-02 choice or missing probabilities"
        raise ValueError(error_message)
    if set(probabilities) != allowed:
        error_message = "THX-02 returned a different option set"
        raise ValueError(error_message)
    if any(
        type(value) not in (int, float) or not 0 <= value <= 1 for value in probabilities.values()
    ):
        error_message = "Invalid THX-02 probability"
        raise ValueError(error_message)
    if abs(sum(probabilities.values()) - 1) > 0.03:
        error_message = "THX-02 probabilities do not sum to one"
        raise ValueError(error_message)
    return choice, float(probabilities[choice])


def decode_response(
    doc: dict[str, Any], response: dict[str, Any], threshold: float
) -> dict[str, Any]:
    if not isinstance(response, dict) or response.get("model", "").lower() != MODEL:
        error_message = "Wrong model in THX-02 response"
        raise ValueError(error_message)
    answers = response.get("answers")
    if not isinstance(answers, dict):
        error_message = "THX-02 response missing answers"
        raise TypeError(error_message)
    choices = {
        name: decode_choice(answers.get(name), set(question["criteria"]))
        for name, question in QUESTIONS.items()
    }
    decision_type, type_p = choices["decision_type"]
    raw_outcome, outcome_p = choices["outcome"]
    polo, polo_p = choices["recorrente_polo"]
    direct, direct_p = choices["winner_direct"]
    outcome = OUTCOME_LABELS[raw_outcome]
    # No polarity inference from an untrusted/uncertain appellant label.
    is_recursal = outcome in RECURSAL
    reliable_p = min(outcome_p, polo_p) if is_recursal else outcome_p
    winner = resolve_winner(outcome, polo)
    # A procedural act cannot independently resolve the substantive dispute.
    if decision_type in {"interlocutoria", "despacho", "outro"} or type_p < threshold:
        winner = "unknown"
    if reliable_p < threshold:
        winner = "unknown"
    return {
        "id": doc["id"],
        "decision_type": decision_type,
        "decision_type_probability": type_p,
        "outcome": outcome,
        "outcome_probability": outcome_p,
        "recorrente_polo": polo,
        "recorrente_probability": polo_p,
        "winner": winner,
        "winner_rule_probability": reliable_p,
        "winner_direct": direct,
        "winner_direct_probability": direct_p,
        "abstained": winner == "unknown",
        "gold_outcome": doc.get("gold_outcome"),
        "gold_winner": doc.get("gold_winner"),
        "latency_ms": response.get("latency_ms"),
        "usage": response.get("usage", {}),
    }


def send_batch(items: list[dict[str, Any]], *, api_key: str | None = None) -> list[dict[str, Any]]:
    payload = json.dumps({"model": MODEL, "items": items}, ensure_ascii=False).encode("utf-8")
    if len(payload) > 8_000_000:
        error_message = "Batch exceeds THX API 8 MB body cap"
        raise ValueError(error_message)
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = Request(API_URL, data=payload, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=120) as response:
            body = response.read(8_000_001)
            if len(body) > 8_000_000:
                error_message = "Response too large"
                raise ValueError(error_message)
            parsed = json.loads(body)
    except HTTPError as exc:
        # Do not log body: it may echo document content or credentials.
        error_message = f"THX-02 HTTP {exc.code}; retry 429 after Retry-After"
        raise RuntimeError(error_message) from exc
    except URLError as exc:
        error_message = "THX-02 network unavailable"
        raise RuntimeError(error_message) from exc
    if not isinstance(parsed, dict) or not isinstance(parsed.get("results"), list):
        error_message = "Invalid THX-02 batch envelope"
        raise TypeError(error_message)
    if len(parsed["results"]) != len(items):
        error_message = "THX-02 batch cardinality mismatch"
        raise ValueError(error_message)
    return parsed["results"]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    docs = [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    for doc in docs:
        if not isinstance(doc.get("id"), str):
            error_message = "Each input document requires a string id"
            raise TypeError(error_message)
    if len({d["id"] for d in docs}) != len(docs):
        error_message = "Duplicate id in input"
        raise ValueError(error_message)
    return docs


def load_gold_dir(directory: Path, limit: int) -> list[dict[str, Any]]:
    """Read committed benchmark Markdown; not all older gold labels are trustworthy."""
    import yaml  # dependency already in the CausaGanha pyproject

    docs: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        if not raw.startswith("---\n"):
            continue
        _, metadata, body = raw.split("---", 2)
        info = yaml.safe_load(metadata)
        if not isinstance(info, dict) or not body.strip():
            continue
        outcome = info.get("outcome", "unknown")
        polo = info.get("recorrente_polo")
        # Historical versions omit appellant; never silently guess it.
        gold_winner = resolve_winner(outcome, polo)
        docs.append(
            {
                "id": path.stem,
                "text": body.strip(),
                "gold_outcome": outcome,
                "gold_winner": gold_winner,
            }
        )
        if len(docs) >= limit:
            break
    return docs


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    good = [r for r in results if "error" not in r]
    comparable = [r for r in good if r.get("gold_winner") in {"A", "P", "draw", "unknown"}]
    true_gate = [r for r in comparable if r["gold_winner"] != "unknown"]
    tp = sum(r["winner"] != "unknown" and r["gold_winner"] != "unknown" for r in comparable)
    fp = sum(r["winner"] != "unknown" and r["gold_winner"] == "unknown" for r in comparable)
    fn = sum(r["winner"] == "unknown" and r["gold_winner"] != "unknown" for r in comparable)
    p = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = (
        2 * p * recall / (p + recall)
        if p is not None and recall is not None and p + recall
        else None
    )
    return {
        "n_total": len(results),
        "n_valid": len(good),
        "n_errors": len(results) - len(good),
        "outcomes": dict(Counter(r["outcome"] for r in good)),
        "coverage": sum(r["winner"] != "unknown" for r in good) / len(good) if good else None,
        "gold_ratable_count": len(true_gate),
        "gate_precision": p,
        "gate_recall": recall,
        "gate_f1": f1,
        "conditional_accuracy": (
            sum(r["winner"] == r["gold_winner"] for r in true_gate) / len(true_gate)
            if true_gate
            else None
        ),
        "outcome_accuracy": (
            sum(
                r["outcome"] == r["gold_outcome"] for r in good if r.get("gold_outcome") is not None
            )
            / sum(r.get("gold_outcome") is not None for r in good)
            if any(r.get("gold_outcome") is not None for r in good)
            else None
        ),
        "direct_winner_accuracy": (
            sum(r["winner_direct"] == r["gold_winner"] for r in comparable) / len(comparable)
            if comparable
            else None
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--input", type=Path, help="JSONL with id, text, optional gold labels")
    source.add_argument(
        "--gold-dir", type=Path, help="Directory with benchmark Markdown frontmatter"
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Explicitly transmit data to HAL-X; default is offline",
    )
    parser.add_argument(
        "--permit-third-party",
        action="store_true",
        help="Confirm external transfer of non-synthetic texts is authorized",
    )
    parser.add_argument(
        "--output", type=Path, help="Write predictions as JSONL (without input texts)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=12,
        help="Max records (1..12, to respect anonymous RPM)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.90,
        help="Minimum selected probability, default 0.90",
    )
    parser.add_argument(
        "--think",
        action="store_true",
        help="Use think:auto instead of direct inference",
    )
    parser.add_argument("--tta", choices=[1, 4], type=int, default=1)
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= MAX_FREE_ITEMS:
        parser.error("--limit must be 1..12 for a single free-tier batch (4 decisions/item)")
    if not 0 <= args.threshold <= 1:
        parser.error("--threshold must be within 0..1")
    if args.live and (args.input or args.gold_dir) and not args.permit_third_party:
        parser.error("--permit-third-party required before transmitting non-synthetic texts")
    fixtures = Path(__file__).resolve().parent.parent / "tests/fixtures/thx02_spike.jsonl"
    docs = (
        load_gold_dir(args.gold_dir, args.limit)
        if args.gold_dir
        else load_jsonl(args.input or fixtures)[: args.limit]
    )
    if not docs:
        parser.error("No input documents")
    items = [make_item(d, think=args.think, tta=args.tta) for d in docs]
    if not args.live:
        print(
            json.dumps(
                {
                    "mode": "offline",
                    "model": MODEL,
                    "n_documents": len(docs),
                    "decisions": len(docs) * len(QUESTIONS),
                    "question_names": list(QUESTIONS),
                    "would_transmit": False,
                },
                ensure_ascii=False,
            )
        )
        return 0
    responses = send_batch(items, api_key=os.getenv("HALX_API_KEY"))
    results: list[dict[str, Any]] = []
    for doc, response in zip(docs, responses, strict=True):
        try:
            results.append(decode_response(doc, response, args.threshold))
        except (TypeError, ValueError, AttributeError) as exc:
            results.append({"id": doc["id"], "error": str(exc)})
    if args.output:
        args.output.write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in results),
            encoding="utf-8",
        )
    print(json.dumps(summarize(results), ensure_ascii=False, indent=2))
    return 1 if any("error" in row for row in results) else 0


if __name__ == "__main__":
    sys.exit(main())
