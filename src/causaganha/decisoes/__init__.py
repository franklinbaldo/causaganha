"""Public decision/content discovery for CausaGanha product surfaces."""

from causaganha.decisoes.planner import (
    DecisionSearchBudgetError,
    DecisionSearchPlan,
    plan_decision_search,
)
from causaganha.decisoes.published import (
    PublishedDecisionDataset,
    discover_published_decision_datasets,
    discover_published_juris_datasets,
)
from causaganha.decisoes.taxonomy import (
    DocumentTaxonomyRegistry,
    MacroCategory,
    TaxonomyClassification,
    TaxonomyRule,
)
from causaganha.decisoes.topology_router import (
    DecisionTopology,
    TopologyRouter,
)

__all__ = [
    "DecisionSearchBudgetError",
    "DecisionSearchPlan",
    "DecisionTopology",
    "DocumentTaxonomyRegistry",
    "MacroCategory",
    "PublishedDecisionDataset",
    "TaxonomyClassification",
    "TaxonomyRule",
    "TopologyRouter",
    "discover_published_decision_datasets",
    "discover_published_juris_datasets",
    "plan_decision_search",
    # Exportados com carregamento preguiçoso (lazy) para não exigir joblib/sklearn em tempo de importação:
    "DispositifResult",
    "DocumentStructure",
    "FullDocumentStructuralSegmenter",
    "HybridDispositifSegmenter",
    "ModelRatchetGate",
    "RatchetDecision",
    "RatchetMetrics",
    "SectionSpan",
    "SectionType",
]


def __getattr__(name: str):
    """Carregamento preguiçoso para componentes que dependem de scikit-learn / joblib."""
    if name in ("HybridDispositifSegmenter", "DispositifResult"):
        from causaganha.decisoes.hybrid_segmenter import DispositifResult, HybridDispositifSegmenter

        return {
            "HybridDispositifSegmenter": HybridDispositifSegmenter,
            "DispositifResult": DispositifResult,
        }[name]
    if name in ("ModelRatchetGate", "RatchetDecision", "RatchetMetrics"):
        from causaganha.decisoes.model_ratchet import (
            ModelRatchetGate,
            RatchetDecision,
            RatchetMetrics,
        )

        return {
            "ModelRatchetGate": ModelRatchetGate,
            "RatchetDecision": RatchetDecision,
            "RatchetMetrics": RatchetMetrics,
        }[name]
    if name in (
        "FullDocumentStructuralSegmenter",
        "DocumentStructure",
        "SectionSpan",
        "SectionType",
    ):
        from causaganha.decisoes.structural_segmenter import (
            DocumentStructure,
            FullDocumentStructuralSegmenter,
            SectionSpan,
            SectionType,
        )

        return {
            "FullDocumentStructuralSegmenter": FullDocumentStructuralSegmenter,
            "DocumentStructure": DocumentStructure,
            "SectionSpan": SectionSpan,
            "SectionType": SectionType,
        }[name]
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
