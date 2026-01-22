"""Embedding provider implementations (API services).

This module defines embedding providers (API services) separately from models (configurations).
Providers handle API authentication, requests, retries, and error handling.
Models define configuration like dimensions and token limits.
"""

import os
from abc import ABC, abstractmethod
from typing import Literal

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from causaganha.v2.analysis.embedding_models import EmbeddingModel, get_default_model


logger = structlog.get_logger()

# Task type mapping between providers
TaskType = Literal["RETRIEVAL_QUERY", "RETRIEVAL_DOCUMENT"]


class EmbeddingProviderBase(ABC):
    """Abstract base class for embedding providers (API services).

    Providers handle:
    - API authentication
    - HTTP requests
    - Retry logic
    - Error handling

    Models (EmbeddingModel) define:
    - Model name
    - Dimensions
    - Token limits
    """

    def __init__(
        self,
        api_key: str | None,
        api_key_env_var: str,
        base_url: str,
        provider_name: str,
    ) -> None:
        """Initialize the provider with API connection details.

        Args:
            api_key: API key. If None, reads from environment variable.
            api_key_env_var: Name of environment variable for API key.
            base_url: Base URL for the API.
            provider_name: Name of the provider for logging.

        Raises:
            ValueError: If API key is not provided and not in environment.
        """
        self.api_key = api_key or os.getenv(api_key_env_var)
        if not self.api_key:
            msg = f"{provider_name} API key must be provided or set in {api_key_env_var} env var"
            raise ValueError(
                msg,
            )

        self.base_url = base_url
        self.provider_name = provider_name

        logger.info(
            "%s_provider_initialized",
            provider_name.lower(),
            base_url=base_url,
        )

    @abstractmethod
    async def embed_text(
        self,
        text: str,
        model: EmbeddingModel,
        task_type: TaskType = "RETRIEVAL_QUERY",
    ) -> list[float]:
        """Generate embedding for a single text using the specified model.

        Args:
            text: Text to embed.
            model: EmbeddingModel configuration to use.
            task_type: Type of task (RETRIEVAL_QUERY or RETRIEVAL_DOCUMENT).

        Returns:
            Embedding vector.

        Raises:
            httpx.HTTPError: If the API request fails.
        """
        ...

    async def validate(self, model: EmbeddingModel) -> bool:
        """Validate provider by testing API authentication with a simple request.

        Args:
            model: EmbeddingModel to use for validation.

        Returns:
            True if authentication succeeds, False otherwise.
        """
        try:
            # Try to embed a very short test text
            await self.embed_text("test", model=model, task_type="RETRIEVAL_QUERY")
            logger.info(
                "%s_provider_validated",
                self.provider_name.lower(),
                status="success",
                model=model.name,
            )
            return True
        except Exception as e:
            logger.warning(
                "%s_provider_validation_failed",
                self.provider_name.lower(),
                error=str(e),
                error_type=type(e).__name__,
                model=model.name,
            )
            return False


class GoogleProvider(EmbeddingProviderBase):
    """Google AI embedding provider (API service).

    Supports models:
    - gemini-embedding-001 (768D-3072D, 2K tokens)
    - text-embedding-004 (deprecated)
    """

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize Google provider.

        Args:
            api_key: Google API key. If None, reads from GOOGLE_API_KEY env var.
        """
        super().__init__(
            api_key=api_key,
            api_key_env_var="GOOGLE_API_KEY",
            base_url="https://generativelanguage.googleapis.com/v1beta",
            provider_name="Google",
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def embed_text(
        self,
        text: str,
        model: EmbeddingModel,
        task_type: TaskType = "RETRIEVAL_QUERY",
    ) -> list[float]:
        """Generate embedding using Google's API.

        Args:
            text: Text to embed.
            model: EmbeddingModel configuration (must be a Google model).
            task_type: Type of task (RETRIEVAL_QUERY or RETRIEVAL_DOCUMENT).

        Returns:
            Embedding vector with dimensions specified by model.

        Raises:
            ValueError: If model is not a Google model.
            httpx.HTTPError: If the API request fails.
        """
        if model.provider != "google":
            msg = f"GoogleProvider requires a Google model, got {model.provider}/{model.name}"
            raise ValueError(
                msg,
            )

        url = f"{self.base_url}/models/{model.name}:embedContent"
        headers = {"Content-Type": "application/json"}
        params = {"key": self.api_key}

        payload = {
            "content": {"parts": [{"text": text}]},
            "taskType": task_type,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers,
                    params=params,
                )
                response.raise_for_status()

                data = response.json()
                embedding = data["embedding"]["values"]

                logger.debug(
                    "google_embedding_generated",
                    text_length=len(text),
                    embedding_dim=len(embedding),
                    model=model.name,
                    task_type=task_type,
                )

                return embedding

            except httpx.HTTPError as e:
                logger.exception(
                    "google_embedding_failed",
                    error=str(e),
                    text_length=len(text),
                    model=model.name,
                )
                raise


class JinaProvider(EmbeddingProviderBase):
    """Jina AI embedding provider (API service).

    Supports models:
    - jina-embeddings-v4 (256D-1024D, 32K tokens) - recommended
    - jina-embeddings-v3 (256D-1024D, 8K tokens)
    - jina-embeddings-v2 (768D, 8K tokens) - deprecated
    """

    # Task type mapping: our standard -> Jina's task format
    TASK_MAPPING = {
        "RETRIEVAL_QUERY": "retrieval.query",
        "RETRIEVAL_DOCUMENT": "retrieval.passage",
    }

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize Jina provider.

        Args:
            api_key: Jina API key. If None, reads from JINA_API_KEY env var.
        """
        super().__init__(
            api_key=api_key,
            api_key_env_var="JINA_API_KEY",
            base_url="https://api.jina.ai/v1",
            provider_name="Jina",
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def embed_text(
        self,
        text: str,
        model: EmbeddingModel,
        task_type: TaskType = "RETRIEVAL_QUERY",
    ) -> list[float]:
        """Generate embedding using Jina AI's API.

        Args:
            text: Text to embed.
            model: EmbeddingModel configuration (must be a Jina model).
            task_type: Type of task (RETRIEVAL_QUERY or RETRIEVAL_DOCUMENT).

        Returns:
            Embedding vector with dimensions specified by model.

        Raises:
            ValueError: If model is not a Jina model.
            httpx.HTTPError: If the API request fails.
        """
        if model.provider != "jina":
            msg = f"JinaProvider requires a Jina model, got {model.provider}/{model.name}"
            raise ValueError(
                msg,
            )

        url = f"{self.base_url}/embeddings"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        # Map our task type to Jina's format
        jina_task = self.TASK_MAPPING.get(task_type, "retrieval.query")

        payload = {
            "input": [text],  # Jina expects an array
            "model": model.name,
            "dimensions": model.dimension,
            "task": jina_task,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()

                data = response.json()
                # Jina returns OpenAI-compatible format with 'data' array
                embedding = data["data"][0]["embedding"]

                logger.debug(
                    "jina_embedding_generated",
                    text_length=len(text),
                    embedding_dim=len(embedding),
                    model=model.name,
                    task_type=task_type,
                    jina_task=jina_task,
                )

                return embedding

            except httpx.HTTPError as e:
                logger.exception(
                    "jina_embedding_failed",
                    error=str(e),
                    text_length=len(text),
                    model=model.name,
                    status_code=getattr(e.response, "status_code", None)
                    if hasattr(e, "response")
                    else None,
                )
                raise


def create_provider(provider: str, api_key: str | None = None) -> EmbeddingProviderBase:
    """Factory function to create an embedding provider.

    Args:
        provider: Provider name ('google' or 'jina').
        api_key: API key for the provider.

    Returns:
        Initialized embedding provider.

    Raises:
        ValueError: If provider is not supported.
    """
    provider = provider.lower()

    if provider == "google":
        return GoogleProvider(api_key=api_key)
    if provider == "jina":
        return JinaProvider(api_key=api_key)
    msg = f"Unsupported embedding provider: {provider}. Supported providers: google, jina"
    raise ValueError(
        msg,
    )


async def auto_select_provider(
    priority: list[str] | None = None,
) -> EmbeddingProviderBase | None:
    """Automatically select an embedding provider based on priority and API key availability.

    Tries providers in the specified priority order, validating API keys and authentication.
    Returns the first provider that successfully validates.

    Args:
        priority: List of provider names in priority order. Default: ["jina", "google"]

    Returns:
        First successfully validated provider, or None if all fail.
    """
    if priority is None:
        priority = ["jina", "google"]

    logger.info("auto_selecting_embedding_provider", priority=priority)

    for name in priority:
        provider_name = name.lower()

        # Check if API key is available in environment
        if provider_name == "google":
            api_key = os.getenv("GOOGLE_API_KEY")
            env_var = "GOOGLE_API_KEY"
        elif provider_name == "jina":
            api_key = os.getenv("JINA_API_KEY")
            env_var = "JINA_API_KEY"
        else:
            logger.warning("unsupported_provider_in_priority", provider=provider_name)
            continue

        if not api_key:
            logger.debug(
                "provider_skipped_no_api_key",
                provider=provider_name,
                env_var=env_var,
            )
            continue

        # Try to create and validate the provider
        try:
            provider = create_provider(provider=provider_name, api_key=api_key)

            # Get default model for validation
            default_model = get_default_model(provider_name)  # type: ignore

            # Validate authentication
            logger.info("validating_provider", provider=provider_name)
            if await provider.validate(default_model):
                logger.info(
                    "provider_auto_selected",
                    provider=provider_name,
                    model=default_model.name,
                    dimension=default_model.dimension,
                )
                return provider
            logger.warning(
                "provider_validation_failed",
                provider=provider_name,
            )
        except Exception as e:
            logger.warning(
                "provider_creation_failed",
                provider=provider_name,
                error=str(e),
                error_type=type(e).__name__,
            )

    logger.error("no_valid_provider_found", priority=priority)
    return None
