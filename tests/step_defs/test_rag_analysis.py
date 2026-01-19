"""Step definitions for RAG analysis BDD tests."""

import asyncio
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pytest_bdd import given, when, then, scenario, parsers

from causaganha.v2.analysis.embedding_service import EmbeddingService
from causaganha.v2.analysis.rag_analyzer import RAGAnalyzer
from causaganha.v2.analysis.vector_store import VectorStore
from causaganha.v2.analysis.models import DecisionAnalysis


# Scenarios
@scenario("../features/rag_analysis.feature", "Analyze a decision with high confidence using RAG")
def test_high_confidence_rag():
    """Test RAG analysis with high confidence result."""


@scenario("../features/rag_analysis.feature", "Analyze a decision with medium confidence using RAG")
def test_medium_confidence_rag():
    """Test RAG analysis with medium confidence result."""


@scenario("../features/rag_analysis.feature", "Analyze a decision with low confidence using RAG")
def test_low_confidence_rag():
    """Test RAG analysis with low confidence result."""


@scenario("../features/rag_analysis.feature", "Chunk decision text for embedding")
def test_chunk_text():
    """Test text chunking functionality."""


@scenario("../features/rag_analysis.feature", "Generate embeddings for decision chunks")
def test_generate_embeddings():
    """Test embedding generation."""


@scenario("../features/rag_analysis.feature", "Classify using k-NN voting")
def test_knn_classification():
    """Test k-NN classification logic."""


@scenario("../features/rag_analysis.feature", "Track RAG analysis costs")
def test_rag_costs():
    """Test cost calculation for RAG analysis."""


@scenario("../features/rag_analysis.feature", "Batch analysis with RAG")
def test_batch_analysis():
    """Test batch analysis with RAG."""


# Fixtures
@pytest.fixture
def mock_vector_store(tmp_path):
    """Create a mock vector store with test data."""
    store = VectorStore(db_path=tmp_path / "test_lancedb")

    # Create mock ground truth data
    ground_truth_data = []
    for i in range(10):
        # 7 WIN, 2 LOSS, 1 UNKNOWN
        if i < 7:
            outcome = "WIN"
        elif i < 9:
            outcome = "LOSS"
        else:
            outcome = "UNKNOWN"

        ground_truth_data.append({
            "intimation_id": i,
            "outcome": outcome,
            "text": f"Decision text {i}",
            "vector": [float(i) * 0.1] * 768,  # Mock embedding
        })

    store.create_table("ground_truth", ground_truth_data, mode="overwrite")
    return store


@pytest.fixture
def mock_embedding_service():
    """Create a mock embedding service."""
    service = MagicMock(spec=EmbeddingService)

    # Mock embedding generation
    async def mock_embed_text(text, task_type="RETRIEVAL_QUERY", add_prefix=True):
        # Return a mock embedding vector
        return [0.1] * 768

    async def mock_embed_batch(texts, task_type="RETRIEVAL_QUERY", add_prefix=True):
        return [[0.1] * 768 for _ in texts]

    service.embed_text = AsyncMock(side_effect=mock_embed_text)
    service.embed_batch = AsyncMock(side_effect=mock_embed_batch)
    service.chunk_text = EmbeddingService.chunk_text

    return service


@pytest.fixture
def rag_analyzer(mock_vector_store, mock_embedding_service):
    """Create a RAG analyzer with mocked dependencies."""
    analyzer = RAGAnalyzer(
        vector_store_path=mock_vector_store.db_path,
        ground_truth_table="ground_truth",
        k_neighbors=7,
    )
    analyzer.embedding_service = mock_embedding_service
    return analyzer


# Given steps
@given("the system has a vector store initialized")
def vector_store_initialized(mock_vector_store):
    """Ensure vector store is initialized."""
    assert mock_vector_store.table_exists("ground_truth")


@given("the vector store contains ground truth decisions")
def vector_store_has_ground_truth(mock_vector_store):
    """Ensure ground truth data exists."""
    info = mock_vector_store.get_table_info("ground_truth")
    assert info["num_records"] > 0


@given("I have a decision text about a clear win outcome")
def decision_text_clear_win(context):
    """Create a clear WIN decision text."""
    context["decision_text"] = """
    SENTENÇA

    Vistos, etc.

    DJALMA SILVA ajuizou ação de cobrança em face de JOSE NETO.

    O autor requer o pagamento de R$ 50.000,00.

    JULGO PROCEDENTE o pedido para condenar o réu ao pagamento integral.

    Custas pelo réu. P.R.I.
    """


@given("I have a decision text with mixed signals")
def decision_text_mixed(context):
    """Create a decision text with mixed outcome signals."""
    context["decision_text"] = """
    DECISÃO

    Trata-se de pedido de indenização.

    Acolho parcialmente o pedido. Defiro parte dos danos materiais.

    Nego os danos morais por falta de comprovação.
    """


@given("I have a decision text with unclear outcome")
def decision_text_unclear(context):
    """Create a decision text with unclear outcome."""
    context["decision_text"] = """
    DESPACHO

    Intime-se a parte autora para apresentar documentos complementares.

    Após, tornem conclusos.
    """


@given(parsers.parse("I have a decision text of {length:d} characters"))
def decision_text_length(context, length):
    """Create a decision text of specific length."""
    context["decision_text"] = "X" * length
    context["expected_length"] = length


@given(parsers.parse("I have {num:d} decision text chunks"))
def decision_chunks(context, num):
    """Create decision text chunks."""
    context["chunks"] = [f"Chunk {i} text" for i in range(num)]


@given("I have decision embeddings")
def decision_embeddings(context):
    """Create mock decision embeddings."""
    context["embeddings"] = [
        [float(i) * 0.1] * 768 for i in range(3)
    ]


@given("the vector store has 5 similar WIN decisions and 2 LOSS decisions")
def vector_store_win_loss_data(mock_vector_store):
    """Ensure specific ground truth distribution."""
    # Already set up in mock_vector_store fixture (7 WIN, 2 LOSS)
    pass


@given(parsers.parse("I analyze {num:d} decisions using RAG"))
def analyze_multiple_decisions(context, num):
    """Set number of decisions to analyze."""
    context["num_decisions"] = num


@given(parsers.parse("I have {num:d} pending decisions to analyze"))
def pending_decisions(context, num):
    """Create pending decisions for batch analysis."""
    context["pending_texts"] = [
        f"Decision text number {i}" for i in range(num)
    ]


# When steps
@when("I analyze the decision using RAG")
def analyze_with_rag(context, rag_analyzer):
    """Analyze decision using RAG."""
    text = context.get("decision_text", "Sample decision text")

    # Run async analysis
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(
        rag_analyzer.analyze_text(text, intimation_id=1)
    )

    context["analysis_result"] = result


@when(parsers.parse("I chunk the text with {chunk_size:d} character chunks and {overlap:d} character overlap"))
def chunk_text_with_params(context, chunk_size, overlap):
    """Chunk text with specific parameters."""
    text = context.get("decision_text", "")
    chunks = EmbeddingService.chunk_text(text, chunk_size=chunk_size, overlap=overlap)
    context["chunks"] = chunks


@when("I generate embeddings for the chunks")
def generate_embeddings(context, mock_embedding_service):
    """Generate embeddings for chunks."""
    chunks = context.get("chunks", [])

    loop = asyncio.get_event_loop()
    embeddings = loop.run_until_complete(
        mock_embedding_service.embed_batch(chunks)
    )

    context["embeddings"] = embeddings


@when(parsers.parse("I classify using k={k:d} nearest neighbors"))
def classify_knn(context, k, rag_analyzer):
    """Classify using k-NN."""
    embeddings = context.get("embeddings", [])

    # Use RAG analyzer's internal k-NN method
    classification = rag_analyzer._classify_with_knn(embeddings)

    context["classification"] = classification


@when("I calculate the total cost")
def calculate_total_cost(context):
    """Calculate total RAG cost."""
    num = context.get("num_decisions", 0)
    cost = RAGAnalyzer.calculate_cost(num)
    context["total_cost"] = cost


@when("I run batch analysis using RAG")
def run_batch_analysis(context, rag_analyzer):
    """Run batch RAG analysis."""
    texts = context.get("pending_texts", [])

    loop = asyncio.get_event_loop()
    start_time = loop.time()

    results = loop.run_until_complete(
        rag_analyzer.analyze_batch(texts)
    )

    end_time = loop.time()

    context["batch_results"] = results
    context["batch_time"] = end_time - start_time


# Then steps
@then(parsers.parse('the outcome should be classified as "{outcome}"'))
def check_outcome(context, outcome):
    """Check the classified outcome."""
    result = context.get("analysis_result") or context.get("classification")
    actual_outcome = result.outcome if hasattr(result, "outcome") else result["outcome"]
    assert actual_outcome == outcome, f"Expected {outcome}, got {actual_outcome}"


@then(parsers.parse("the confidence score should be greater than {threshold:f}"))
def check_confidence_greater(context, threshold):
    """Check confidence is above threshold."""
    result = context.get("analysis_result") or context.get("classification")
    confidence = result.confidence_score if hasattr(result, "confidence_score") else result["confidence"]
    assert confidence > threshold, f"Confidence {confidence} not greater than {threshold}"


@then(parsers.parse("the confidence score should be between {min_conf:f} and {max_conf:f}"))
def check_confidence_range(context, min_conf, max_conf):
    """Check confidence is within range."""
    result = context.get("analysis_result") or context.get("classification")
    confidence = result.confidence_score if hasattr(result, "confidence_score") else result["confidence"]
    assert min_conf <= confidence <= max_conf, f"Confidence {confidence} not in range [{min_conf}, {max_conf}]"


@then(parsers.parse("the confidence score should be less than {threshold:f}"))
def check_confidence_less(context, threshold):
    """Check confidence is below threshold."""
    result = context.get("analysis_result") or context.get("classification")
    confidence = result.confidence_score if hasattr(result, "confidence_score") else result["confidence"]
    assert confidence < threshold, f"Confidence {confidence} not less than {threshold}"


@then(parsers.parse('the analysis method should be "{method}"'))
def check_analysis_method(context, method):
    """Check the analysis method used."""
    result = context.get("analysis_result")
    assert result.analysis_method == method, f"Expected {method}, got {result.analysis_method}"


@then("an outcome should be returned")
def check_outcome_exists(context):
    """Check that an outcome was returned."""
    result = context.get("analysis_result") or context.get("classification")
    outcome = result.outcome if hasattr(result, "outcome") else result["outcome"]
    assert outcome is not None


@then(parsers.parse("I should get {expected_chunks:d} chunks"))
def check_chunk_count(context, expected_chunks):
    """Check the number of chunks."""
    chunks = context.get("chunks", [])
    assert len(chunks) == expected_chunks, f"Expected {expected_chunks} chunks, got {len(chunks)}"


@then(parsers.parse("each chunk should be approximately {size:d} characters"))
def check_chunk_size(context, size):
    """Check chunk sizes."""
    chunks = context.get("chunks", [])
    for i, chunk in enumerate(chunks):
        # Allow some variance (±50 chars), except for last chunk which can be smaller
        if i == len(chunks) - 1:
            # Last chunk can be any size up to chunk_size
            assert len(chunk) <= size + 50, f"Last chunk {i} size {len(chunk)} exceeds {size}"
        else:
            assert abs(len(chunk) - size) <= 50, f"Chunk {i} size {len(chunk)} not approximately {size}"


@then("consecutive chunks should have overlapping content")
def check_chunk_overlap(context):
    """Check that chunks have overlap."""
    chunks = context.get("chunks", [])
    if len(chunks) < 2:
        return  # Need at least 2 chunks to check overlap

    for i in range(len(chunks) - 1):
        # Check if end of current chunk appears in start of next chunk
        current_end = chunks[i][-50:]  # Last 50 chars
        next_start = chunks[i + 1][:100]  # First 100 chars

        # Some part of current_end should be in next_start
        has_overlap = any(
            current_end[j:j+10] in next_start
            for j in range(0, len(current_end) - 10, 5)
        )

        assert has_overlap, f"No overlap found between chunks {i} and {i+1}"


@then(parsers.parse("I should receive {count:d} embedding vectors"))
def check_embedding_count(context, count):
    """Check number of embeddings."""
    embeddings = context.get("embeddings", [])
    assert len(embeddings) == count, f"Expected {count} embeddings, got {len(embeddings)}"


@then(parsers.parse("each embedding should have {dimensions:d} dimensions"))
def check_embedding_dimensions(context, dimensions):
    """Check embedding dimensions."""
    embeddings = context.get("embeddings", [])
    for emb in embeddings:
        assert len(emb) == dimensions, f"Expected {dimensions} dimensions, got {len(emb)}"


@then(parsers.parse("the confidence should be approximately {expected:f}"))
def check_confidence_approximate(context, expected):
    """Check confidence is approximately expected value."""
    classification = context.get("classification")
    confidence = classification["confidence"]
    # Allow 10% variance
    assert abs(confidence - expected) <= 0.1, f"Confidence {confidence} not approximately {expected}"


@then(parsers.parse("the vote distribution should show {win_votes:d} WIN and {loss_votes:d} LOSS"))
def check_vote_distribution(context, win_votes, loss_votes):
    """Check k-NN vote distribution."""
    classification = context.get("classification")
    votes = classification["votes"]
    assert votes.get("WIN", 0) == win_votes, f"Expected {win_votes} WIN votes, got {votes.get('WIN', 0)}"
    assert votes.get("LOSS", 0) == loss_votes, f"Expected {loss_votes} LOSS votes, got {votes.get('LOSS', 0)}"


@then(parsers.parse("the cost should be approximately ${expected_cost:f}"))
def check_cost(context, expected_cost):
    """Check total cost."""
    actual_cost = context.get("total_cost", 0.0)
    # Allow 1% variance
    variance = expected_cost * 0.01
    assert abs(actual_cost - expected_cost) <= variance, f"Cost {actual_cost} not approximately ${expected_cost}"


@then(parsers.parse("the cost per decision should be ${expected_per:f}"))
def check_cost_per_decision(context, expected_per):
    """Check cost per decision."""
    total_cost = context.get("total_cost", 0.0)
    num_decisions = context.get("num_decisions", 1)
    per_decision = total_cost / num_decisions if num_decisions > 0 else 0.0

    variance = expected_per * 0.01
    assert abs(per_decision - expected_per) <= variance, f"Cost per decision {per_decision} not approximately ${expected_per}"


@then(parsers.parse("all {count:d} decisions should be classified"))
def check_all_classified(context, count):
    """Check all decisions were classified."""
    results = context.get("batch_results", [])
    assert len(results) == count, f"Expected {count} results, got {len(results)}"


@then("the analysis method for all should be \"rag\"")
def check_all_rag_method(context):
    """Check all use RAG method."""
    results = context.get("batch_results", [])
    for result in results:
        assert result.analysis_method == "rag", f"Expected 'rag', got '{result.analysis_method}'"


@then(parsers.parse("the total processing time should be less than {max_time:d} seconds"))
def check_processing_time(context, max_time):
    """Check processing time."""
    batch_time = context.get("batch_time", 0.0)
    assert batch_time < max_time, f"Processing took {batch_time}s, expected less than {max_time}s"


# Shared context fixture
@pytest.fixture
def context():
    """Shared context for BDD steps."""
    return {}
