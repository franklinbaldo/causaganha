from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import httpx


DEFAULT_BASE_URL = "https://comunicaapi.pje.jus.br/api/v1"


def _candidate_urls(base_url: str) -> list[str]:
    base_url = base_url.rstrip("/")
    return [
        f"{base_url}/openapi.json",
        f"{base_url}/openapi.yaml",
        f"{base_url}/swagger.json",
        f"{base_url}/swagger.yaml",
        f"{base_url}/api-docs",
        f"{base_url}/api-docs/swagger.json",
        f"{base_url}/api-docs/openapi.json",
    ]


def _try_fetch(url: str, timeout_s: float) -> tuple[str, bytes] | None:
    with httpx.Client(timeout=timeout_s, follow_redirects=True) as client:
        resp = client.get(url, headers={"Accept": "application/json, text/yaml, */*"})
        if resp.status_code >= 400:
            return None
        return resp.headers.get("content-type", ""), resp.content


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch and vendor the PJe Comunica API OpenAPI definition.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"API base URL (default: {DEFAULT_BASE_URL})")
    parser.add_argument(
        "--output",
        default="openapi/pje-comunicaapi-v1.openapi.json",
        help="Output path for the vendored OpenAPI (JSON).",
    )
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout (seconds).")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    last_error: str | None = None
    for url in _candidate_urls(args.base_url):
        try:
            result = _try_fetch(url, timeout_s=args.timeout)
            if result is None:
                last_error = f"HTTP error for {url}"
                continue

            content_type, body = result

            # Prefer a JSON file on disk to avoid toolchain variability.
            if "json" in content_type.lower() or body.lstrip().startswith((b"{", b"[")):
                data: Any = json.loads(body.decode("utf-8", errors="replace"))
            else:
                # If we ever hit YAML, keep it simple: store a JSON wrapper with the raw payload.
                # (We can add a YAML parser later if we actually encounter YAML in the wild.)
                data = {"_raw": body.decode("utf-8", errors="replace"), "_content_type": content_type, "_source": url}

            output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Wrote {output_path} (source: {url})")
            return 0

        except Exception as exc:  # noqa: BLE001
            last_error = f"{url}: {exc}"
            continue

    message = (
        "Failed to fetch OpenAPI definition.\n"
        f"- base_url: {args.base_url}\n"
        f"- tried: {', '.join(_candidate_urls(args.base_url))}\n"
        f"- last_error: {last_error}\n\n"
        "Note: the service may be geo-blocked by CloudFront (HTTP 403). "
        "If so, run this from an allowed network and commit the generated file."
    )
    raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())

