#!/usr/bin/env python3
"""Compare 4 alternative extraction strategies for judicial decision dispositif.

Methods evaluated:
1. Canonical Regex Anchors (Ante o exposto, JULGO, ACORDAM) in last 35%
2. Tail Window (Last 2000 chars)
3. Light Paragraph Scorer (Heuristic density of operative terms in paragraphs)
4. Fixed Block Chunking (Baseline Spike / OPF simulation: 400 chars chunk)
"""

from __future__ import annotations

import json
import re
import time
from typing import Any
import pandas as pd

# ---------------------------------------------------------
# Method 1: Canonical Regex Anchors
# ---------------------------------------------------------
CANONICAL_ANCHORS = [
    r"\bante\s+(?:ao|o)\s+exposto\b",
    r"\bdiante\s+do\s+exposto\b",
    r"\bisto\s+posto\b",
    r"\bpelo\s+exposto\b",
    r"\b(?:d\s*e\s*c\s*i\s*d\s*o|decido)\b",
    r"\b(?:d\s*i\s*s\s*p\s*o\s*s\s*i\s*t\s*i\s*v\s*o|dispositivo)\b",
    r"\b(?:a\s*c\s*o\s*r\s*d\s*a\s*m|acordam)\b",
    r"\bjulgo\s+(?:procedente|improcedente|parcialmente)\b",
    r"\bhomologo\s+o\s+acordo\b",
    r"\bextingo\s+o\s+processo\b",
    r"\bpostoque\b",
]

REGEX_COMBINED = re.compile("|".join(CANONICAL_ANCHORS), re.IGNORECASE)

def extract_canonical_regex(text: str) -> dict[str, Any]:
    t0 = time.perf_counter()
    n = len(text)
    # Procurar preferencialmente nos ultimos 40% do documento
    search_start = int(n * 0.60) if n > 1500 else 0
    subtext = text[search_start:]

    matches = list(REGEX_COMBINED.finditer(subtext))
    fallback = False
    if matches:
        # Pega a ultima ocorrencia da ancora no subtrecho
        chosen = matches[-1]
        start_idx = search_start + chosen.start()
        extracted = text[start_idx:].strip()
    else:
        # Se nao achou nos 40% finais, tenta no documento inteiro
        matches_all = list(REGEX_COMBINED.finditer(text))
        if matches_all:
            chosen = matches_all[-1]
            extracted = text[chosen.start():].strip()
        else:
            # Fallback: ultimos 1500 caracteres
            extracted = text[-1500:].strip()
            fallback = True

    # Corta excesso se for absurdamente longo (> 3000 chars)
    if len(extracted) > 3000:
        extracted = extracted[:3000]

    elapsed_ms = (time.perf_counter() - t0) * 1000
    return {
        "method": "canonical_regex",
        "extracted_text": extracted,
        "char_count": len(extracted),
        "extraction_ms": elapsed_ms,
        "fallback_used": fallback,
    }


# ---------------------------------------------------------
# Method 2: Tail Window (Last 2000 chars)
# ---------------------------------------------------------
def extract_tail_window(text: str, window_size: int = 2000) -> dict[str, Any]:
    t0 = time.perf_counter()
    extracted = text[-window_size:].strip() if len(text) > window_size else text.strip()
    elapsed_ms = (time.perf_counter() - t0) * 1000
    return {
        "method": "tail_window",
        "extracted_text": extracted,
        "char_count": len(extracted),
        "extraction_ms": elapsed_ms,
        "fallback_used": False,
    }


# ---------------------------------------------------------
# Method 3: Light Paragraph Scorer
# ---------------------------------------------------------
OPERATIVE_TERMS = {
    "julgo": 3.0,
    "procedente": 2.5,
    "improcedente": 2.5,
    "extingo": 3.0,
    "homologo": 3.0,
    "acordam": 3.0,
    "condeno": 2.0,
    "dispositivo": 3.0,
    "exposto": 2.0,
    "provimento": 2.0,
    "custas": 1.0,
    "honorarios": 1.0,
    "resolucao do merito": 2.5,
    "sem resolucao do merito": 2.5,
}

def extract_paragraph_scorer(text: str) -> dict[str, Any]:
    t0 = time.perf_counter()
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text]

    num_p = len(paragraphs)
    best_idx = num_p - 1
    best_score = -1.0

    for i, p in enumerate(paragraphs):
        p_lower = p.lower()
        # Posicao relativa no documento (0 a 1)
        rel_pos = i / max(num_p - 1, 1)

        # Dispositivo raramente esta na primeira metade (apenas em atos curtissimos)
        pos_weight = 1.0 + (rel_pos * 2.0)

        term_score = sum(weight for term, weight in OPERATIVE_TERMS.items() if term in p_lower)
        total_score = term_score * pos_weight

        if total_score > best_score and term_score > 0:
            best_score = total_score
            best_idx = i

    # Junta a partir do melhor paragrafo ate o final (ou maximo de 2500 chars)
    extracted_paragraphs = paragraphs[best_idx:]
    extracted = "\n".join(extracted_paragraphs).strip()
    if len(extracted) > 2500:
        extracted = extracted[:2500]

    elapsed_ms = (time.perf_counter() - t0) * 1000
    return {
        "method": "paragraph_scorer",
        "extracted_text": extracted,
        "char_count": len(extracted),
        "extraction_ms": elapsed_ms,
        "fallback_used": (best_score <= 0),
    }


# ---------------------------------------------------------
# Method 4: Fixed Block Chunking (Baseline Spike / OPF style)
# ---------------------------------------------------------
def extract_block_chunk(text: str, chunk_size: int = 500, overlap: int = 100) -> dict[str, Any]:
    t0 = time.perf_counter()
    n = len(text)
    step = chunk_size - overlap
    chunks = []
    for i in range(0, n, step):
        chunk = text[i:i + chunk_size]
        chunks.append((i, chunk))

    # Seleciona o chunk nos ultimos 40% com maior densidade operativa
    best_chunk = chunks[-1][1] if chunks else text
    best_score = -1.0
    fallback = True

    search_threshold = n * 0.50
    for offset, chunk in chunks:
        if offset < search_threshold:
            continue
        c_lower = chunk.lower()
        score = sum(weight for term, weight in OPERATIVE_TERMS.items() if term in c_lower)
        if score > best_score and score > 2.0:
            best_score = score
            best_chunk = chunk
            fallback = False

    elapsed_ms = (time.perf_counter() - t0) * 1000
    return {
        "method": "block_chunk",
        "extracted_text": best_chunk.strip(),
        "char_count": len(best_chunk.strip()),
        "extraction_ms": elapsed_ms,
        "fallback_used": fallback,
    }


def main():
    print("Testing extraction methods on gold_benchmark sample...")
    df = pd.read_parquet("data/benchmark/gold_benchmark.parquet")

    # Amostra estratificada representativa de 20 decisoes
    target_outcomes = [
        ("procedente", 3),
        ("improcedente", 3),
        ("parcialmente procedente", 3),
        ("extinto sem mérito", 2),
        ("acordo", 2),
        ("provido", 2),
        ("não provido", 2),
        ("não conhecido", 1),
        ("unknown", 2),
    ]

    sampled_indices = []
    for out, count in target_outcomes:
        subset = df[df["outcome"] == out]
        if len(subset) >= count:
            sampled_indices.extend(subset.head(count).index.tolist())
        else:
            sampled_indices.extend(subset.index.tolist())

    sample_df = df.loc[sampled_indices].copy()
    print(f"Sample size: {len(sample_df)} decisions.")

    results = []
    for _, row in sample_df.iterrows():
        text = row["texto"]
        doc_id = row["text_uuid"]
        gold_out = row["outcome"]
        doc_type = row["decision_type"]

        m1 = extract_canonical_regex(text)
        m2 = extract_tail_window(text)
        m3 = extract_paragraph_scorer(text)
        m4 = extract_block_chunk(text)

        for m in [m1, m2, m3, m4]:
            results.append({
                "text_uuid": doc_id,
                "doc_type": doc_type,
                "gold_outcome": gold_out,
                "method": m["method"],
                "char_count": m["char_count"],
                "extraction_ms": m["extraction_ms"],
                "fallback_used": m["fallback_used"],
                "extracted_snippet": m["extracted_text"][:120].replace("\n", " "),
            })

    res_df = pd.DataFrame(results)
    print("\n--- EXTRACTION BENCHMARK SUMMARY ---")
    summary = res_df.groupby("method").agg(
        avg_chars=("char_count", "mean"),
        min_chars=("char_count", "min"),
        max_chars=("char_count", "max"),
        avg_extract_ms=("extraction_ms", "mean"),
        fallback_rate=("fallback_used", "mean")
    )
    print(summary)

if __name__ == "__main__":
    main()
