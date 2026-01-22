"""Embedding provider implementations (API services).

This module defines embedding providers (API services) separately from models (configurations).
Providers handle API authentication, requests, retries, and error handling.
Models define configuration like dimensions and token limits.
"""

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Literal

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


class LocalProvider(EmbeddingProviderBase):
    """Local embedding provider using CPU-optimized models (ONNX Runtime).

    Supports models:
    - intfloat/multilingual-e5-small (384D, 512 tokens, multilingual)
    - sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 (384D, 128 tokens)
    - neuralmind/bert-base-portuguese-cased (768D, 512 tokens, Portuguese-specific)

    Uses sentence-transformers library with ONNX Runtime backend for optimal CPU performance.
    Models are downloaded once and cached locally (~/.cache/huggingface/).
    """

    def __init__(
        self,
        cache_dir: str | Path | None = None,
        device: str = "cpu",
    ) -> None:
        """Initialize local embedding provider.

        Args:
            cache_dir: Directory for model cache. If None, uses default (~/.cache/huggingface/).
            device: Device for inference ('cpu' or 'cuda'). Default: 'cpu'.

        Note:
            Unlike API providers, LocalProvider doesn't require an API key.
            Models are loaded on-demand when first used.
        """
        # LocalProvider doesn't need API key, so we pass dummy values to parent
        # The parent's __init__ will not be called with real API key requirements
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.device = device
        self._models: dict[str, Any] = {}  # Cache for loaded models
        self.provider_name = "Local"

        logger.info(
            "local_provider_initialized",
            cache_dir=str(self.cache_dir) if self.cache_dir else "default",
            device=device,
        )

    def _ensure_dependencies(self) -> None:
        """Ensure required dependencies are available.

        Raises:
            ImportError: If sentence-transformers is not installed.
        """
        try:
            import sentence_transformers  # noqa: F401
        except ImportError as e:
            msg = (
                "sentence-transformers is required for LocalProvider. "
                "Install with: pip install sentence-transformers"
            )
            raise ImportError(msg) from e

    def _load_model(self, model: EmbeddingModel) -> Any:
        """Load a model into memory (cached).

        Args:
            model: EmbeddingModel configuration.

        Returns:
            Loaded SentenceTransformer model.

        Raises:
            ImportError: If sentence-transformers is not installed.
            ValueError: If model cannot be loaded.
        """
        if model.name in self._models:
            return self._models[model.name]

        self._ensure_dependencies()

        try:
            from sentence_transformers import SentenceTransformer

            logger.info(
                "loading_local_model",
                model_name=model.name,
                cache_dir=str(self.cache_dir) if self.cache_dir else "default",
            )

            # Load model with optional cache directory
            kwargs = {"device": self.device}
            if self.cache_dir:
                kwargs["cache_folder"] = str(self.cache_dir)

            loaded_model = SentenceTransformer(model.name, **kwargs)

            # Cache the loaded model
            self._models[model.name] = loaded_model

            logger.info(
                "local_model_loaded",
                model_name=model.name,
                dimension=loaded_model.get_sentence_embedding_dimension(),
                max_seq_length=loaded_model.max_seq_length,
            )

            return loaded_model

        except Exception as e:
            logger.exception(
                "local_model_load_failed",
                model_name=model.name,
                error=str(e),
            )
            raise

    async def embed_text(
        self,
        text: str,
        model: EmbeddingModel,
        task_type: TaskType = "RETRIEVAL_QUERY",
    ) -> list[float]:
        """Generate embedding using local CPU-optimized model.

        Args:
            text: Text to embed.
            model: EmbeddingModel configuration (must be a local model).
            task_type: Type of task (RETRIEVAL_QUERY or RETRIEVAL_DOCUMENT).
                      Note: Some local models don't distinguish between task types.

        Returns:
            Embedding vector with dimensions specified by model.

        Raises:
            ValueError: If model is not a local model.
            ImportError: If sentence-transformers is not installed.
        """
        if model.provider != "local":
            msg = f"LocalProvider requires a local model, got {model.provider}/{model.name}"
            raise ValueError(msg)

        # Load model (cached)
        loaded_model = self._load_model(model)

        try:
            # Generate embedding (synchronous, but fast on CPU)
            # sentence-transformers encode() returns numpy array
            embedding_np = loaded_model.encode(
                text,
                convert_to_numpy=True,
                normalize_embeddings=True,  # Important for cosine similarity
                show_progress_bar=False,
            )

            # Convert to list of floats
            embedding = embedding_np.tolist()

            logger.debug(
                "local_embedding_generated",
                text_length=len(text),
                embedding_dim=len(embedding),
                model=model.name,
                task_type=task_type,
            )

            return embedding

        except Exception as e:
            logger.exception(
                "local_embedding_failed",
                error=str(e),
                text_length=len(text),
                model=model.name,
            )
            raise

    async def validate(self, model: EmbeddingModel) -> bool:
        """Validate provider by testing model loading and inference.

        Args:
            model: EmbeddingModel to use for validation.

        Returns:
            True if model loads and generates embeddings successfully, False otherwise.
        """
        try:
            # Try to load the model and embed test text
            await self.embed_text("test", model=model, task_type="RETRIEVAL_QUERY")
            logger.info(
                "local_provider_validated",
                status="success",
                model=model.name,
            )
            return True
        except Exception as e:
            logger.warning(
                "local_provider_validation_failed",
                error=str(e),
                error_type=type(e).__name__,
                model=model.name,
            )
            return False


def create_provider(provider: str, api_key: str | None = None) -> EmbeddingProviderBase:
    """Factory function to create an embedding provider.

    Args:
        provider: Provider name ('google', 'jina', or 'local').
        api_key: API key for the provider (not required for 'local').

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
    if provider == "local":
        return LocalProvider()
    msg = f"Unsupported embedding provider: {provider}. " f"Supported providers: google, jina, local"
    raise ValueError(
        msg,
    )


async def auto_select_provider(
    priority: list[str] | None = None,
) -> EmbeddingProviderBase | None:
    """Automatically select an embedding provider based on priority and availability.

    Tries providers in the specified priority order, validating API keys (for cloud providers)
    or dependencies (for local providers). Returns the first provider that successfully validates.

    Args:
        priority: List of provider names in priority order. Default: ["local", "jina", "google"]

    Returns:
        First successfully validated provider, or None if all fail.
    """
    if priority is None:
        priority = ["local", "jina", "google"]

    logger.info("auto_selecting_embedding_provider", priority=priority)

    for name in priority:
        provider_name = name.lower()

        # Handle local provider (no API key required)
        if provider_name == "local":
            try:
                logger.info("trying_local_provider")
                provider = create_provider(provider="local")
                default_model = get_default_model("local")  # type: ignore

                # Validate by checking if dependencies are available
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
                    reason="dependencies_missing",
                )
            except Exception as e:
                logger.warning(
                    "provider_creation_failed",
                    provider=provider_name,
                    error=str(e),
                    error_type=type(e).__name__,
                )
            continue

        # Handle cloud providers (require API keys)
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
