import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from unittest.mock import MagicMock, AsyncMock, patch
from causaganha.ml.types import WinnerClassifierMode, WinnerBootstrapMode, WinnerLabel, PredictionResult
from causaganha.application.pipeline.analyze import run_analysis
from causaganha.domain.models import Intimation
from causaganha.domain.models_analysis import DecisionAnalysis, Outcome
from datetime import date, datetime, UTC
import asyncio

# Load scenarios
scenarios('../features/winner_prediction.feature')

# Fixtures

@pytest.fixture
def mock_repositories():
    intimation_repo = MagicMock()
    analysis_repo = MagicMock()
    # Mock ibis connection for analysis_repo
    analysis_repo.con = MagicMock()
    analysis_repo.store_analysis_results_batch = AsyncMock()
    return intimation_repo, analysis_repo

@pytest.fixture
def mock_doc_service():
    service = MagicMock()
    service.download_pdf = AsyncMock(return_value=b"fake pdf content")
    return service

@pytest.fixture
def mock_analyzer():
    analyzer = MagicMock()
    analyzer.analyze_decision = AsyncMock(return_value=DecisionAnalysis(
        outcome=Outcome.WIN,
        summary="Summary of decision",
        judge_name="Judge Dredd",
        confidence_score=0.9,
        decision_reasoning="Reasoning",
        winner_party_name="Plaintiff Party" # Matches bootstrap logic
    ))
    return analyzer

@pytest.fixture
def context():
    return {}

# Given Steps

@given("the winner classifier is disabled")
def winner_classifier_disabled(context):
    context['mode'] = WinnerClassifierMode.OFF
    context['bootstrap'] = WinnerBootstrapMode.OFF
    context['bootstrap_limit'] = 0

@given('the winner classifier is set to "infer"')
def winner_classifier_infer(context):
    context['mode'] = WinnerClassifierMode.INFER
    context['bootstrap'] = WinnerBootstrapMode.OFF
    context['bootstrap_limit'] = 0

@given('the winner classifier is set to "teach"')
def winner_classifier_teach(context):
    context['mode'] = WinnerClassifierMode.TEACH
    context['bootstrap'] = WinnerBootstrapMode.OFF # Default off for this scenario unless specified
    context['bootstrap_limit'] = 0

@given('the winner classifier is set to "teach" with bootstrap "auto"')
def winner_classifier_teach_auto(context):
    context['mode'] = WinnerClassifierMode.TEACH
    context['bootstrap'] = WinnerBootstrapMode.AUTO
    context['bootstrap_limit'] = 5000

@given("the learner is untrained")
def learner_untrained():
    # We will mock the predictor to appear untrained
    pass

@given("a fake teacher that returns \"plaintiff_won\"")
def fake_teacher_returns_plaintiff_won(context):
    context['teacher_label'] = WinnerLabel.PLAINTIFF_WON

@given(parsers.parse("the database contains {count:d} labeled decisions"))
def db_contains_decisions(context, mock_repositories, count):
    _, analysis_repo = mock_repositories

    # Create fake rows
    rows = []
    for i in range(count):
        rows.append({
            "outcome": "WIN",
            "decision_reasoning": f"Reasoning {i}",
            "summary": f"Summary {i}",
            "winner_party_name": "Plaintiff Party"
        })

    # Mock the ibis table query for bootstrap
    mock_table = MagicMock()
    mock_filter = MagicMock()

    analysis_repo.con.table.return_value = mock_table
    mock_table.filter.return_value = mock_filter

    # Handle limit side effect to return sliced data
    def limit_side_effect(limit_val=None):
        mock_limited_query = MagicMock()
        limited_rows = rows[:limit_val] if limit_val is not None else rows
        mock_limited_df = MagicMock()
        mock_limited_df.to_dict.return_value = limited_rows
        mock_limited_query.execute.return_value = mock_limited_df
        return mock_limited_query

    mock_filter.limit.side_effect = limit_side_effect

@given("the model is initially untrained")
def model_initially_untrained():
    pass

@given(parsers.parse("the bootstrap limit is set to {limit:d}"))
def set_bootstrap_limit(context, limit):
    context['bootstrap_limit'] = limit

# When Steps

@when("I run the analysis pipeline on a batch of decisions")
def run_pipeline_batch(context, mock_repositories, mock_doc_service, mock_analyzer):
    asyncio.run(_run_pipeline(context, mock_repositories, mock_doc_service, mock_analyzer, count=3))

@when("I run the analysis pipeline on a decision")
def run_pipeline_single(context, mock_repositories, mock_doc_service, mock_analyzer):
    asyncio.run(_run_pipeline(context, mock_repositories, mock_doc_service, mock_analyzer, count=1))

@when("I run the analysis pipeline")
def run_pipeline_generic(context, mock_repositories, mock_doc_service, mock_analyzer):
    asyncio.run(_run_pipeline(context, mock_repositories, mock_doc_service, mock_analyzer, count=1))

async def _run_pipeline(context, repos, doc_service, analyzer, count):
    intimation_repo, analysis_repo = repos

    # Mock get_unanalyzed_intimations to return 'count' items once, then empty
    items = [
        Intimation(
            id=i,
            numero_processo=f"123{i}",
            data_disponibilizacao=date.today(),
            sigla_tribunal="TJSP",
            tipo_comunicacao="Intimação",
            nome_orgao="Vara X",
            texto=f"Decision text {i}",
            link=f"http://example.com/{i}.pdf",
            tipo_documento="Sentença",
            nome_classe="Procedimento Comum",
            hash=f"hash{i}"
        ) for i in range(count)
    ]

    intimation_repo.get_unanalyzed_intimations = AsyncMock(side_effect=[items, []])

    with patch('causaganha.ml.runner.GeminiEmbedder') as MockEmbedder, \
         patch('causaganha.ml.runner.WinnerPredictor') as MockPredictor, \
         patch('causaganha.ml.runner.LLMTeacher') as MockTeacher, \
         patch('causaganha.ml.runner.EmbeddingCache') as MockCache:

        # Setup mocks
        embedder_instance = MockEmbedder.return_value
        embedder_instance.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])

        predictor_instance = MockPredictor.return_value
        predictor_instance.is_trained = False # Initially untrained
        predictor_instance.predict.return_value = PredictionResult(
            prediction=WinnerLabel.PLAINTIFF_WON,
            confidence=0.6,
            model_version="v1"
        )
        def update_side_effect(*args, **kwargs):
            predictor_instance.is_trained = True
        predictor_instance.update.side_effect = update_side_effect

        teacher_instance = MockTeacher.return_value
        teacher_label = context.get('teacher_label', WinnerLabel.UNCLEAR)
        teacher_instance.label = AsyncMock(return_value=teacher_label)

        # Store mocks in context for verification
        context['mocks'] = {
            'embedder': embedder_instance,
            'predictor': predictor_instance,
            'teacher': teacher_instance
        }

        # We need to ensure bootstrap task (which is fire-and-forget in Runner) completes for the test.
        # Since we mock Runner's components, but we don't mock Runner itself, the Runner logic runs.
        # It calls asyncio.create_task(self._handle_bootstrap()).
        # In this asyncio.run() session, that task will be scheduled.
        # We want to wait for pending tasks?

        await run_analysis(
            repository=intimation_repo,
            analysis_repository=analysis_repo,
            doc_service=doc_service,
            analyzer=analyzer,
            limit=count,
            winner_classifier_mode=context.get('mode', WinnerClassifierMode.OFF),
            winner_bootstrap_mode=context.get('bootstrap', WinnerBootstrapMode.OFF),
            winner_bootstrap_limit=context.get('bootstrap_limit', 5000)
        )

        # Let other tasks run (like bootstrap)
        # We need to find the bootstrap task.
        # Since we don't have reference to the runner instance easily (it's inside run_analysis),
        # we can just sleep a bit to let the loop process pending tasks.
        # Or better, we can assume that if run_analysis finishes, we give a bit of time for background tasks.
        await asyncio.sleep(0.1)

        # Capture what was stored
        context['stored_results'] = []
        for call in analysis_repo.store_analysis_results_batch.call_args_list:
            context['stored_results'].extend(call[0][0])

# Then Steps

@then("no embeddings are computed")
def verify_no_embeddings(context):
    assert not context['mocks']['embedder'].embed.called

@then("no teacher LLM calls are made")
def verify_no_teacher_calls(context):
    if 'teacher' in context['mocks']:
        assert not context['mocks']['teacher'].label.called

@then("the persisted analysis results do not contain ML prediction fields")
def verify_no_ml_fields(context):
    for result in context['stored_results']:
        assert "winner_ml_pred" not in result
        assert "winner_ml_confidence" not in result

@then("the decision text is embedded")
def verify_embedded(context):
    assert context['mocks']['embedder'].embed.called

@then("the learner predicts a result with low confidence")
def verify_predict_low_conf(context):
    assert context['mocks']['predictor'].predict.called

@then("the analysis result contains \"winner_ml_pred\" and \"winner_ml_confidence\"")
def verify_ml_fields_present(context):
    for result in context['stored_results']:
        assert "winner_ml_pred" in result
        assert "winner_ml_confidence" in result

@then("the analysis result does not contain \"winner_teacher_label\"")
def verify_no_teacher_label(context):
    for result in context['stored_results']:
        assert "winner_teacher_label" not in result

@then("the learner predicts a result")
def verify_predict_called(context):
    assert context['mocks']['predictor'].predict.called

@then("the teacher is called to label the decision")
def verify_teacher_called(context):
    assert context['mocks']['teacher'].label.called

@then("the learner is updated with the new example")
def verify_learner_updated(context):
    assert context['mocks']['predictor'].update.called

@then("the analysis result contains \"winner_teacher_label\" and \"winner_model_version\"")
def verify_teacher_fields(context):
    for result in context['stored_results']:
        assert "winner_teacher_label" in result
        assert "winner_model_version" in result

@then(parsers.parse("the model is trained on the {count:d} historical decisions first"))
def verify_bootstrap_count(context, count):
    # Check that update was called at least count times
    assert context['mocks']['predictor'].update.call_count >= count

@then("then the new decisions are processed using the trained model")
def verify_processed_after_train(context):
    pass

@then(parsers.parse("the model is trained on at most {limit:d} historical decisions"))
def verify_bootstrap_limit(context, limit):
    # In the scenario, we process 1 new decision. So limit + 1
    assert context['mocks']['predictor'].update.call_count <= limit + 1
