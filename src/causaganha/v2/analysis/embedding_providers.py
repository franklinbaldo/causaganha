"""Embedding provider implementations for different APIs (Google, Jina AI, etc.)."""

import os
from abc import abstractmethod
from typing import Literal, Protocol

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()

# Task type mapping between providers
TaskType = Literal["RETRIEVAL_QUERY", "RETRIEVAL_DOCUMENT"]


class EmbeddingProvider(Protocol):
    """Protocol defining the interface for embedding providers."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension for this provider."""
        ...

    @abstractmethod
    async def embed_text(
        self,
        text: str,
        task_type: TaskType = "RETRIEVAL_QUERY",
    ) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed.
            task_type: Type of task (RETRIEVAL_QUERY or RETRIEVAL_DOCUMENT).

        Returns:
            Embedding vector.

        Raises:
            httpx.HTTPError: If the API request fails.
        """
        ...

    @abstractmethod
    async def validate(self) -> bool:
        """Validate that the provider is configured correctly and can authenticate.

        Returns:
            True if provider is valid and can authenticate, False otherwise.
        """
        ...


class GoogleEmbeddingProvider:
    """Google Gemini embedding provider using text-embedding-004 model."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "text-embedding-004",
        dimension: int = 768,
    ) -> None:
        """Initialize Google embedding provider.

        Args:
            api_key: Google API key. If None, reads from GOOGLE_API_KEY env var.
            model: Embedding model to use (default: text-embedding-004).
            dimension: Embedding dimension (default: 768).
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Google API key must be provided or set in GOOGLE_API_KEY env var"
            )

        self.model = model
        self._dimension = dimension
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

        logger.info(
            "google_embedding_provider_initialized",
            model=model,
            dimension=dimension,
        )

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        return self._dimension

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def embed_text(
        self,
        text: str,
        task_type: TaskType = "RETRIEVAL_QUERY",
    ) -> list[float]:
        """Generate embedding for a single text using Google's API.

        Args:
            text: Text to embed.
            task_type: Type of task (RETRIEVAL_QUERY or RETRIEVAL_DOCUMENT).

        Returns:
            Embedding vector (768 dimensions by default).

        Raises:
            httpx.HTTPError: If the API request fails.
        """
        url = f"{self.base_url}/models/{self.model}:embedContent"
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
                    task_type=task_type,
                )

                return embedding

            except httpx.HTTPError as e:
                logger.error(
                    "google_embedding_failed",
                    error=str(e),
                    text_length=len(text),
                )
                raise

    async def validate(self) -> bool:
        """Validate Google provider by testing API authentication with a simple request.

        Returns:
            True if authentication succeeds, False otherwise.
        """
        try:
            # Try to embed a very short test text
            await self.embed_text("test", task_type="RETRIEVAL_QUERY")
            logger.info("google_provider_validated", status="success")
            return True
        except Exception as e:
            logger.warning(
                "google_provider_validation_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return False


class JinaEmbeddingProvider:
    """Jina AI embedding provider using jina-embeddings-v3 model."""

    # Task type mapping: our standard -> Jina's task format
    TASK_MAPPING = {
        "RETRIEVAL_QUERY": "retrieval.query",
        "RETRIEVAL_DOCUMENT": "retrieval.passage",
    }

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "jina-embeddings-v3",
        dimension: int = 1024,
    ) -> None:
        """Initialize Jina AI embedding provider.

        Args:
            api_key: Jina API key. If None, reads from JINA_API_KEY env var.
            model: Embedding model to use (default: jina-embeddings-v3).
            dimension: Embedding dimension (default: 1024, range: 256-1024).
        """
        self.api_key = api_key or os.getenv("JINA_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Jina API key must be provided or set in JINA_API_KEY env var"
            )

        self.model = model
        self._dimension = dimension
        self.base_url = "https://api.jina.ai/v1"

        # Validate dimension range for jina-embeddings-v3
        if "v3" in model and not (256 <= dimension <= 1024):
            raise ValueError(
                f"Jina v3 dimension must be between 256 and 1024, got {dimension}"
            )

        logger.info(
            "jina_embedding_provider_initialized",
            model=model,
            dimension=dimension,
        )

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        return self._dimension

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def embed_text(
        self,
        text: str,
        task_type: TaskType = "RETRIEVAL_QUERY",
    ) -> list[float]:
        """Generate embedding for a single text using Jina AI's API.

        Args:
            text: Text to embed.
            task_type: Type of task (RETRIEVAL_QUERY or RETRIEVAL_DOCUMENT).

        Returns:
            Embedding vector (1024 dimensions by default).

        Raises:
            httpx.HTTPError: If the API request fails.
        """
        url = f"{self.base_url}/embeddings"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        # Map our task type to Jina's format
        jina_task = self.TASK_MAPPING.get(task_type, "retrieval.query")

        payload = {
            "input": [text],  # Jina expects an array
            "model": self.model,
            "dimensions": self._dimension,
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
                    task_type=task_type,
                    jina_task=jina_task,
                )

                return embedding

            except httpx.HTTPError as e:
                logger.error(
                    "jina_embedding_failed",
                    error=str(e),
                    text_length=len(text),
                    status_code=getattr(e.response, "status_code", None)
                    if hasattr(e, "response")
                    else None,
                )
                raise

    async def validate(self) -> bool:
        """Validate Jina provider by testing API authentication with a simple request.

        Returns:
            True if authentication succeeds, False otherwise.
        """
        try:
            # Try to embed a very short test text
            await self.embed_text("test", task_type="RETRIEVAL_QUERY")
            logger.info("jina_provider_validated", status="success")
            return True
        except Exception as e:
            logger.warning(
                "jina_provider_validation_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return False


def create_embedding_provider(
    provider: str = "google",
    api_key: str | None = None,
    **kwargs,
) -> EmbeddingProvider:
    """Factory function to create an embedding provider.

    Args:
        provider: Provider name ('google' or 'jina').
        api_key: API key for the provider.
        **kwargs: Additional provider-specific arguments.

    Returns:
        Initialized embedding provider.

    Raises:
        ValueError: If provider is not supported.
    """
    provider = provider.lower()

    if provider == "google":
        return GoogleEmbeddingProvider(api_key=api_key, **kwargs)
    elif provider == "jina":
        return JinaEmbeddingProvider(api_key=api_key, **kwargs)
    else:
        raise ValueError(
            f"Unsupported embedding provider: {provider}. "
            f"Supported providers: google, jina"
        )


async def auto_select_provider(
    priority: list[str] | None = None,
    **kwargs,
) -> EmbeddingProvider | None:
    """Automatically select an embedding provider based on priority and API key availability.

    Tries providers in the specified priority order, validating API keys and authentication.
    Returns the first provider that successfully validates.

    Args:
        priority: List of provider names in priority order. Default: ["jina", "google"]
        **kwargs: Additional provider-specific arguments.

    Returns:
        First successfully validated provider, or None if all fail.
    """
    if priority is None:
        priority = ["jina", "google"]

    logger.info("auto_selecting_embedding_provider", priority=priority)

    for provider_name in priority:
        provider_name = provider_name.lower()

        # Check if API key is available in environment
        if provider_name == "google":
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                logger.debug(
                    "provider_skipped_no_api_key",
                    provider=provider_name,
                    env_var="GOOGLE_API_KEY",
                )
                continue
        elif provider_name == "jina":
            api_key = os.getenv("JINA_API_KEY")
            if not api_key:
                logger.debug(
                    "provider_skipped_no_api_key",
                    provider=provider_name,
                    env_var="JINA_API_KEY",
                )
                continue
        else:
            logger.warning("unsupported_provider_in_priority", provider=provider_name)
            continue

        # Try to create and validate the provider
        try:
            provider = create_embedding_provider(
                provider=provider_name,
                api_key=api_key,
                **kwargs,
            )

            # Validate authentication
            logger.info("validating_provider", provider=provider_name)
            if await provider.validate():
                logger.info(
                    "provider_auto_selected",
                    provider=provider_name,
                    dimension=provider.dimension,
                )
                return provider
            else:
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
