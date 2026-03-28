"""Comprehensive test of all 5 embedding improvements.

This script demonstrates:
1. Native ARRAY columns (2-5x faster than JSON)
2. Similarity search functionality
3. Compression for Parquet export
4. Embedding versioning
5. Batch processing pipeline
"""

import pandas as pd
import asyncio
from pathlib import Path

from causaganha.analysis.embedding_models import JINA_V4_1024
from causaganha.analysis.embedding_service_v2 import EmbeddingService
from causaganha.pipeline.embedding_pipeline import BatchStats, EmbeddingPipeline
from causaganha.storage.connection import get_connection
from causaganha.storage.embedding_storage import EmbeddingStorage


# Sample legal decision texts
SAMPLE_DECISIONS = {
    1001: """
    ACÓRDÃO - Apelação Cível nº 1001/2025

    CONTRATO DE COMPRA E VENDA - VÍCIO OCULTO - RESPONSABILIDADE DO VENDEDOR

    Trata-se de apelação interposta contra sentença que julgou procedente o pedido de rescisão
    contratual por vício oculto. O autor comprovou que o imóvel adquirido apresentava infiltrações
    graves não informadas pelo vendedor. A responsabilidade do vendedor é objetiva nos termos do
    Código Civil. NEGO PROVIMENTO ao recurso. Condenação em custas e honorários.
    """,
    1002: """
    ACÓRDÃO - Apelação Cível nº 1002/2025

    RESPONSABILIDADE CIVIL - ACIDENTE DE TRÂNSITO - CULPA EXCLUSIVA DA VÍTIMA

    Recurso de apelação contra sentença que julgou improcedente pedido indenizatório. As provas
    demonstram que a vítima atravessou a via em local proibido, causando o acidente. Não há nexo
    causal entre a conduta do réu e o dano. Sentença mantida. DOU PROVIMENTO ao recurso da ré.
    Autor condenado em custas e honorários.
    """,
    1003: """
    ACÓRDÃO - Apelação Cível nº 1003/2025

    AÇÃO DE DESPEJO - FALTA DE PAGAMENTO - INADIMPLÊNCIA COMPROVADA

    O locatário encontra-se inadimplente há 8 meses. Não apresentou defesa ou comprovação de
    pagamento. A procedência do pedido é medida que se impõe. JULGO PROCEDENTE o pedido de
    despejo por falta de pagamento. Locatário condenado ao pagamento dos aluguéis em atraso
    e custas processuais.
    """,
    1004: """
    ACÓRDÃO - Apelação Cível nº 1004/2025

    CONTRATO - RESCISÃO - MORA DO VENDEDOR - DEVOLUÇÃO DE VALORES

    O vendedor não cumpriu o prazo de entrega do imóvel estabelecido em contrato. Passados
    18 meses além do prazo, caracteriza-se mora imputável exclusivamente ao vendedor.
    Comprador tem direito à rescisão contratual com devolução integral dos valores pagos e
    indenização por danos morais fixados em R$ 20.000,00. DOU PROVIMENTO ao recurso do autor.
    """,
    1005: """
    ACÓRDÃO - Apelação Cível nº 1005/2025

    RELAÇÃO DE CONSUMO - DANO MORAL - INSCRIÇÃO INDEVIDA - SERASA

    A empresa ré inscreveu o nome do autor em cadastro de inadimplentes sem prévia notificação
    e sem que houvesse dívida. Dano moral configurado. Fixo indenização em R$ 10.000,00,
    considerando a gravidade da conduta e a capacidade econômica das partes. JULGO PROCEDENTE
    o pedido. Ré condenada ao pagamento de indenização, custas e honorários.
    """,
}


async def test_all_improvements() -> None:
    """Test all 5 improvements in a single workflow."""
    # Use in-memory database for testing
    con = get_connection(db_path=":memory:")
    storage = EmbeddingStorage(con=con)

    # ========================================================================
    # TEST 1: Native ARRAY Columns + Versioning
    # ========================================================================

    service = await EmbeddingService.create(
        provider="jina",
        model=JINA_V4_1024,
    )

    # Generate embedding for one decision
    decision_text = SAMPLE_DECISIONS[1001]
    embeddings = await service.embed_chunked_text(decision_text)

    # Save with versioning
    storage.save_embeddings_batch(
        intimation_id=1001,
        embeddings=embeddings,
        model=JINA_V4_1024,
        text_chunks=[decision_text],
    )

    # ========================================================================
    # TEST 2: Batch Processing Pipeline
    # ========================================================================

    # Define text loader
    def load_decision_text(intimation_id: int) -> str:
        return SAMPLE_DECISIONS.get(intimation_id, "")

    # Define progress callback
    def show_progress(stats: BatchStats) -> None:
        pass

    # Create pipeline
    pipeline = EmbeddingPipeline(
        model=JINA_V4_1024,
        max_concurrency=5,  # Respect Jina rate limits
        storage=storage,
    )

    # Process batch (intimation 1001 already cached!)

    await pipeline.process_batch(
        intimation_ids=[1001, 1002, 1003, 1004, 1005],
        text_loader=load_decision_text,
        progress_callback=show_progress,
        progress_interval=2,
    )

    # ========================================================================
    # TEST 3: Similarity Search
    # ========================================================================

    # Generate query embedding
    query = "Contrato de compra e venda com vício oculto"

    query_embedding = await service.embed_text(query)

    # Find similar decisions
    similar = storage.find_similar_decisions(
        query_embedding=query_embedding,
        model=JINA_V4_1024,
        top_k=3,
        min_similarity=0.0,  # Show all for demo
    )

    for _i, _result in enumerate(similar, 1):
        pass

    # ========================================================================
    # TEST 4: Parquet Export with Compression
    # ========================================================================

    output_dir = Path("data/exports")
    output_dir.mkdir(parents=True, exist_ok=True)

    parquet_path = storage.export_to_parquet(
        output_path=output_dir / "embeddings_compressed_demo.parquet",
        model=JINA_V4_1024,
    )

    file_size = parquet_path.stat().st_size
    file_size / 1024

    # Verify Parquet contents

    df = pd.read_parquet(parquet_path)
    for _col in df.columns:
        pass

    # ========================================================================
    # TEST 5: Statistics & Monitoring
    # ========================================================================

    stats_data = storage.get_stats()

    for _model in stats_data["models"]:
        pass

    # ========================================================================
    # SUMMARY
    # ========================================================================


if __name__ == "__main__":
    asyncio.run(test_all_improvements())
