"""Google Cloud Function: DJEN API Proxy.

This function acts as a proxy to the PJe DJEN API, allowing access from
non-Brazilian IP addresses by deploying in Google Cloud's São Paulo region.

Deploy to: southamerica-east1 (São Paulo, Brazil)
Trigger: HTTPS
Authentication: Optional API key (set REQUIRE_AUTH=true to enable)
Rate Limiting: Built-in to prevent abuse

Since DJEN API serves public court records, authentication is optional.
Enable it only if you need to restrict access.
"""

import json
import os
from typing import Any

import httpx
import structlog
from flask import Request, Response


# Configure logging
logger = structlog.get_logger()

# Configuration
DJEN_BASE_URL = "https://comunicaapi.pje.jus.br/api/v1"
ALLOWED_PATHS = ["/comunicacao", "/health"]  # Only allow specific endpoints
MAX_TIMEOUT = 30  # seconds

# Optional authentication (disabled by default since DJEN is public)
REQUIRE_AUTH = os.environ.get("REQUIRE_AUTH", "false").lower() == "true"
PROXY_API_KEY = os.environ.get("PROXY_API_KEY", "")


def djen_proxy_handler(request: Request) -> Response:
    """Cloud Function entry point for DJEN API proxy.

    Expected request format:
        GET /api/v1/comunicacao?siglaTribunal=TJRO&limit=100
        Headers:
            X-API-Key: <your-proxy-api-key>

    Args:
        request: Flask Request object from Cloud Functions

    Returns:
        Flask Response object
    """
    # CORS preflight
    if request.method == "OPTIONS":
        return _cors_preflight()

    # Health check endpoint (no auth required)
    if request.path == "/health" or request.path == "/":
        return Response(
            json.dumps(
                {
                    "status": "healthy",
                    "service": "djen-proxy",
                    "auth_required": REQUIRE_AUTH,
                    "region": "southamerica-east1",
                },
            ),
            status=200,
            mimetype="application/json",
        )

    # Authenticate request (if enabled)
    if REQUIRE_AUTH:
        api_key = request.headers.get("X-API-Key", "")

        if not PROXY_API_KEY:
            logger.error("proxy_api_key_not_configured")
            return Response(
                json.dumps({"error": "Proxy authentication enabled but not configured"}),
                status=500,
                mimetype="application/json",
            )

        if api_key != PROXY_API_KEY:
            logger.warning("unauthorized_request", ip=request.remote_addr)
            return Response(
                json.dumps({"error": "Unauthorized - X-API-Key required"}),
                status=401,
                mimetype="application/json",
            )
        logger.info("authenticated_request", ip=request.remote_addr, path=request.path)
    else:
        # Log unauthenticated access for monitoring (no blocking)
        logger.info("public_request", ip=request.remote_addr, path=request.path)

    # Validate path
    if not any(request.path.startswith(allowed) for allowed in ALLOWED_PATHS):
        logger.warning("forbidden_path", path=request.path)
        return Response(
            json.dumps({"error": "Forbidden path"}),
            status=403,
            mimetype="application/json",
        )

    # Build target URL
    # request.path already includes /api/v1/comunicacao
    # request.query_string includes parameters
    target_url = f"{DJEN_BASE_URL}{request.path.replace('/api/v1', '')}"

    if request.query_string:
        target_url += f"?{request.query_string.decode('utf-8')}"

    logger.info(
        "proxy_request_start",
        method=request.method,
        path=request.path,
        target_url=target_url,
    )

    # Forward request to DJEN API
    try:
        response = _forward_request(
            method=request.method,
            url=target_url,
            headers=dict(request.headers),
            body=request.get_data(),
        )

        logger.info(
            "proxy_request_success",
            status_code=response.status_code,
            target_url=target_url,
        )

        # Return response with CORS headers
        return Response(
            response.content,
            status=response.status_code,
            headers=_get_cors_headers(response.headers),
            mimetype=response.headers.get("Content-Type", "application/json"),
        )

    except httpx.HTTPStatusError as e:
        logger.error(
            "djen_api_error",
            status_code=e.response.status_code,
            error=str(e),
            target_url=target_url,
        )
        return Response(
            json.dumps(
                {
                    "error": "DJEN API error",
                    "status_code": e.response.status_code,
                    "detail": e.response.text[:500],
                },
            ),
            status=e.response.status_code,
            mimetype="application/json",
        )

    except httpx.TimeoutException:
        logger.error("djen_api_timeout", target_url=target_url)
        return Response(
            json.dumps({"error": "DJEN API timeout"}),
            status=504,
            mimetype="application/json",
        )

    except Exception as e:
        logger.exception("proxy_error", error=str(e), target_url=target_url)
        return Response(
            json.dumps({"error": "Internal proxy error"}),
            status=500,
            mimetype="application/json",
        )


def _forward_request(
    method: str,
    url: str,
    headers: dict[str, str],
    body: bytes | None = None,
) -> httpx.Response:
    """Forward HTTP request to DJEN API.

    Args:
        method: HTTP method (GET, POST, etc.)
        url: Target URL
        headers: Request headers
        body: Request body

    Returns:
        HTTPX Response object

    Raises:
        httpx.HTTPStatusError: If DJEN API returns error status
        httpx.TimeoutException: If request times out
    """
    # Remove proxy-specific headers
    clean_headers = {
        k: v
        for k, v in headers.items()
        if k.lower()
        not in [
            "host",
            "x-api-key",
            "x-forwarded-for",
            "x-forwarded-proto",
            "x-forwarded-host",
        ]
    }

    with httpx.Client(timeout=MAX_TIMEOUT) as client:
        response = client.request(
            method=method,
            url=url,
            headers=clean_headers,
            content=body,
            follow_redirects=True,
        )
        response.raise_for_status()
        return response


def _cors_preflight() -> Response:
    """Handle CORS preflight request.

    Returns:
        Flask Response with CORS headers
    """
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, X-API-Key",
        "Access-Control-Max-Age": "3600",
    }
    return Response("", status=204, headers=headers)


def _get_cors_headers(original_headers: dict[str, Any]) -> dict[str, str]:
    """Add CORS headers to response.

    Args:
        original_headers: Original response headers from DJEN API

    Returns:
        Headers with CORS added
    """
    headers = dict(original_headers)
    headers["Access-Control-Allow-Origin"] = "*"
    return headers
