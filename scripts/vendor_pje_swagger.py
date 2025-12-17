from __future__ import annotations

import argparse
from pathlib import Path
from urllib.request import Request, urlopen


DEFAULT_URL = "https://comunicaapi.pje.jus.br/swagger/djen.yml"
DEFAULT_OUTPUT = "openapi/pje-comunicaapi-djen.swagger.yml"


def fetch(url: str, timeout_s: float) -> bytes:
    req = Request(url, headers={"User-Agent": "causaganha-openapi-vendor/1.0"})
    with urlopen(req, timeout=timeout_s) as resp:  # noqa: S310
        body = resp.read()
    if not body:
        msg = f"Empty response when fetching {url}"
        raise RuntimeError(msg)
    return body


def main() -> int:
    parser = argparse.ArgumentParser(description="Vendor the PJe Comunica API Swagger spec into the repo.")
    parser.add_argument("--url", default=DEFAULT_URL, help=f"Swagger URL (default: {DEFAULT_URL})")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help=f"Output path (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout (seconds)")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    content = fetch(args.url, timeout_s=args.timeout)

    # Preserve upstream bytes exactly, but ensure a trailing newline (diff friendliness).
    if not content.endswith(b"\n"):
        content += b"\n"

    output_path.write_bytes(content)
    print(f"Wrote {output_path} (source: {args.url})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

