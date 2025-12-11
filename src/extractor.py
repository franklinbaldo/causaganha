import os
import pathlib
import json
import datetime
import re
import argparse
import logging
import time
import random
import tempfile
import asyncio
from typing import List, Optional

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None
    logging.warning(
        "Module fitz (PyMuPDF) could not be imported. PDF text extraction will not be available."
    )

try:
    from pydantic_ai import Agent
    from pydantic_ai.models.gemini import GeminiModel
    try:
        from .schemas import ExtractionResult, Decisao
    except ImportError:
        from schemas import ExtractionResult, Decisao
    PYDANTIC_AI_AVAILABLE = True
except ImportError as e:
    logging.warning(f"pydantic-ai or dependencies not available: {e}")
    PYDANTIC_AI_AVAILABLE = False


SYSTEM_PROMPT = """
Você é um assistente jurídico especializado em analisar Diários da Justiça.
Sua tarefa é extrair APENAS decisões de acórdãos e sentenças que tenham RESULTADO definido.
IGNORE despachos administrativos.

Regras de Extração:
- Processe decisões como "RECURSO PROVIDO", "SENTENÇA CONFIRMADA", "SENTENÇA PROCEDENTE", etc.
- Ignore despachos que apenas movimentam processos.
- Número CNJ: Use o número no formato NNNNNNN-NN.NNNN.N.NN.NNNN quando disponível.
- Tipo de Decisão: Identifique se é Acórdão, Sentença, Decisão Monocrática, etc.
- Partes e Advogados: Extraia nomes e OABs quando disponíveis.
- Resultado: Classifique o resultado (Procedente, Improcedente, etc).
- Resumo: Crie um resumo conciso (max 250 caracteres).
- Se houver texto indicando "CONTINUAÇÃO DO TRECHO ANTERIOR", use-o para contexto mas evite duplicar decisões já extraídas.
"""

class GeminiExtractor:
    """
    Extracts information from PDF files using the Gemini API via pydantic-ai.
    """

    def __init__(
        self, api_key: str | None = None, model_name: str = "gemini-1.5-flash"
    ):
        if api_key:
            self.api_key = api_key
            # pydantic-ai/google-genai typically checks env var or explicit arg
            os.environ["GEMINI_API_KEY"] = api_key
        else:
            self.api_key = os.getenv("GEMINI_API_KEY")

        self.model_name = model_name
        self.gemini_configured = False
        self.agent = None

        if PYDANTIC_AI_AVAILABLE and self.api_key:
            try:
                self.model = GeminiModel(self.model_name, api_key=self.api_key)
                self.agent = Agent(
                    self.model,
                    result_type=ExtractionResult,
                    system_prompt=SYSTEM_PROMPT,
                    retries=3
                )
                logging.info(
                    "GeminiExtractor initialized: pydantic-ai configured with API key."
                )
                self.gemini_configured = True
            except Exception as e:
                logging.error(
                    "GeminiExtractor: Failed to configure pydantic-ai agent: %s", e
                )
                self.gemini_configured = False
        else:
            logging.warning(
                "GeminiExtractor initialized: pydantic-ai not available or API key missing. Real API calls will be skipped."
            )
            self.gemini_configured = False

    def is_configured(self) -> bool:
        """Checks if Gemini is configured and an API key is available."""
        return bool(self.gemini_configured and self.agent)

    def _sanitize_filename(self, filename: str) -> str:
        sanitized = re.sub(r"[^\w\.\-_]", "", filename)
        if not sanitized:
            return "default_filename"
        return sanitized

    def _extract_text_from_pdf(self, pdf_path: pathlib.Path) -> list[str]:
        """Extract text from PDF using PyMuPDF (fitz) and return chunks."""
        if not fitz:
            logging.error("PyMuPDF (fitz) not available for text extraction.")
            return []

        doc = None
        try:
            doc = fitz.open(str(pdf_path))  # type: ignore
            page_count = len(doc)
            chunks = []
            chunk_size = 25
            overlap_size = 1

            for chunk_start in range(0, page_count, chunk_size):
                chunk_end = min(chunk_start + chunk_size, page_count)
                chunk_text_parts = []

                if chunk_start > 0:
                    overlap_start = max(0, chunk_start - overlap_size)
                    chunk_text_parts.append(
                        "\n=== CONTINUAÇÃO DO TRECHO ANTERIOR ===\n"
                    )
                    for page_num in range(overlap_start, chunk_start):
                        page = doc.load_page(page_num)
                        text = page.get_text()
                        chunk_text_parts.append(
                            f"\n--- PÁGINA {page_num + 1} (OVERLAP) ---\n{text}\n"
                        )
                    chunk_text_parts.append("\n=== NOVO TRECHO ===\n")

                for page_num in range(chunk_start, chunk_end):
                    page = doc.load_page(page_num)
                    text = page.get_text()
                    chunk_text_parts.append(
                        f"\n--- PÁGINA {page_num + 1} ---\n{text}\n"
                    )

                chunks.append("".join(chunk_text_parts))

            logging.info(
                f"Extracted text from {pdf_path.name} ({page_count} pages) into {len(chunks)} chunks"
            )
            return chunks

        except (RuntimeError, OSError) as e:
            logging.error("Error extracting text from PDF %s: %s", pdf_path.name, e)
            return []
        finally:
            if doc:
                try:
                    doc.close()
                except Exception as e_close:
                    logging.warning(
                        f"Error closing PDF document {pdf_path.name}: {e_close}"
                    )

    def extract_and_save_json(
        self, pdf_path: str | pathlib.Path, output_json_dir: str | pathlib.Path
    ) -> pathlib.Path | None:
        pdf_path = pathlib.Path(pdf_path)
        logging.info(f"Starting extraction for PDF: {pdf_path.name}")

        if not pdf_path.exists():
            logging.error(f"PDF file not found: {pdf_path}")
            return None

        output_json_dir = pathlib.Path(output_json_dir)
        output_json_dir.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix="pdf_extraction_") as temp_dir_str:
            temp_dir = pathlib.Path(temp_dir_str)
            logging.info(f"Using temporary directory for processing: {temp_dir}")

            final_extracted_data = None

            if not self.is_configured():
                logging.warning(
                    f"Skipping real Gemini API call for {pdf_path.name} (Gemini not configured). Returning dummy data."
                )
                final_extracted_data = {
                    "file_name_source": pdf_path.name,
                    "extraction_timestamp": datetime.datetime.now(
                        datetime.timezone.utc
                    ).isoformat(),
                    "status": "dummy_data_gemini_not_configured",
                    "decisions": [
                        {
                            "numero_processo": "0000000-00.0000.0.00.0000",
                            "tipo_decisao": "sentença",
                            "polo_ativo": ["N/A"],
                            "advogados_polo_ativo": ["N/A (OAB/UF)"],
                            "polo_passivo": ["N/A"],
                            "advogados_polo_passivo": ["N/A (OAB/UF)"],
                            "resultado": "procedente",
                            "data": "1900-01-01",
                            "resumo": "Decisão dummy."
                        }
                    ]
                }
            else:
                logging.info(
                    f"Attempting real Gemini API call for {pdf_path.name} using model {self.model_name}"
                )
                pdf_text_chunks = self._extract_text_from_pdf(pdf_path)
                if not pdf_text_chunks:
                    logging.error(f"Failed to extract text from {pdf_path.name}")
                    return None

                all_decisions = []

                for chunk_index, chunk_text in enumerate(pdf_text_chunks):
                    if chunk_index > 0:
                        delay = 4 + random.uniform(0.5, 1.5)
                        logging.info(
                            f"Rate limiting: waiting {delay:.1f}s before chunk {chunk_index + 1}"
                        )
                        time.sleep(delay)

                    retry_count = 0
                    max_retries = 5
                    base_delay = 30
                    response_successful = False

                    while retry_count < max_retries:
                        try:
                            logging.info(
                                f"Processing chunk {chunk_index + 1}/{len(pdf_text_chunks)} (attempt {retry_count + 1})"
                            )

                            # Run async agent synchronously using asyncio.run
                            # We create a new run for each chunk.
                            result = asyncio.run(
                                self.agent.run(f"Analise este trecho:\n{chunk_text}")
                            )

                            chunk_decisions = result.data.decisoes
                            # Convert pydantic models to dicts for JSON serialization later
                            all_decisions.extend([d.model_dump(mode='json') for d in chunk_decisions])
                            response_successful = True
                            break

                        except Exception as e_api:
                            # Handle rate limits (429) or other API errors
                            if (
                                "429" in str(e_api)
                                or "quota" in str(e_api).lower()
                                or "rate" in str(e_api).lower()
                            ):
                                retry_count += 1
                                if retry_count < max_retries:
                                    backoff = base_delay * (
                                        2 ** (retry_count - 1)
                                    ) + random.uniform(0, 10)
                                    logging.warning(
                                        f"Rate limit for chunk {chunk_index + 1}, attempt {retry_count}. Waiting {backoff:.1f}s..."
                                    )
                                    time.sleep(backoff)
                                else:
                                    logging.error(
                                        f"Max retries for rate limit exceeded for chunk {chunk_index + 1}: {e_api}"
                                    )
                            else:
                                logging.error(
                                    f"Error processing chunk {chunk_index + 1}: {e_api}"
                                )
                                response_successful = False
                                break

                    if not response_successful:
                        logging.error(f"Skipping chunk {chunk_index + 1} due to errors.")
                        return None

                final_extracted_data = {
                    "file_name_source": pdf_path.name,
                    "extraction_timestamp": datetime.datetime.now(
                        datetime.timezone.utc
                    ).isoformat(),
                    "decisions": all_decisions,
                    "chunks_processed": len(pdf_text_chunks),
                    "total_decisions_found": len(all_decisions),
                }
                logging.info(
                    f"Processed {len(pdf_text_chunks)} chunks for {pdf_path.name}. Total decisions: {len(all_decisions)}"
                )

            if final_extracted_data is None:
                logging.warning(f"No data extracted for {pdf_path.name}.")
                return None

            json_filename = f"{self._sanitize_filename(pdf_path.stem)}_extraction.json"
            output_json_path = output_json_dir / json_filename

            try:
                with open(output_json_path, "w", encoding="utf-8") as f:
                    json.dump(final_extracted_data, f, ensure_ascii=False, indent=4)
                logging.info(
                    f"Successfully saved extracted data to: {output_json_path}"
                )
                return output_json_path
            except IOError as e:
                logging.error(f"Error saving JSON file {output_json_path}: {e}")
                return None

def main():
    parser = argparse.ArgumentParser(
        description="Extract structured data from a PDF document using Gemini via pydantic-ai."
    )
    parser.add_argument(
        "--pdf_file",
        type=pathlib.Path,
        required=True,
        help="Path to the PDF file to process.",
    )
    parser.add_argument(
        "--output_dir",
        type=pathlib.Path,
        default=pathlib.Path(__file__).resolve().parent.parent.parent / "data",
        help="Directory to save the extracted JSON file. Defaults to data/",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="Gemini API Key (optional if GEMINI_API_KEY env var is set)",
    )
    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    if not args.pdf_file.exists() or not args.pdf_file.is_file():
        logging.error(f"PDF file not found: {args.pdf_file}")
        return

    extractor = GeminiExtractor(api_key=args.api_key)
    saved_path = extractor.extract_and_save_json(args.pdf_file, args.output_dir)
    if saved_path:
        logging.info(f"Extraction complete. JSON saved to {saved_path}")
    else:
        logging.warning(f"Extraction failed for {args.pdf_file}.")


if __name__ == "__main__":
    dummy_pdf_dir = pathlib.Path(__file__).resolve().parent.parent.parent / "data"
    dummy_pdf_dir.mkdir(parents=True, exist_ok=True)
    cli_test_pdf = dummy_pdf_dir / "cli_test_doc_for_extractor.pdf"
    if not cli_test_pdf.exists():
        try:
            from PyPDF2 import PdfWriter  # type: ignore

            writer = PdfWriter()
            writer.add_blank_page(width=612, height=792)
            with open(cli_test_pdf, "wb") as f:
                writer.write(f)
        except Exception:
            with open(cli_test_pdf, "w") as f:
                f.write("Dummy PDF content.")
    main()
