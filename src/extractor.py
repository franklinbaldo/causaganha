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
from src.language_utils import detect_language, translate_text

try:
    import google.generativeai as genai
except ImportError:
    genai = None
    logging.warning(
        "Module google.generativeai could not be imported. Ensure it is installed correctly. GeminiExtractor will use dummy responses if API key is also missing."
    )

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None
    logging.warning(
        "Module fitz (PyMuPDF) could not be imported. PDF text extraction will not be available."
    )


class GeminiExtractor:
    """
    Extracts information from PDF files using the Gemini API.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "gemini-1.5-flash-latest",
        enable_translation: bool = False,
        target_language: str = "pt",
    ):
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = os.getenv("GEMINI_API_KEY")

        self.model_name = model_name
        self.enable_translation = enable_translation
        self.target_language = target_language

        if genai and self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                logging.info(
                    "GeminiExtractor initialized: google.generativeai configured with API key."
                )
                self.gemini_configured = True
            except (ValueError, TypeError, ImportError) as e:
                logging.error(
                    "GeminiExtractor: Failed to configure google.generativeai: %s", e
                )
                self.gemini_configured = False
        elif genai and not self.api_key:
            logging.warning(
                "GeminiExtractor initialized: google.generativeai imported, but API key missing. Real API calls will be skipped."
            )
            self.gemini_configured = False
        else:
            logging.info(
                "GeminiExtractor initialized: google.generativeai not imported. Real API calls will be skipped."
            )
            self.gemini_configured = False

    def is_configured(self) -> bool:
        """Checks if Gemini is configured and an API key is available."""
        return bool(genai and self.api_key and self.gemini_configured)

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
                    "numero_processo": "0000000-00.0000.0.00.0000",
                    "tipo_decisao": "sentença",
                    "partes": {"requerente": ["N/A"], "requerido": ["N/A"]},
                    "advogados": {
                        "requerente": ["N/A (OAB/UF)"],
                        "requerido": ["N/A (OAB/UF)"],
                    },
                    "resultado": "procedente",
                    "data_decisao": "1900-01-01",
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
                if genai is None:
                    logging.error("genai module is None, cannot proceed with API call.")
                    return None

                model = genai.GenerativeModel(self.model_name)
                prompt = """Este é o texto extraído do Diário da Justiça. Analise o conteúdo e extraia APENAS decisões de acórdãos e sentenças que tenham RESULTADO definido (procedente, improcedente, etc). IGNORE despachos administrativos.

SEMPRE retorne um array JSON válido. Exemplos:

Array vazio se não encontrar decisões:
[]

Array com decisões encontradas:
[
    {
        "numero_processo": "1234567-89.2023.8.23.0001",
        "tipo_decisao": "acórdão",
        "polo_ativo": ["Nome Agravante", "Nome Autor"],
        "advogados_polo_ativo": ["Nome Advogado (OAB/UF)"],
        "polo_passivo": ["Nome Agravado", "Nome Réu"],
        "advogados_polo_passivo": ["Nome Advogado (OAB/UF)"],
        "resultado": "procedente|improcedente|parcialmente_procedente|extinto|provido|negado_provimento|confirmada|reformada",
        "data": "YYYY-MM-DD",
        "resumo": "Resumo da decisão em no máximo 250 caracteres"
    }
]

REGRAS OBRIGATÓRIAS:
- Retorne SEMPRE um array JSON válido, nunca texto explicativo
- Se não encontrar decisões com resultado, retorne: []
- Processe decisões como "RECURSO PROVIDO", "SENTENÇA CONFIRMADA", "SENTENÇA PROCEDENTE", etc.
- Ignore despachos que apenas movimentam processos
- Número CNJ quando disponível, senão use o número encontrado
- Procure por textos como: "Decisão:", "Decisão Monocrática:", "À UNANIMIDADE", etc.
- Resumo deve ter no máximo 250 caracteres e descrever brevemente a decisão
- Se há texto de CONTINUAÇÃO DO TRECHO ANTERIOR, considere-o para contexto mas evite duplicar decisões"""

                for chunk_index, chunk_text in enumerate(pdf_text_chunks):
                    if chunk_index > 0:
                        delay = 4 + random.uniform(0.5, 1.5)
                        logging.info(
                            f"Rate limiting: waiting {delay:.1f}s before chunk {chunk_index + 1}"
                        )
                        time.sleep(delay)

                    (
                        retry_count,
                        max_retries,
                        base_delay,
                        response_successful,
                        response,
                    ) = 0, 5, 30, False, None
                    while retry_count < max_retries:
                        try:
                            logging.info(
                                f"Processing chunk {chunk_index + 1}/{len(pdf_text_chunks)} (attempt {retry_count + 1})"
                            )
                            full_prompt = f"{prompt}\n\nTexto (Chunk {chunk_index + 1}):\n{chunk_text}"
                            response = model.generate_content(full_prompt)
                            response_successful = True
                            break
                        except Exception as e_api:
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
                                    f"Non-rate-limit error for chunk {chunk_index + 1}: {e_api}"
                                )
                                response_successful = False
                                break

                    if not response_successful:
                        logging.error(f"Skipping chunk {chunk_index + 1}.")
                        return None

                    try:
                        clean_response = (
                            response.text.strip()
                            .removeprefix("```json")
                            .removesuffix("```")
                            .strip()
                        )  # type: ignore
                        chunk_decisions = json.loads(clean_response)
                        if isinstance(chunk_decisions, list):
                            all_decisions.extend(chunk_decisions)
                        else:
                            logging.warning(
                                f"Chunk {chunk_index + 1}: Unexpected response type: {type(chunk_decisions)}"
                            )
                    except json.JSONDecodeError as je:
                        logging.error(
                            f"Chunk {chunk_index + 1}: JSON parse error: {je}. Raw: {response.text[:300]}..."
                        )  # type: ignore
                        return None

                # Detect language and optionally translate
                for dec in all_decisions:
                    combined = " ".join(
                        str(v) if not isinstance(v, list) else " ".join(v)
                        for v in dec.values()
                    )
                    lang = detect_language(combined)
                    dec["language"] = lang
                    if self.enable_translation and lang != self.target_language:
                        if "resultado" in dec and isinstance(dec["resultado"], str):
                            dec["resultado_translated"] = translate_text(
                                dec["resultado"], self.target_language
                            )

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
        # TemporaryDirectory is automatically cleaned up here via 'with' statement


def main():
    parser = argparse.ArgumentParser(
        description="Extract structured data from a PDF document using Gemini."
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
    args = parser.parse_args()
    if not args.pdf_file.exists() or not args.pdf_file.is_file():
        logging.error(f"PDF file not found: {args.pdf_file}")
        return  # Added return
    extractor = GeminiExtractor()
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
        except Exception:  # Broad except for dummy creation
            with open(cli_test_pdf, "w") as f:  # Fixed: multiple statements on one line
                f.write("Dummy PDF content.")
    main()
