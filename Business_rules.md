# Business Rules for CausaGanha

## Introduction

This document outlines the business rules that govern the operation of the CausaGanha system. These rules define how data is acquired, processed, analyzed, and how lawyer performance is evaluated using the Elo rating system. They are derived from the system's design, documentation, and codebase.

## I. Data Acquisition & Scope

1.  **Primary Data Source:** The sole source of legal documents for analysis is the electronic Diário da Justiça (Official Gazette) of the Tribunal de Justiça de Rondônia (TJRO).
2.  **Document Format:** Input documents are exclusively in PDF format.
3.  **Collection Cadence:** PDFs are intended to be collected daily, corresponding to their publication date.
4.  **Optional PDF Backup:** Downloaded PDFs may be backed up to a designated Google Drive folder if the system is configured to do so.

## II. Information Extraction (LLM-based)

1.  **Extraction Engine:** Google's Gemini Large Language Model (LLM) is the designated engine for extracting structured information from PDF documents.
2.  **Targeted Information per Decision:** For each judicial decision identified within a PDF, the system must attempt to extract the following key data points:
    *   `numero_processo`: Case number, expected in Conselho Nacional de Justiça (CNJ) format (e.g., "NNNNNNN-DD.YYYY.J.TR.OOOO").
    *   `tipo_decisao`: Type of decision (e.g., "sentença", "acórdão", "despacho" - translating to sentence, judgment, order).
    *   `partes`: Parties involved in the case:
        *   `requerente`: Plaintiff(s) or applicant(s).
        *   `requerido`: Defendant(s) or respondent(s).
    *   `advogados`: Lawyers representing the parties:
        *   `requerente`: Lawyer(s) for the plaintiff, ideally in "Name (OAB/UF)" format (OAB is the Brazilian Bar Association, UF is the state).
        *   `requerido`: Lawyer(s) for the defendant, ideally in "Name (OAB/UF)" format.
    *   `resultado`: The outcome of the decision (e.g., "procedente" - granted, "improcedente" - denied, "extinto" - dismissed).
    *   `data_decisao`: The date the decision was made, in "YYYY-MM-DD" format.
3.  **Handling Multiple Decisions per PDF:** A single PDF from the Diário da Justiça may contain multiple distinct judicial decisions. The extraction process is designed to identify all such decisions, and the system processes each one individually for potential Elo rating.
4.  **Extraction Fallback (Gemini Configuration Issue):** If the Gemini LLM is not properly configured (e.g., due to a missing API key), the system will generate a dummy JSON record with predefined placeholder values for that PDF. This allows the processing pipeline to continue but results in non-authentic, placeholder data for that specific document.

## III. Data Validation & Normalization

1.  **Decision Validation Criteria:** An extracted decision is considered valid and eligible for further processing (including Elo rating) only if it meets *all* of the following criteria:
    *   The decision data itself must be a structured dictionary (JSON object).
    *   `numero_processo` (case number):
        *   Must be present and not empty.
        *   Must be a string.
        *   Must conform to the expected structural pattern (typically `[\d.-]{15,25}` which is a flexible match for CNJ-like numbers).
    *   `partes` (parties involved):
        *   Must be present and be a dictionary.
        *   `partes.requerente` (plaintiff): Must be present and contain at least one non-empty name (either as a direct string or as a list containing at least one non-empty string).
        *   `partes.requerido` (defendant): Must be present and contain at least one non-empty name (either as a direct string or as a list containing at least one non-empty string).
    *   `resultado` (outcome):
        *   Must be present and not empty.
        *   Must be a string.
2.  **Handling of Invalid Decisions:** Decisions that fail any of the above validation criteria are logged with the specific reason for invalidity. These decisions are then skipped and do not proceed to the Elo rating stage or contribute to any lawyer's performance metrics.
3.  **Lawyer Name Normalization & Identification:**
    *   Lawyer names extracted from decisions undergo a standardized normalization process before being used as identifiers (`advogado_id`):
        *   Conversion to lowercase.
        *   Iterative removal of common professional titles (e.g., "Dr.", "Dra.", "Doutor", "Doutora").
        *   Normalization of accented characters to their basic Latin equivalents (e.g., "José" becomes "Jose").
        *   Standardization of whitespace: multiple spaces are reduced to a single space, and leading/trailing whitespace is removed.
    *   The resulting normalized name serves as the unique identifier (`advogado_id`) for a lawyer in the system.

## IV. Elo Rating System & Match Processing

1.  **Core Rating System:** The Elo rating system is employed to dynamically assess and rank lawyer performance based on the outcomes of their processed legal cases.
2.  **Basis of an Elo "Match":** Each valid judicial decision that has successfully passed data validation and contains identifiable lawyers for both the plaintiff and the defendant constitutes a single "match" for Elo calculation purposes.
3.  **Lawyer Pairing for Matches:** For each match:
    *   Player A is defined as the **first lawyer listed** in the `advogados.requerente` (plaintiff's lawyers) array.
    *   Player B is defined as the **first lawyer listed** in the `advogados.requerido` (defendant's lawyers) array.
4.  **Exclusion - Missing Lawyers:** If, after extraction and validation, either the plaintiff's lawyer (Player A) or the defendant's lawyer (Player B) cannot be identified from the decision data (e.g., the respective lawyer list is empty or missing), the decision is skipped for Elo rating.
5.  **Exclusion - Unidentifiable (Empty Normalized) Lawyers:** If the normalization process for either Player A's or Player B's name results in an empty string, that specific decision is skipped for Elo rating.
6.  **Exclusion - Self-Representation or Same Lawyer:** If the normalized `advogado_id` of Player A is identical to that of Player B (indicating the same lawyer is listed for both parties), the match is skipped for Elo rating to prevent a lawyer from playing against themselves.
7.  **Match Outcome Determination (Score for Player A - Plaintiff's Lawyer):** The `score_a` variable, representing Player A's score in the Elo calculation, is determined as follows based on the `resultado` field of the decision:
    *   `resultado` = "procedente" (plaintiff's case fully granted): `score_a = 1.0` (Win for Player A).
    *   `resultado` = "improcedente" (plaintiff's case denied, defendant wins): `score_a = 0.0` (Loss for Player A).
    *   `resultado` = "parcialmente procedente", "parcialmente_procedente" (partially granted), "extinto sem resolução de mérito" (dismissed without prejudice), "extinto" (dismissed): `score_a = 0.5` (Draw).
    *   Any other value for `resultado`: Treated as a Draw, `score_a = 0.5`, and a warning is logged by the system.
8.  **Default Elo Rating:** Lawyers encountered by the system for the first time (i.e., not yet present in the ratings database) are assigned a default starting Elo rating of 1500.0.
9.  **K-Factor:** A fixed K-factor of 16 is used in all Elo rating update calculations. This factor determines the maximum possible rating change from a single match.
10. **Rating Update Mechanism:** Following each match, the Elo ratings of both participating lawyers (Player A and Player B) are updated based on the match outcome and their prior ratings. The total number of matches played (`total_partidas`) for each participating lawyer is also incremented by one.

## V. Data Storage & Management

1.  **Lawyer Ratings Storage:** Current Elo ratings and the total number of matches played for every lawyer are stored in a CSV file located at `causaganha/data/ratings.csv`. This file uses the normalized lawyer name as `advogado_id`. The file is typically sorted by Elo rating in descending order.
2.  **Match History Storage:** A detailed historical log of all processed Elo matches is maintained in a CSV file at `causaganha/data/partidas.csv`. Each record in this file includes:
    *   `data_partida`: Date of the match (derived from the `data_decisao` of the judicial decision).
    *   `advogado_a_id`: Normalized ID of Player A (plaintiff's lawyer).
    *   `advogado_b_id`: Normalized ID of Player B (defendant's lawyer).
    *   `rating_advogado_a_antes`: Elo rating of Player A before this match.
    *   `rating_advogado_b_antes`: Elo rating of Player B before this match.
    *   `score_a`: The score achieved by Player A in this match (1.0, 0.5, or 0.0).
    *   `rating_advogado_a_depois`: Elo rating of Player A after this match.
    *   `rating_advogado_b_depois`: Elo rating of Player B after this match.
    *   `numero_processo`: The case number associated with this match.
3.  **Processed JSON Archival:** Original JSON files (extracted from PDFs) located in `causaganha/data/json/` that result in at least one valid Elo match being successfully processed are moved to an archive directory: `causaganha/data/json_processed/`.
4.  **Unprocessed/Skipped JSON Handling:** JSON files that do not yield any valid Elo matches (e.g., if all decisions within are invalid, or all lack necessary lawyer information for pairing) remain in the `causaganha/data/json/` directory and are not moved to the processed archive.

## VI. System Operation & Automation

1.  **Pipeline Execution Model:** The CausaGanha system operates based on a defined Extract, Transform, Load (ETL)-like pipeline, executed in the following sequence of commands:
    *   `collect`: Downloads the PDF documents.
    *   `extract`: Extracts structured data from PDFs into JSON files.
    *   `update`: Processes the JSON files to update Elo ratings and match history.
    *   `run`: Executes the `collect`, `extract`, and `update` stages sequentially for a given date.
2.  **Automation:** The entire pipeline is designed for automated daily execution using GitHub Actions workflows, ensuring regular updates to the lawyer ratings.
3.  **Dry Run Capability:** All major pipeline commands (`collect`, `extract`, `update`, `run`) support a "dry run" operational mode. When activated, this mode simulates the command's actions (e.g., downloads, API calls, file modifications, database updates) and logs what would have happened, but does not make any actual changes to data or external systems. This is used for testing, validation, and safe preview of operations.
