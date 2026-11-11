"""Servidor Estático com suporte a HTTP Range (RFC 7233) e CORS para simulação do Internet Archive.

Simula perfeitamente o comportamento do archive.org:
- Responde com HTTP 206 Partial Content para requisições de Range de bytes.
- Registra no terminal a telemetria das requisições (Índice vs Range de Dados).
"""

from __future__ import annotations

import http.server
import os
import re
import socketserver
from pathlib import Path

PUBLIC_DIR = Path(__file__).resolve().parent / "public"
PORT = 8088


class InternetArchiveSimulatorHandler(http.server.SimpleHTTPRequestHandler):
    """Handler que implementa Range Requests e CORS simulando o Internet Archive."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC_DIR), **kwargs)

    def end_headers(self):
        # Habilita CORS total e cabeçalhos de Range
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Range, Content-Type, Accept")
        self.send_header(
            "Access-Control-Expose-Headers", "Content-Range, Content-Length, Accept-Ranges"
        )
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        path = self.translate_path(self.path)
        if not os.path.exists(path) or os.path.isdir(path):
            super().do_GET()
            return

        range_header = self.headers.get("Range")
        file_size = os.path.getsize(path)

        if not range_header:
            # Requisição normal sem Range (ex: página HTML ou micro-índice)
            if "indexes" in self.path:
                print(
                    f"\033[94m[REQ 1: ROTEAMENTO / ÍNDICE]\033[0m GET {self.path} ({file_size} B)"
                )
            elif "catalogo_tpu" in self.path:
                print(f"\033[95m[ASSET: CATÁLOGO TPU]\033[0m GET {self.path} ({file_size} B)")
            super().do_GET()
            return

        # Processamento de HTTP Range: bytes=start-end
        range_match = re.match(r"bytes=(\d+)-(\d*)", range_header)
        if not range_match:
            self.send_error(416, "Requested Range Not Satisfiable")
            return

        start = int(range_match.group(1))
        end = int(range_match.group(2)) if range_match.group(2) else file_size - 1

        if start >= file_size or end >= file_size or start > end:
            self.send_error(416, "Requested Range Not Satisfiable")
            return

        content_length = end - start + 1

        print(
            f"\033[92m[REQ 2: HTTP RANGE / IA SHARD]\033[0m Range: bytes={start}-{end} "
            f"({content_length:,d} B transferidos do ZIP total de {file_size:,d} B)"
        )

        self.send_response(206)  # 206 Partial Content
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
        self.send_header("Content-Length", str(content_length))
        self.end_headers()

        with open(path, "rb") as f:
            f.seek(start)
            self.wfile.write(f.read(content_length))


def run_server():
    server_address = ("", PORT)
    # Permite reusar a porta imediatamente após restart
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(server_address, InternetArchiveSimulatorHandler) as httpd:
        print("\n==================================================================")
        print(" Servidor de Simulação Internet Archive (HTTP Range + CORS) Ativo ")
        print(f" Endereço: http://localhost:{PORT}")
        print(f" Diretório Raiz: {PUBLIC_DIR}")
        print(" Pressione Ctrl+C para encerrar.")
        print("==================================================================\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor encerrado.")


if __name__ == "__main__":
    run_server()
