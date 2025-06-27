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

    def __init__(self, api_key: str | None = None):
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = os.getenv("GEMINI_API_KEY")

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
        else:  # genai is None
            logging.info(
                "GeminiExtractor initialized: google.generativeai not imported. Real API calls will be skipped."
            )
            self.gemini_configured = False

    def _sanitize_filename(self, filename: str) -> str:
        sanitized = re.sub(r"[^\w\.\-_]", "", filename)
        return sanitized if sanitized else "default_filename"

    def _extract_text_from_pdf(self, pdf_path: pathlib.Path) -> list[str]:
        """Extract text from PDF using PyMuPDF (fitz) and return chunks of 10 pages each"""
        if not fitz:
            logging.error("PyMuPDF (fitz) not available for text extraction")
            return []

        try:
            doc = fitz.open(str(pdf_path))
            page_count = len(doc)
            chunks = []
            chunk_size = 25

            overlap_size = 1  # 1 page overlap

            for chunk_start in range(0, page_count, chunk_size):
                chunk_end = min(chunk_start + chunk_size, page_count)
                chunk_text = ""

                # Add overlap from previous chunk (if not the first chunk)
                if chunk_start > 0:
                    overlap_start = max(0, chunk_start - overlap_size)
                    chunk_text += "\n=== CONTINUAÇÃO DO TRECHO ANTERIOR ===\n"
                    for page_num in range(overlap_start, chunk_start):
                        page = doc.load_page(page_num)
                        text = page.get_text()
                        chunk_text += (
                            f"\n--- PÁGINA {page_num + 1} (OVERLAP) ---\n{text}\n"
                        )
                    chunk_text += "\n=== NOVO TRECHO ===\n"

                # Add main chunk pages
                for page_num in range(chunk_start, chunk_end):
                    page = doc.load_page(page_num)
                    text = page.get_text()
                    chunk_text += f"\n--- PÁGINA {page_num + 1} ---\n{text}\n"

                chunks.append(chunk_text)
                if chunk_start > 0:
                    logging.info(
                        f"Created chunk {len(chunks)}: pages {chunk_start - overlap_size + 1}-{chunk_end} (with overlap)"
                    )
                else:
                    logging.info(
                        f"Created chunk {len(chunks)}: pages {chunk_start + 1}-{chunk_end}"
                    )

            doc.close()
            logging.info(
                f"Successfully extracted text from {pdf_path.name} ({page_count} pages) into {len(chunks)} chunks"
            )
            return chunks

        except (RuntimeError, OSError) as e:
            logging.error("Error extracting text from PDF %s: %s", pdf_path.name, e)
            if "doc" in locals():
                try:
                    doc.close()
                except (RuntimeError, AttributeError):
                    pass
            return []

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

        # Create temporary directory for processing artifacts
        temp_dir = pathlib.Path(tempfile.mkdtemp(prefix="pdf_extraction_"))
        logging.info(f"Using temporary directory for processing: {temp_dir}")

        final_extracted_data = None

        if not self.gemini_configured:
            logging.warning(
                f"Skipping real Gemini API call for {pdf_path.name} (Gemini not configured or API key missing). Returning dummy data structure."
            )
            # Dummy data structure as a fallback
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
            logging.info(f"Attempting real Gemini API call for {pdf_path.name}")

            # Extract text from PDF in chunks
            pdf_text_chunks = self._extract_text_from_pdf(pdf_path)
            if not pdf_text_chunks:
                logging.error(f"Failed to extract text from {pdf_path.name}")
                final_extracted_data = None
            else:
                # Save full extracted text for debugging in temp directory
                full_text = "\n".join(pdf_text_chunks)
                text_file_path = temp_dir / f"{pdf_path.stem}_extracted_text.txt"

                try:
                    with open(text_file_path, "w", encoding="utf-8") as f:
                        f.write(full_text)
                    logging.info(f"Saved extracted text to temp: {text_file_path}")
                except (OSError, IOError) as e:
                    logging.warning("Failed to save extracted text: %s", e)

                # Process each chunk separately
                all_decisions = []
                all_raw_responses = []

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

                model = genai.GenerativeModel("gemini-2.5-flash-lite-preview-06-17")

                for chunk_index, chunk_text in enumerate(pdf_text_chunks):
                    # Rate limiting: Free tier is 15 RPM, so wait 4+ seconds between requests
                    if chunk_index > 0:
                        delay = 4 + random.uniform(0.5, 1.5)  # 4-5.5 seconds
                        logging.info(
                            f"Rate limiting: waiting {delay:.1f} seconds before chunk {chunk_index + 1}"
                        )
                        time.sleep(delay)

                    retry_count = 0
                    max_retries = 5
                    base_delay = 30
                    response_successful = False
                    response = None  # Ensure response is defined before the loop

                    while retry_count < max_retries:
                        try:
                            logging.info(
                                f"Processing chunk {chunk_index + 1}/{len(pdf_text_chunks)} for {pdf_path.name} (attempt {retry_count + 1})"
                            )
                            full_prompt = f"{prompt}\n\nTexto extraído do PDF (Chunk {chunk_index + 1}):\n{chunk_text}"
                            response = model.generate_content(full_prompt)
                            response_successful = True
                            break
                        except (OSError, ValueError, Exception) as e:
                            if (
                                "429" in str(e)
                                or "quota" in str(e).lower()
                                or "rate" in str(e).lower()
                            ):
                                retry_count += 1
                                if retry_count < max_retries:
                                    backoff_delay = base_delay * (
                                        2 ** (retry_count - 1)
                                    ) + random.uniform(0, 10)
                                    logging.warning(
                                        f"Rate limit hit for chunk {chunk_index + 1}, attempt {retry_count}. Waiting {backoff_delay:.1f} seconds..."
                                    )
                                    time.sleep(backoff_delay)
                                else:
                                    logging.error(
                                        f"Max retries for rate limit hit exceeded for chunk {chunk_index + 1}: {e}"
                                    )
                                    # response_successful remains False, loop will terminate
                            else:
                                logging.error(
                                    f"Non-rate-limit error for chunk {chunk_index + 1}: {e}"
                                )
                                response_successful = False
                                break

                    if not response_successful:
                        logging.error(
                            f"Skipping chunk {chunk_index + 1} due to unrecoverable API error or max retries."
                        )
                        # If one chunk fails unrecoverably, consider the whole PDF extraction a failure
                        logging.error(
                            f"Aborting extraction for PDF {pdf_path.name} due to error in chunk {chunk_index + 1}."
                        )
                        return None  # Abort for the entire PDF

                    # Process the successful response
                    logging.info(
                        f"Response received from Gemini for {pdf_path.name} chunk {chunk_index + 1}"
                    )

                    # Save raw response for this chunk in temp directory
                    raw_response_file = (
                        temp_dir
                        / f"{pdf_path.stem}_gemini_raw_response_chunk_{chunk_index + 1}.txt"
                    )
                    try:
                        with open(raw_response_file, "w", encoding="utf-8") as f:
                            f.write(response.text)
                        logging.info(
                            f"Saved raw Gemini response chunk {chunk_index + 1} to temp: {raw_response_file}"
                        )
                        all_raw_responses.append(
                            f"Chunk {chunk_index + 1}: {response.text[:200]}..."
                        )
                    except (OSError, IOError) as e:
                        logging.warning(
                            "Failed to save raw Gemini response for chunk %d: %s",
                            chunk_index + 1,
                            e,
                        )

                    # Parse JSON response for this chunk
                    try:
                        # Clean up response text by removing markdown if present
                        clean_response = response.text.strip()
                        if clean_response.startswith("```json"):
                            clean_response = (
                                clean_response.replace("```json", "")
                                .replace("```", "")
                                .strip()
                            )
                        elif clean_response.startswith("```"):
                            clean_response = clean_response.replace("```", "").strip()

                        chunk_decisions = json.loads(clean_response)

                        if isinstance(chunk_decisions, list):
                            all_decisions.extend(chunk_decisions)
                            logging.info(
                                f"Chunk {chunk_index + 1}: Found {len(chunk_decisions)} decisions"
                            )
                        else:
                            logging.warning(
                                f"Chunk {chunk_index + 1}: Unexpected response format: {type(chunk_decisions)}"
                            )

                    except json.JSONDecodeError as je:
                        logging.error(
                            f"Chunk {chunk_index + 1}: Failed to parse JSON response: {je}. Aborting extraction for this PDF."
                        )
                        logging.debug(
                            f"Chunk {chunk_index + 1} raw response: {response.text[:300]}..."
                        )
                        return None  # Abort for the entire PDF

                # Combine all results
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
                    f"Completed processing {len(pdf_text_chunks)} chunks for {pdf_path.name}. Total decisions found: {len(all_decisions)}"
                )

        if final_extracted_data is None:
            logging.warning(
                f"No data extracted or error occurred for {pdf_path.name}. JSON file will not be saved."
            )
            return None

        # Always use PDF filename for consistency (not individual process numbers)
        process_number_to_use = f"{pdf_path.stem}_extraction"

        sanitized_filename_base = self._sanitize_filename(process_number_to_use)
        json_filename = f"{sanitized_filename_base}.json"
        output_json_path = output_json_dir / json_filename

        try:
            with open(output_json_path, "w", encoding="utf-8") as f:
                json.dump(final_extracted_data, f, ensure_ascii=False, indent=4)
            logging.info(f"Successfully saved extracted data to: {output_json_path}")

            # Clean up temporary directory
            try:
                import shutil

                shutil.rmtree(temp_dir)
                logging.info(f"Cleaned up temporary directory: {temp_dir}")
            except (OSError, FileNotFoundError) as cleanup_error:
                logging.warning(
                    "Failed to clean up temporary directory: %s", cleanup_error
                )

            return output_json_path
        except IOError as e:
            logging.error(f"Error saving JSON file {output_json_path}: {e}")
            # Clean up temp directory even on failure
            try:
                import shutil

                shutil.rmtree(temp_dir)
            except Exception:
                pass
            return None


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
        logging.error(f"PDF file not found or is not a file: {args.pdf_file}")
        return

    # For testing, GEMINI_API_KEY should be in the environment or passed to constructor
    extractor = GeminiExtractor()
    saved_path = extractor.extract_and_save_json(args.pdf_file, args.output_dir)

    if saved_path:
        logging.info(f"Extraction process complete. JSON saved to {saved_path}")
    else:
        logging.warning(
            f"Extraction process failed or produced no output for {args.pdf_file}."
        )


if __name__ == "__main__":
    # Create a dummy PDF for CLI testing if it doesn't exist
    dummy_pdf_dir = pathlib.Path(__file__).resolve().parent.parent.parent / "data"
    dummy_pdf_dir.mkdir(parents=True, exist_ok=True)
    cli_test_pdf = (
        dummy_pdf_dir / "cli_test_doc_for_extractor.pdf"
    )  # Different name to avoid conflict
    if not cli_test_pdf.exists():
        try:
            # Attempt to create a more realistic dummy PDF if PyPDF2 is available
            from PyPDF2 import PdfWriter

            writer = PdfWriter()
            writer.add_blank_page(width=612, height=792)  # Standard letter size
            # You could add some text here if needed for more advanced dummy content
            # writer.add_page(...)
            with open(cli_test_pdf, "wb") as f:
                writer.write(f)
            logging.info(
                f"Created dummy PDF (blank page) for CLI testing: {cli_test_pdf}"
            )
        except ImportError:
            with open(cli_test_pdf, "w") as f:
                f.write(
                    "This is a dummy PDF content for CLI testing (google-generativeai not available or text-only dummy)."
                )
            logging.info(
                f"Created basic dummy PDF (text file) for CLI testing: {cli_test_pdf}"
            )
        except (OSError, IOError) as e:
            logging.error(
                "Could not create dummy PDF: %s. Falling back to simple text file.", e
            )
            with open(cli_test_pdf, "w") as f:
                f.write("Fallback dummy PDF content.")
            logging.info(
                f"Created super-basic dummy PDF (text file) for CLI testing: {cli_test_pdf}"
            )

    # To run main: python causaganha/core/extractor.py --pdf_file data/cli_test_doc_for_extractor.pdf
    # Ensure GEMINI_API_KEY is set in your environment if you want to test real API calls.
    main()
