"""PII tagging service for legal documents.

Uses the 'openai/privacy-filter' token-classification model locally to detect
private person entities and wrap them with XML tags (<parte>...</parte>).
"""

from __future__ import annotations

import structlog
from transformers import pipeline


logger = structlog.get_logger()


class DocumentMarkupService:
    """Detect and tag private person names in legal documents with XML markers."""

    def __init__(self, model_name: str = "openai/privacy-filter") -> None:  # noqa: D107
        logger.info("initializing_document_markup_service", model=model_name)
        self.classifier = pipeline(
            task="token-classification",
            model=model_name,
            aggregation_strategy="simple",
        )
        logger.info("document_markup_service_initialized", model=model_name)

    def tag_parties(self, text: str) -> str:
        """Wrap private person names with <parte>...</parte> XML tags.

        Args:
            text: Raw document text.

        Returns:
            Text with identified private person names wrapped in XML tags.
        """
        if not text:
            return ""

        results = self.classifier(text)

        person_spans = [
            (e["start"], e["end"])
            for e in results
            if e.get("entity_group") == "private_person"
        ]

        if not person_spans:
            return text

        # Apply tags back-to-front to preserve offsets
        person_spans.sort(key=lambda x: x[0], reverse=True)
        tagged = text
        for start, end in person_spans:
            tagged = tagged[:start] + f"<parte>{tagged[start:end]}</parte>" + tagged[end:]

        return tagged
