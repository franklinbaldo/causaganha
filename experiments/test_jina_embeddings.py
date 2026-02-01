"""Experiment: Test Jina AI embeddings with legal text.

This script tests the Jina AI embedding provider with sample Brazilian legal text
to verify:
1. API authentication and connectivity
2. Embedding generation quality
3. Task type differentiation (query vs document)
4. Vector dimensions and normalization
5. Performance metrics (latency, cost estimation)
"""

import asyncio
import time
from typing import Any

import structlog

from causaganha.analysis.embedding_service import EmbeddingService


# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ],
)

logger = structlog.get_logger()

# Sample legal texts for testing
SAMPLE_TEXTS = {
    "short_decision": """
    DECISÃO: Defiro a liminar requerida pelo autor, determinando a suspensão
    imediata da cobrança do débito. Requisitos presentes. Cite-se o réu.
    """,
    "partial_win": """
    SENTENÇA: Julgo PARCIALMENTE PROCEDENTE o pedido para condenar o réu ao
    pagamento de R$ 10.000,00 a título de indenização por danos morais,
    rejeitando o pedido de danos materiais por insuficiência probatória.
    Custas repartidas. Honorários fixados em 10% sobre o valor da condenação.
    """,
    "procedural_question": """
    Qual foi o resultado da decisão judicial para o autor?
    """,
    "long_decision": """
    ACÓRDÃO: Vistos, relatados e discutidos estes autos, acordam os Desembargadores
    da 1ª Câmara Cível do Tribunal de Justiça, por unanimidade, em conhecer do
    recurso e dar-lhe provimento para reformar a sentença de primeiro grau.
    Constatou-se que o autor comprovou todos os requisitos necessários para a
    procedência do pedido, apresentando documentação robusta e testemunhas idôneas.
    O réu, por sua vez, não logrou êxito em demonstrar suas alegações de defesa.
    Assim, condena-se o réu ao pagamento de R$ 50.000,00 por danos morais,
    R$ 30.000,00 por danos materiais, e R$ 10.000,00 por lucros cessantes,
    tudo corrigido monetariamente desde o ajuizamento da ação e acrescido de
    juros legais desde a citação. Custas e honorários advocatícios, fixados em
    15% sobre o valor da condenação, a cargo do réu. É como voto.
    """,
}


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    import math

    dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=False))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))

    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)


def vector_stats(embedding: list[float]) -> dict[str, Any]:
    """Calculate statistics for an embedding vector."""
    import math

    magnitude = math.sqrt(sum(x * x for x in embedding))
    mean = sum(embedding) / len(embedding)
    variance = sum((x - mean) ** 2 for x in embedding) / len(embedding)
    std_dev = math.sqrt(variance)

    return {
        "dimension": len(embedding),
        "magnitude": magnitude,
        "mean": mean,
        "std_dev": std_dev,
        "min": min(embedding),
        "max": max(embedding),
        "zero_count": sum(1 for x in embedding if abs(x) < 1e-6),
    }


async def test_jina_provider() -> None:
    """Test Jina AI embedding provider with various scenarios."""
    # Test 1: Auto-selection (should select Jina)
    start = time.time()
    await EmbeddingService.create(provider="auto")
    time.time() - start

    # Test 2: Force Jina provider
    start = time.time()
    jina_service = EmbeddingService(provider="jina")
    time.time() - start

    # Test 3: Single text embedding
    text = SAMPLE_TEXTS["short_decision"]
    start = time.time()
    embedding = await jina_service.embed_text(text, add_prefix=False)
    time.time() - start

    vector_stats(embedding)

    # Test 4: Task type differentiation (QUERY vs DOCUMENT)
    query_text = SAMPLE_TEXTS["procedural_question"]
    doc_text = SAMPLE_TEXTS["partial_win"]

    start = time.time()
    query_emb = await jina_service.embed_text(
        query_text,
        task_type="RETRIEVAL_QUERY",
        add_prefix=False,
    )
    time.time() - start

    start = time.time()
    await jina_service.embed_text(
        doc_text,
        task_type="RETRIEVAL_DOCUMENT",
        add_prefix=False,
    )
    time.time() - start

    # Test 5: Semantic similarity
    emb1 = await jina_service.embed_text(
        SAMPLE_TEXTS["short_decision"],
        task_type="RETRIEVAL_DOCUMENT",
        add_prefix=False,
    )
    emb2 = await jina_service.embed_text(
        SAMPLE_TEXTS["partial_win"],
        task_type="RETRIEVAL_DOCUMENT",
        add_prefix=False,
    )
    emb3 = await jina_service.embed_text(
        SAMPLE_TEXTS["long_decision"],
        task_type="RETRIEVAL_DOCUMENT",
        add_prefix=False,
    )

    cosine_similarity(emb1, emb2)
    cosine_similarity(emb1, emb3)
    cosine_similarity(emb2, emb3)

    # Test 6: Query-document matching
    query_emb = await jina_service.embed_text(
        "Qual foi o resultado da decisão?",
        task_type="RETRIEVAL_QUERY",
        add_prefix=False,
    )

    doc_embeddings = {
        "short": emb1,
        "partial": emb2,
        "long": emb3,
    }

    similarities = {name: cosine_similarity(query_emb, emb) for name, emb in doc_embeddings.items()}

    for _name, _sim in sorted(similarities.items(), key=lambda x: x[1], reverse=True):
        pass

    # Test 7: Batch processing
    texts = list(SAMPLE_TEXTS.values())
    start = time.time()
    await jina_service.embed_batch(texts, add_prefix=False)
    time.time() - start

    # Test 8: Contextual prefix effect
    text = SAMPLE_TEXTS["partial_win"]

    emb_no_prefix = await jina_service.embed_text(text, add_prefix=False)
    emb_with_prefix = await jina_service.embed_text(text, add_prefix=True)

    cosine_similarity(emb_no_prefix, emb_with_prefix)

    # Summary


if __name__ == "__main__":
    asyncio.run(test_jina_provider())
