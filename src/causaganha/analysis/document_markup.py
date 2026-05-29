"""Service for anonymizing and tagging personal identifiable information (PII) in legal documents.

Uses the 'openai/privacy-filter' token-classification model locally to detect
private entities (like names of parties) and wrap them with XML tags (e.g., <parte>...).
"""

import structlog
from transformers import pipeline

logger = structlog.get_logger()


class DocumentMarkupService:
    """Service to detect and wrap personal names (PII) in legal documents using XML tags."""

    def __init__(self, model_name: str = "openai/privacy-filter") -> None:
        logger.info("initializing_document_markup_service", model=model_name)
        # Load token classification pipeline locally
        self.classifier = pipeline(
            task="token-classification",
            model=model_name,
            aggregation_strategy="simple"
        )
        logger.info("document_markup_service_initialized", model=model_name)

    def tag_parties(self, text: str) -> str:
        """Identify names of private persons in text and wrap them with <parte>...</parte> XML tags.

        Args:
            text: Raw document text.

        Returns:
            Text with names of parties wrapped in XML tags.
        """
        if not text:
            return ""

        # Run token classification model
        results = self.classifier(text)

        # Filter only 'private_person' entities
        person_spans = []
        for entity in results:
            if entity.get("entity_group") == "private_person":
                start = entity.get("start")
                end = entity.get("end")
                word = text[start:end]
                person_spans.append((start, end, word))

        if not person_spans:
            return text

        # Sort spans by starting index in reverse order to modify text from back to front
        person_spans.sort(key=lambda x: x[0], reverse=True)

        # Apply XML tags
        tagged_text = text
        for start, end, word in person_spans:
            # Wrap in XML tag
            tagged_text = (
                tagged_text[:start]
                + f"<parte>{word}</parte>"
                + tagged_text[end:]
            )

        return tagged_text
