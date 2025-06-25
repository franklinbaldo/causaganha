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
                "extraction_timestamp": datetime.datetime.utcnow().isoformat() + "Z",
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
            uploaded_file_object = None
            try:
                logging.info(f"Uploading {pdf_path.name} to Gemini...")
                uploaded_file_object = genai.upload_file(
                    path=str(pdf_path),
                    mime_type="application/pdf",
                )
                logging.info(
                    f"Successfully uploaded {pdf_path.name} as {uploaded_file_object.name}"
                )

                prompt = """Analise este PDF do Diário da Justiça e extraia APENAS decisões judiciais.
Para cada decisão encontrada, retorne JSON com:
{
    "numero_processo": "formato CNJ",
    "tipo_decisao": "sentença|acórdão|despacho",
    "partes": {
        "requerente": ["nome1", "nome2"],
        "requerido": ["nome1", "nome2"]
    },
    "advogados": {
        "requerente": ["Nome (OAB/UF)", ...],
        "requerido": ["Nome (OAB/UF)", ...]
    },
    "resultado": "procedente|improcedente|parcialmente_procedente|extinto",
    "data_decisao": "YYYY-MM-DD"
}
Se múltiplas decisões forem encontradas, retorne uma lista de JSONs.
Se nenhuma decisão for encontrada, retorne um JSON vazio: {}.
Não inclua markdown (```json ... ```) na sua resposta."""

                model = genai.GenerativeModel("gemini-1.5-flash")
                logging.info(
                    f"Generating content for {pdf_path.name} using 'gemini-1.5-flash'..."
                )
                response = model.generate_content([prompt, uploaded_file_object])

                logging.info(f"Response received from Gemini for {pdf_path.name}.")

                try:
                    extracted_data_from_api = json.loads(response.text)

                    # Add common metadata
                    if isinstance(extracted_data_from_api, list):
                        # If it's a list of decisions, wrap it or decide how to store metadata
                        # For now, creating a wrapper object
                        final_extracted_data = {
                            "file_name_source": pdf_path.name,
                            "extraction_timestamp": datetime.datetime.utcnow().isoformat()
                            + "Z",
                            "decisions": extracted_data_from_api,
                        }
                    elif isinstance(extracted_data_from_api, dict):
                        # If it's a single decision object
                        extracted_data_from_api["file_name_source"] = pdf_path.name
                        extracted_data_from_api["extraction_timestamp"] = (
                            datetime.datetime.utcnow().isoformat() + "Z"
                        )
                        final_extracted_data = extracted_data_from_api
                    else:
                        logging.error(
                            f"Gemini response for {pdf_path.name} was not a JSON dict or list: {type(extracted_data_from_api)}"
                        )
                        final_extracted_data = None  # Or some error structure

                except json.JSONDecodeError as je:
                    logging.error(
                        f"Failed to parse JSON response from Gemini for {pdf_path.name}: {je}"
                    )
                    logging.debug(
                        f"Gemini raw response text for {pdf_path.name}: {response.text[:500]}..."
                    )  # Log snippet
                    final_extracted_data = None

            except Exception as e:
                logging.error(
                    f"Error during Gemini API call or processing for {pdf_path.name}: {e}"
                )
                final_extracted_data = None  # Ensure it's None if any step failed
            finally:
                if uploaded_file_object:
                    try:
                        logging.info(
                            f"Deleting uploaded file {uploaded_file_object.name} from Gemini."
                        )
                        genai.delete_file(uploaded_file_object.name)
                        logging.info(
                            f"Successfully deleted file {uploaded_file_object.name}."
                        )
                    except Exception as e_del:
                        logging.error(
                            f"Error deleting file {uploaded_file_object.name} from Gemini: {e_del}"
                        )

        if final_extracted_data is None:
            logging.warning(
                f"No data extracted or error occurred for {pdf_path.name}. JSON file will not be saved."
            )
            return None

        # Determine filename based on extracted data if possible
        # This part might need adjustment based on how multiple decisions are handled.
        # If it's a list, we might use the first decision's number or a generic name.
        process_number_to_use = "unknown_process"
        if (
            isinstance(final_extracted_data, dict)
            and "numero_processo" in final_extracted_data
        ):
            process_number_to_use = final_extracted_data["numero_processo"]
        elif (
            isinstance(final_extracted_data, dict)
            and "decisions" in final_extracted_data
            and isinstance(final_extracted_data["decisions"], list)
            and len(final_extracted_data["decisions"]) > 0
            and "numero_processo" in final_extracted_data["decisions"][0]
        ):
            process_number_to_use = final_extracted_data["decisions"][0][
                "numero_processo"
            ]
        else:  # Fallback if numero_processo is not easily found or if it's an empty dict {}
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
