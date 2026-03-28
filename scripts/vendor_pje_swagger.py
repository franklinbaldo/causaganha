from __future__ import annotations

import argparse
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


MAGIC_VAL_403 = 403

DEFAULT_URL = "https://comunicaapi.pje.jus.br/swagger/djen.yml"
DEFAULT_OUTPUT = "openapi/pje-comunicaapi-djen.swagger.yml"


def fetch(url: str, timeout_s: float) -> bytes:
    req = Request(url, headers={"User-Agent": "causaganha-openapi-vendor/1.0"})
    try:
        with urlopen(req, timeout=timeout_s) as resp:
            body = resp.read()
    except HTTPError as exc:
        if exc.code == MAGIC_VAL_403:
            msg = (
                f"HTTP 403 when fetching {url}.\n\n"
                "The PJe host is frequently geo-blocked. Options:\n"
                "1) Run this script from a network that can reach the origin, or\n"
                "2) Mirror the YAML somewhere reachable and pass --url <mirror>, or\n"
                f"3) Download it manually and run with --input-file <path>.\n\n"
                f"Expected output file: {DEFAULT_OUTPUT}\n"
            )
            raise RuntimeError(msg) from exc
        raise
    if not body:
        msg = f"Empty response when fetching {url}"
        raise RuntimeError(msg)
    return body


def validate_swagger_bytes(content: bytes, *, source: str) -> None:
    head = content[:4096].decode("utf-8", errors="ignore")
    lowered = head.lower()
    if "<html" in lowered or "the request could not be satisfied" in lowered:
        msg = f"Fetched HTML instead of YAML from {source}"
        raise RuntimeError(msg)
    if "openapi:" not in lowered and "swagger:" not in lowered:
        msg = f"Fetched content does not look like an OpenAPI/Swagger spec (source: {source})"
        raise RuntimeError(msg)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Vendor the PJe Comunica API Swagger spec into the repo.",
    )
    src = parser.add_mutually_exclusive_group()
    src.add_argument("--url", default=DEFAULT_URL, help=f"Swagger URL (default: {DEFAULT_URL})")
    src.add_argument("--input-file", help="Read spec bytes from a local file instead of fetching")
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Output path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout (seconds)")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.input_file:
        source = str(args.input_file)
        content = Path(args.input_file).read_bytes()
    else:
        source = args.url
        content = fetch(args.url, timeout_s=args.timeout)

    validate_swagger_bytes(content, source=source)

    # Preserve upstream bytes exactly, but ensure a trailing newline (diff friendliness).
    if not content.endswith(b"\n"):
        content += b"\n"

    output_path.write_bytes(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
