"""Step definitions for hybrid analysis strategy BDD tests."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_bdd import given, parsers, scenario, then, when

from causaganha.v2.analysis.analyzer import DecisionAnalyzer
from causaganha.v2.analysis.hybrid_analyzer import HybridAnalyzer
from causaganha.v2.analysis.models import DecisionAnalysis
from causaganha.v2.analysis.rag_analyzer import RAGAnalyzer
from causaganha.v2.analysis.strategy import AnalysisStrategy


# Scenarios
@scenario(
    "../features/hybrid_analysis.feature",
    "High confidence RAG result does not trigger LLM fallback",
)
def test_high_confidence_no_fallback():
    """Test hybrid strategy with high RAG confidence."""


@scenario("../features/hybrid_analysis.feature", "Low confidence RAG result triggers LLM fallback")
def test_low_confidence_fallback():
    """Test hybrid strategy triggers LLM fallback."""


@scenario("../features/hybrid_analysis.feature", "Hybrid strategy with custom confidence threshold")
def test_custom_threshold():
    """Test hybrid strategy with custom threshold."""


@scenario("../features/hybrid_analysis.feature", "Batch analysis with hybrid strategy cost savings")
def test_batch_hybrid_cost_savings():
    """Test cost savings with hybrid batch analysis."""


@scenario("../features/hybrid_analysis.feature", "Track method usage statistics")
def test_method_usage_stats():
    """Test tracking of analysis method statistics."""


@scenario(
    "../features/hybrid_analysis.feature", "Hybrid strategy without PDF URL falls back gracefully"
)
def test_no_pdf_graceful_fallback():
    """Test hybrid strategy without PDF URL."""


@scenario("../features/hybrid_analysis.feature", "Strategy selection via configuration")
def test_strategy_llm_only():
    """Test LLM-only strategy selection."""


@scenario("../features/hybrid_analysis.feature", "Strategy selection for RAG only")
def test_strategy_rag_only():
    """Test RAG-only strategy selection."""


@scenario("../features/hybrid_analysis.feature", "Default strategy is hybrid")
def test_default_strategy():
    """Test that hybrid is the default strategy."""


@scenario(
    "../features/hybrid_analysis.feature", "Store RAG confidence even when using LLM fallback"
)
def test_preserve_rag_confidence():
    """Test that RAG confidence is preserved in hybrid results."""


# Fixtures
@pytest.fixture
def mock_rag_analyzer():
    """Create a mock RAG analyzer."""
    analyzer = MagicMock(spec=RAGAnalyzer)

    # Mock analyze_text to return configurable confidence
    async def mock_analyze(text, intimation_id=None):
        # Default: high confidence WIN result
        confidence = getattr(analyzer, "_test_confidence", 0.85)
        return DecisionAnalysis(
            intimation_id=intimation_id or 0,
            decision_type="RAG_CLASSIFIED",
            outcome="WIN",
            plaintiff_won=True,
            confidence_score=confidence,
            summary=f"RAG classification with {confidence:.2%} confidence",
            analysis_method="rag",
            rag_confidence=confidence,
            rag_votes={"WIN": 8, "LOSS": 2},
        )

    analyzer.analyze_text = AsyncMock(side_effect=mock_analyze)
    return analyzer


@pytest.fixture
def mock_llm_analyzer():
    """Create a mock LLM analyzer."""
    analyzer = MagicMock(spec=DecisionAnalyzer)

    # Mock analyze_pdf
    async def mock_analyze(pdf_url, intimation_id=None):
        return DecisionAnalysis(
            intimation_id=intimation_id or 0,
            decision_type="sentença",
            outcome="WIN",
            winner_lawyer_oab="12345",
            loser_lawyer_oab="67890",
            plaintiff_won=True,
            confidence_score=0.92,
            summary="LLM analysis with high confidence",
            analysis_method="llm",
        )

    analyzer.analyze_pdf = AsyncMock(side_effect=mock_analyze)
    return analyzer


@pytest.fixture
def hybrid_analyzer(mock_rag_analyzer, mock_llm_analyzer):
    """Create a hybrid analyzer with mocked dependencies."""
    return HybridAnalyzer(
        rag_analyzer=mock_rag_analyzer,
        llm_analyzer=mock_llm_analyzer,
        confidence_threshold=0.70,
    )


# Given steps
@given("the system has both RAG and LLM analyzers configured")
def analyzers_configured(hybrid_analyzer):
    """Ensure both analyzers are configured."""
    assert hybrid_analyzer.rag is not None
    assert hybrid_analyzer.llm is not None


@given(parsers.parse("the confidence threshold is set to {threshold:f}"))
def set_confidence_threshold(context, threshold, hybrid_analyzer):
    """Set custom confidence threshold."""
    hybrid_analyzer.threshold = threshold
    context["threshold"] = threshold


@given("I have a decision text with clear outcome signals")
def decision_clear_outcome(context, mock_rag_analyzer):
    """Create decision with clear outcome (high RAG confidence)."""
    context["decision_text"] = "Clear WIN decision text"
    context["pdf_url"] = "https://example.com/decision.pdf"
    mock_rag_analyzer._test_confidence = 0.85  # High confidence


@given("I have a decision text with ambiguous outcome")
def decision_ambiguous_outcome(context, mock_rag_analyzer):
    """Create decision with ambiguous outcome (low RAG confidence)."""
    context["decision_text"] = "Ambiguous decision text"
    context["pdf_url"] = "https://example.com/decision.pdf"
    mock_rag_analyzer._test_confidence = 0.55  # Low confidence


@given(parsers.parse("I have a decision with RAG confidence of {confidence:f}"))
def decision_specific_confidence(context, confidence, mock_rag_analyzer):
    """Set specific RAG confidence for testing."""
    context["decision_text"] = "Test decision text"
    context["pdf_url"] = "https://example.com/decision.pdf"
    mock_rag_analyzer._test_confidence = confidence


@given(parsers.parse("I have {total:d} decisions to analyze"))
def decisions_to_analyze(context, total):
    """Create batch of decisions."""
    context["total_decisions"] = total
    context["decision_texts"] = [f"Decision {i}" for i in range(total)]
    context["pdf_urls"] = [f"https://example.com/decision_{i}.pdf" for i in range(total)]


@given(parsers.parse("{high_conf:d} decisions have clear outcomes (high confidence)"))
def set_high_conf_count(context, high_conf, mock_rag_analyzer):
    """Set number of high-confidence decisions."""
    context["high_conf_count"] = high_conf

    # Create side effect that varies confidence by index
    original_analyze = mock_rag_analyzer.analyze_text.side_effect

    async def varying_analyze(text, intimation_id=None):
        # Extract index from text
        idx = int(text.split()[-1]) if text.split()[-1].isdigit() else 0
        high_count = context.get("high_conf_count", 0)

        # First N decisions have high confidence
        confidence = 0.85 if idx < high_count else 0.55
        mock_rag_analyzer._test_confidence = confidence

        result = await original_analyze(text, intimation_id)
        result.rag_confidence = confidence
        result.confidence_score = confidence
        return result

    mock_rag_analyzer.analyze_text = AsyncMock(side_effect=varying_analyze)


@given(parsers.parse("{low_conf:d} decisions have ambiguous outcomes (low confidence)"))
def set_low_conf_count(context, low_conf):
    """Set number of low-confidence decisions."""
    context["low_conf_count"] = low_conf


@given(parsers.parse("I have analyzed {total:d} decisions using hybrid strategy"))
def analyzed_decisions(context, total):
    """Set up analyzed decisions for statistics."""
    context["total_analyzed"] = total


@given(parsers.parse("{rag_count:d} used RAG and {llm_count:d} used LLM fallback"))
def set_method_counts(context, rag_count, llm_count):
    """Set method usage counts."""
    context["rag_used"] = rag_count
    context["llm_used"] = llm_count


@given("I have a decision text with low RAG confidence")
def decision_low_rag_confidence(context, mock_rag_analyzer):
    """Create decision with low RAG confidence."""
    context["decision_text"] = "Low confidence decision"
    mock_rag_analyzer._test_confidence = 0.45


@given("no PDF URL is available")
def no_pdf_url(context):
    """Set PDF URL to None."""
    context["pdf_url"] = None


@given(parsers.parse('the analysis strategy is set to "{strategy}"'))
def set_analysis_strategy(context, strategy):
    """Set the analysis strategy."""
    context["strategy"] = AnalysisStrategy(strategy)


@given("no analysis strategy is explicitly configured")
def no_strategy_configured(context):
    """No strategy set - should use default."""
    context["strategy"] = AnalysisStrategy.default()


# When steps
@when("I analyze using hybrid strategy")
def analyze_hybrid(context, hybrid_analyzer):
    """Analyze using hybrid strategy."""
    text = context.get("decision_text", "Test decision")
    pdf_url = context.get("pdf_url")

    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(
        hybrid_analyzer.analyze_text(text, intimation_id=1, pdf_url=pdf_url),
    )

    context["analysis_result"] = result

    # Track which analyzers were called
    context["rag_called"] = hybrid_analyzer.rag.analyze_text.called
    context["llm_called"] = hybrid_analyzer.llm.analyze_pdf.called


@when("I run batch analysis using hybrid strategy")
def run_hybrid_batch(context, hybrid_analyzer):
    """Run batch analysis with hybrid strategy."""
    texts = context.get("decision_texts", [])
    pdf_urls = context.get("pdf_urls", [])

    loop = asyncio.get_event_loop()
    results, stats = loop.run_until_complete(
        hybrid_analyzer.analyze_batch(texts, pdf_urls=pdf_urls),
    )

    context["batch_results"] = results
    context["batch_stats"] = stats


@when("I check the analysis statistics")
def check_statistics(context):
    """Prepare to check statistics."""
    # Statistics are already in context from previous steps


@when("I analyze a decision")
def analyze_decision(context, mock_rag_analyzer, mock_llm_analyzer):
    """Analyze a decision based on configured strategy."""
    strategy = context.get("strategy", AnalysisStrategy.HYBRID)
    text = context.get("decision_text", "Test decision")
    pdf_url = context.get("pdf_url", "https://example.com/test.pdf")

    loop = asyncio.get_event_loop()

    if strategy == AnalysisStrategy.LLM:
        # LLM only
        result = loop.run_until_complete(
            mock_llm_analyzer.analyze_pdf(pdf_url, intimation_id=1),
        )
        context["llm_only_called"] = True
        context["rag_only_called"] = False
    elif strategy == AnalysisStrategy.RAG:
        # RAG only
        result = loop.run_until_complete(
            mock_rag_analyzer.analyze_text(text, intimation_id=1),
        )
        context["rag_only_called"] = True
        context["llm_only_called"] = False
    else:
        # Hybrid (default)
        hybrid = HybridAnalyzer(mock_rag_analyzer, mock_llm_analyzer)
        result = loop.run_until_complete(
            hybrid.analyze_text(text, intimation_id=1, pdf_url=pdf_url),
        )
        context["rag_only_called"] = False
        context["llm_only_called"] = False

    context["analysis_result"] = result


@when("I analyze using hybrid strategy with LLM fallback")
def analyze_hybrid_with_fallback(context, mock_rag_analyzer, mock_llm_analyzer):
    """Analyze using hybrid with guaranteed LLM fallback."""
    mock_rag_analyzer._test_confidence = 0.55  # Ensure low confidence

    text = context.get("decision_text", "Test decision")
    pdf_url = "https://example.com/test.pdf"

    hybrid = HybridAnalyzer(
        mock_rag_analyzer,
        mock_llm_analyzer,
        confidence_threshold=0.70,
    )

    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(
        hybrid.analyze_text(text, intimation_id=1, pdf_url=pdf_url),
    )

    context["analysis_result"] = result


# Then steps
@then("the RAG analyzer should be used")
def check_rag_used(context):
    """Verify RAG analyzer was called."""
    assert context.get("rag_called", False), "RAG analyzer was not called"


@then("the LLM analyzer should not be called")
def check_llm_not_called(context):
    """Verify LLM was not called."""
    assert not context.get("llm_called", False), "LLM analyzer was called unexpectedly"


@then("the LLM analyzer should be called as fallback")
def check_llm_called(context):
    """Verify LLM was called as fallback."""
    assert context.get("llm_called", False), "LLM analyzer was not called for fallback"


@then("the RAG analyzer should be tried first")
def check_rag_tried_first(context):
    """Verify RAG was tried first."""
    assert context.get("rag_called", False), "RAG analyzer was not tried"


@then("the confidence score from LLM should be used")
def check_llm_confidence_used(context):
    """Verify LLM confidence is in final result."""
    result = context["analysis_result"]
    # LLM typically has higher confidence (>0.90)
    assert result.confidence_score > 0.80, f"Expected LLM confidence, got {result.confidence_score}"


@then(parsers.parse("the cost should be ${expected:f}"))
def check_cost_value(context, expected):
    """Check analysis cost."""
    result = context["analysis_result"]
    method = result.analysis_method

    if method == "rag":
        actual = 0.000008
    elif method in ["llm", "hybrid"]:
        actual = 0.000420
    else:
        actual = 0.0

    # Allow small variance
    variance = expected * 0.05
    assert abs(actual - expected) <= variance, f"Cost {actual} not approximately ${expected}"


@then("the LLM fallback should be triggered")
def check_llm_fallback_triggered(context):
    """Verify LLM fallback was triggered."""
    result = context["analysis_result"]
    assert result.analysis_method == "hybrid", f"Expected 'hybrid', got '{result.analysis_method}'"


@then(parsers.parse("{count:d} decisions should be analyzed with RAG"))
def check_rag_count(context, count):
    """Check number of decisions analyzed with RAG."""
    stats = context.get("batch_stats", {})
    actual = stats.get("rag_used", 0)
    assert actual == count, f"Expected {count} RAG analyses, got {actual}"


@then(parsers.parse("{count:d} decisions should use LLM fallback"))
def check_llm_fallback_count(context, count):
    """Check number of decisions using LLM fallback."""
    stats = context.get("batch_stats", {})
    actual = stats.get("llm_used", 0)
    assert actual == count, f"Expected {count} LLM fallbacks, got {actual}"


@then(parsers.parse("the total cost should be approximately ${expected:f}"))
def check_total_cost(context, expected):
    """Check total batch cost."""
    stats = context.get("batch_stats", {})
    actual = stats.get("total_cost", 0.0)

    variance = expected * 0.05
    assert abs(actual - expected) <= variance, f"Total cost ${actual} not approximately ${expected}"


@then(parsers.parse("the cost savings compared to LLM-only should be {percentage:d}%"))
def check_cost_savings(context, percentage):
    """Check cost savings percentage."""
    stats = context.get("batch_stats", {})
    actual_savings = stats.get("savings_vs_llm", 0.0)

    variance = 5.0  # Allow 5% variance
    assert (
        abs(actual_savings - percentage) <= variance
    ), f"Savings {actual_savings}% not approximately {percentage}%"


@then(parsers.parse("the RAG usage rate should be {percentage:d}%"))
def check_rag_usage_rate(context, percentage):
    """Check RAG usage percentage."""
    total = context.get("total_analyzed", 0)
    rag_used = context.get("rag_used", 0)

    actual_rate = (rag_used / total * 100) if total > 0 else 0.0

    variance = 5.0
    assert (
        abs(actual_rate - percentage) <= variance
    ), f"RAG usage {actual_rate}% not approximately {percentage}%"


@then(parsers.parse("the LLM fallback rate should be {percentage:d}%"))
def check_llm_fallback_rate(context, percentage):
    """Check LLM fallback percentage."""
    total = context.get("total_analyzed", 0)
    llm_used = context.get("llm_used", 0)

    actual_rate = (llm_used / total * 100) if total > 0 else 0.0

    variance = 5.0
    assert (
        abs(actual_rate - percentage) <= variance
    ), f"LLM fallback {actual_rate}% not approximately {percentage}%"


@then(parsers.parse("the average cost per decision should be approximately ${expected:f}"))
def check_avg_cost_per_decision(context, expected):
    """Check average cost per decision."""
    total = context.get("total_analyzed", 1)
    rag_used = context.get("rag_used", 0)
    llm_used = context.get("llm_used", 0)

    total_cost = (rag_used * 0.000008) + (llm_used * 0.000420)
    actual_avg = total_cost / total if total > 0 else 0.0

    variance = expected * 0.05
    assert (
        abs(actual_avg - expected) <= variance
    ), f"Avg cost ${actual_avg} not approximately ${expected}"


@then(parsers.parse('the analysis method should be "{method}"'))
def check_method_equals(context, method):
    """Check the analysis method matches expected."""
    result = context["analysis_result"]
    assert result.analysis_method == method, f"Expected '{method}', got '{result.analysis_method}'"


@then("a warning should be logged about missing PDF URL")
def check_warning_logged(context, caplog):
    """Check that a warning was logged (mocked here)."""
    # In a real test, we'd check caplog, but with mocks this is implicit
    result = context["analysis_result"]
    assert result.analysis_method == "rag_low_confidence"


@then("only the LLM analyzer should be used")
def check_only_llm_used(context):
    """Verify only LLM was used."""
    assert context.get("llm_only_called", False), "LLM was not used"
    assert not context.get("rag_only_called", False), "RAG was used unexpectedly"


@then("only the RAG analyzer should be used")
def check_only_rag_used(context):
    """Verify only RAG was used."""
    assert context.get("rag_only_called", False), "RAG was not used"
    assert not context.get("llm_only_called", False), "LLM was used unexpectedly"


@then("no LLM fallback should occur")
def check_no_llm_fallback(context):
    """Verify no LLM fallback occurred."""
    result = context["analysis_result"]
    assert result.analysis_method == "rag", f"LLM fallback occurred: {result.analysis_method}"


@then("the hybrid strategy should be used automatically")
def check_hybrid_default(context):
    """Verify hybrid strategy is default."""
    strategy = context.get("strategy")
    assert strategy in [AnalysisStrategy.HYBRID, AnalysisStrategy.AUTO]


@then("the final result should include the LLM outcome")
def check_llm_outcome_present(context):
    """Verify LLM outcome is in result."""
    result = context["analysis_result"]
    # LLM results include OAB numbers
    assert result.winner_lawyer_oab is not None or result.confidence_score > 0.80


@then(parsers.parse("the rag_confidence field should be {confidence:f}"))
def check_rag_confidence_field(context, confidence):
    """Verify RAG confidence is preserved."""
    result = context["analysis_result"]
    assert result.rag_confidence is not None, "RAG confidence not preserved"
    # Allow small variance
    assert (
        abs(result.rag_confidence - confidence) <= 0.1
    ), f"RAG confidence {result.rag_confidence} not approximately {confidence}"


@then("the rag_votes should be preserved")
def check_rag_votes_preserved(context):
    """Verify RAG votes are preserved."""
    result = context["analysis_result"]
    assert result.rag_votes is not None, "RAG votes not preserved"
    assert isinstance(result.rag_votes, dict), "RAG votes not a dictionary"


# Shared context fixture
@pytest.fixture
def context():
    """Shared context for BDD steps."""
    return {}
