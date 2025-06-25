import os
import pathlib
import json
import datetime
import re
import argparse
import logging

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
            except Exception as e:
                logging.error(
                    f"GeminiExtractor: Failed to configure google.generativeai: {e}"
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

    def _extract_text_from_pdf(self, pdf_path: pathlib.Path) -> str | None:
        """Extract text from PDF using PyMuPDF (fitz)"""
        if not fitz:
            logging.error("PyMuPDF (fitz) not available for text extraction")
            return None
        
        try:
            doc = fitz.open(str(pdf_path))
            full_text = ""
            page_count = len(doc)
            
            for page_num in range(page_count):
                page = doc.load_page(page_num)
                text = page.get_text()
                full_text += f"\n--- PÁGINA {page_num + 1} ---\n{text}\n"
            
            doc.close()
            logging.info(f"Successfully extracted text from {pdf_path.name} ({page_count} pages)")
            return full_text
            
        except Exception as e:
            logging.error(f"Error extracting text from PDF {pdf_path.name}: {e}")
            if 'doc' in locals():
                try:
                    doc.close()
                except:
                    pass
            return None

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

        final_extracted_data = None

        if not self.gemini_configured:
            logging.warning(
                f"Skipping real Gemini API call for {pdf_path.name} (Gemini not configured or API key missing). Returning dummy data structure."
            )
            # Dummy data structure as a fallback
            final_extracted_data = {
                "file_name_source": pdf_path.name,
                "extraction_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
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
            
            # Extract text from PDF locally first
            pdf_text = self._extract_text_from_pdf(pdf_path)
            if not pdf_text:
                logging.error(f"Failed to extract text from {pdf_path.name}")
                final_extracted_data = None
            else:
                # Save extracted text for debugging
                text_debug_dir = output_json_dir.parent / "extracted_text"
                text_debug_dir.mkdir(exist_ok=True)
                text_file_path = text_debug_dir / f"{pdf_path.stem}_extracted_text.txt"
                
                try:
                    with open(text_file_path, "w", encoding="utf-8") as f:
                        f.write(pdf_text)
                    logging.info(f"Saved extracted text to: {text_file_path}")
                except Exception as e:
                    logging.warning(f"Failed to save extracted text: {e}")
                
                try:
                    logging.info(f"Extracted text from {pdf_path.name}, sending to Gemini...")

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
        "data": "YYYY-MM-DD"
    }
]

REGRAS OBRIGATÓRIAS:
- Retorne SEMPRE um array JSON válido, nunca texto explicativo
- Se não encontrar decisões com resultado, retorne: []
- Processe decisões como "RECURSO PROVIDO", "SENTENÇA CONFIRMADA", "SENTENÇA PROCEDENTE", etc.
- Ignore despachos que apenas movimentam processos
- Número CNJ quando disponível, senão use o número encontrado
- Procure por textos como: "Decisão:", "Decisão Monocrática:", "À UNANIMIDADE", etc."""

                    model = genai.GenerativeModel("gemini-2.5-flash-lite-preview-06-17")
                    logging.info(
                        f"Generating content for {pdf_path.name} using 'gemini-2.5-flash-lite-preview-06-17'..."
                    )
                    
                    # Combine prompt with extracted text
                    full_prompt = f"{prompt}\n\nTexto extraído do PDF:\n{pdf_text}"
                    response = model.generate_content(full_prompt)

                    logging.info(f"Response received from Gemini for {pdf_path.name}.")

                    try:
                        # Clean up response text by removing markdown if present
                        clean_response = response.text.strip()
                        if clean_response.startswith("```json"):
                            clean_response = clean_response.replace("```json", "").replace("```", "").strip()
                        elif clean_response.startswith("```"):
                            clean_response = clean_response.replace("```", "").strip()
                        
                        extracted_data_from_api = json.loads(clean_response)

                        # Add common metadata
                        if isinstance(extracted_data_from_api, list):
                            # If it's a list of decisions, wrap it with metadata
                            final_extracted_data = {
                                "file_name_source": pdf_path.name,
                                "extraction_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                "decisions": extracted_data_from_api,
                            }
                        elif isinstance(extracted_data_from_api, dict):
                            # If it's a single decision object, treat as single item array
                            extracted_data_from_api["file_name_source"] = pdf_path.name
                            extracted_data_from_api["extraction_timestamp"] = (
                                datetime.datetime.now(datetime.timezone.utc).isoformat()
                            )
                            final_extracted_data = extracted_data_from_api
                        else:
                            logging.error(
                                f"Gemini response for {pdf_path.name} was not a JSON dict or list: {type(extracted_data_from_api)}"
                            )
                            final_extracted_data = None

                    except json.JSONDecodeError as je:
                        logging.warning(
                            f"Gemini returned non-JSON response for {pdf_path.name}. Response: {response.text[:200]}..."
                        )
                        # If Gemini responded but not in JSON, assume no decisions found
                        final_extracted_data = {
                            "file_name_source": pdf_path.name,
                            "extraction_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                            "decisions": [],
                            "gemini_response": response.text[:500]  # Keep first 500 chars for debugging
                        }

                except Exception as e:
                    logging.error(
                        f"Error during Gemini API call or processing for {pdf_path.name}: {e}"
                    )
                    final_extracted_data = None  # Ensure it's None if any step failed

        if final_extracted_data is None:
            logging.warning(
                f"No data extracted or error occurred for {pdf_path.name}. JSON file will not be saved."
            )
            return None

        # Determine filename based on extracted data if possible
        process_number_to_use = "unknown_process"
        if (
            isinstance(final_extracted_data, dict)
            and "decisions" in final_extracted_data
            and isinstance(final_extracted_data["decisions"], list)
            and len(final_extracted_data["decisions"]) > 0
            and "numero_processo" in final_extracted_data["decisions"][0]
        ):
            process_number_to_use = final_extracted_data["decisions"][0]["numero_processo"]
        elif (
            isinstance(final_extracted_data, dict)
            and "numero_processo" in final_extracted_data
        ):
            process_number_to_use = final_extracted_data["numero_processo"]
        else:  # Fallback if numero_processo is not found or if it's an empty array
            process_number_to_use = f"{pdf_path.stem}_extraction"

        sanitized_filename_base = self._sanitize_filename(process_number_to_use)
        json_filename = f"{sanitized_filename_base}.json"
        output_json_path = output_json_dir / json_filename

        try:
            with open(output_json_path, "w", encoding="utf-8") as f:
                json.dump(final_extracted_data, f, ensure_ascii=False, indent=4)
            logging.info(f"Successfully saved extracted data to: {output_json_path}")
            return output_json_path
        except IOError as e:
            logging.error(f"Error saving JSON file {output_json_path}: {e}")
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
        default=pathlib.Path(__file__).resolve().parent.parent / "data" / "json",
        help="Directory to save the extracted JSON file. Defaults to causaganha/data/json/",
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
    dummy_pdf_dir = pathlib.Path(__file__).resolve().parent.parent / "data" / "diarios"
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
        except Exception as e:
            logging.error(
                f"Could not create dummy PDF: {e}. Falling back to simple text file."
            )
            with open(cli_test_pdf, "w") as f:
                f.write("Fallback dummy PDF content.")
            logging.info(
                f"Created super-basic dummy PDF (text file) for CLI testing: {cli_test_pdf}"
            )

    # To run main: python causaganha/core/extractor.py --pdf_file causaganha/data/diarios/cli_test_doc_for_extractor.pdf
    # Ensure GEMINI_API_KEY is set in your environment if you want to test real API calls.
    main()
