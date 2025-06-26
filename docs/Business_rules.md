# Business Rules for CausaGanha

## Introduction

This document outlines the business rules that govern the operation of the CausaGanha system. These rules define how data is acquired, processed, analyzed, and how lawyer performance is evaluated using the OpenSkill rating system. They are derived from the system's design, documentation, and codebase.

## I. Data Acquisition & Scope

1.  **Primary Data Source:** The sole source of legal documents for analysis is the electronic Diário da Justiça (Official Gazette) of the Tribunal de Justiça de Rondônia (TJRO).
2.  **Document Format:** Input documents are exclusively in PDF format.
3.  **Collection Cadence:** PDFs are intended to be collected daily, corresponding to their publication date.
4.  **Optional PDF Backup:** Downloaded PDFs may be backed up to a designated Google Drive folder if the system is configured to do so.

## II. Information Extraction (LLM-based)

1.  **Extraction Engine:** Google's Gemini Large Language Model (LLM) is the designated engine for extracting structured information from PDF documents.
2.  **Targeted Information per Decision:** For each judicial decision identified within a PDF, the system must attempt to extract the following key data points:
    *   `numero_processo`: Case number, expected in Conselho Nacional de Justiça (CNJ) format (e.g., "NNNNNNN-DD.YYYY.J.TR.OOOO").
    *   `tipo_decisao`: Type of decision (e.g., "sentença", "acórdão").
    *   `polo_ativo`: Name(s) of the plaintiff(s) or appellant(s).
    *   `advogados_polo_ativo`: Lawyer(s) for the plaintiff/appellant, ideally in "Name (OAB/UF)" format.
    *   `polo_passivo`: Name(s) of the defendant(s) or appellee(s).
    *   `advogados_polo_passivo`: Lawyer(s) for the defendant/appellee, ideally in "Name (OAB/UF)" format.
    *   `resultado`: The outcome of the decision (e.g., "procedente", "improcedente", "provido", "negado_provimento").
    *   `data`: The date the decision was made, in "YYYY-MM-DD" format (corresponds to `data_decisao` in some contexts).
    *   `resumo`: A brief summary of the decision (max 250 characters).
3.  **Handling Multiple Decisions per PDF:** A single PDF from the Diário da Justiça may contain multiple distinct judicial decisions. The extraction process is designed to identify all such decisions, and the system processes each one individually for potential OpenSkill rating.
4.  **Extraction Fallback (Gemini Configuration Issue):** If the Gemini LLM is not properly configured (e.g., due to a missing API key), the extractor will produce a dummy JSON structure, which will likely fail validation or result in no processable matches.

## III. Data Validation & Normalization

1.  **Decision Validation Criteria:** An extracted decision is considered valid and eligible for further processing (including OpenSkill rating) only if it meets *all* of the following criteria:
    *   The decision data itself must be a structured dictionary (JSON object).
    *   `numero_processo` (case number):
        *   Must be present and not empty.
        *   Must be a string.
        *   Must conform to the expected structural pattern (typically `[\d.-]{15,25}`).
    *   `polo_ativo` (plaintiff/appellant names):
        *   Must be present and contain at least one non-empty name (either as a direct string or as a list containing at least one non-empty string).
    *   `polo_passivo` (defendant/appellee names):
        *   Must be present and contain at least one non-empty name (either as a direct string or as a list containing at least one non-empty string).
    *   `resultado` (outcome):
        *   Must be present and not empty.
        *   Must be a string.
    *   (Note: `advogados_polo_ativo` and `advogados_polo_passivo` are checked later in the pipeline before a match is processed, not strictly by `validate_decision` itself, but are essential for rating.)
2.  **Handling of Invalid Decisions:** Decisions that fail any of the above validation criteria are logged with the specific reason for invalidity. These decisions are then skipped and do not proceed to the OpenSkill rating stage or contribute to any lawyer's performance metrics.
3.  **Lawyer Name Normalization & Identification:**
    *   Lawyer names extracted from decisions undergo a standardized normalization process before being used as identifiers (`advogado_id`):
        *   Conversion to lowercase.
        *   Iterative removal of common professional titles (e.g., "Dr.", "Dra.", "Doutor", "Doutora").
        *   Normalization of accented characters to their basic Latin equivalents (e.g., "José" becomes "Jose").
        *   Standardization of whitespace: multiple spaces are reduced to a single space, and leading/trailing whitespace is removed.
    *   The resulting normalized name serves as the unique identifier (`advogado_id`) for a lawyer in the system.

## IV. OpenSkill Rating System & Match Processing

1.  **Core Rating System:** The OpenSkill rating system is employed to dynamically assess and rank lawyer performance based on the outcomes of their processed legal cases. OpenSkill natively supports matches between teams of varying sizes.
2.  **Basis of an OpenSkill "Match":** Each valid judicial decision that has successfully passed data validation and contains identifiable lawyers for both `advogados_polo_ativo` and `advogados_polo_passivo` constitutes a single "match" for OpenSkill calculation purposes.
3.  **Team Formation for Matches:** For each match:
    *   Team A consists of all unique, normalized lawyer IDs from the `advogados_polo_ativo` list.
    *   Team B consists of all unique, normalized lawyer IDs from the `advogados_polo_passivo` list.
4.  **Exclusion - Missing Lawyer Teams:** If, after extraction and validation, either Team A or Team B is empty (i.e., no valid lawyer IDs could be identified for that side of the case), the decision is skipped for OpenSkill rating.
5.  **Exclusion - Identical Teams:** If, after normalization, Team A and Team B are identical (contain the exact same set of lawyer IDs), the match is skipped to prevent lawyers from playing against themselves in the same capacity.
6.  **Match Outcome Determination:** The outcome of the match is determined from the `resultado` field of the decision, translated into an OpenSkill context (e.g., "win_a" if polo ativo wins, "win_b" if polo passivo wins, "draw" otherwise):
    *   `resultado` values like "procedente", "provido", "confirmada" typically map to a win for Team A (`win_a`).
    *   `resultado` values like "improcedente", "negado_provimento", "reformada" typically map to a win for Team B (`win_b`).
    *   Other `resultado` values like "parcialmente procedente", "extinto" or unrecognized values are treated as a Draw (`draw`). (Note: "parcialmente procedente" could be mapped to a partial win if specific logic is implemented in the pipeline).
7.  **OpenSkill Environment Parameters:** The OpenSkill environment (specifically, the PlackettLuce model used) is configured with specific parameters:
    *   `mu`: The initial average skill rating for new lawyers.
    *   `sigma`: The initial uncertainty (standard deviation) of a lawyer's skill.
    *   `beta`: The variance of player performance, influencing how much skill difference is needed for a likely win.
    *   `tau`: A dynamic factor representing the volatility of skill over time. This parameter can also be adjusted per-match for partial outcomes.
    *   These parameters are configurable via the `[openskill]` section in the `config.toml` file located in the project root.
8.  **Rating Update Mechanism:** Following each match, the OpenSkill ratings (`mu` and `sigma`) of all participating lawyers in both Team A and Team B are updated based on the match outcome and their prior ratings, using the configured OpenSkill model. The total number of matches played (`total_partidas`) for each participating lawyer is also incremented by one.

## V. Data Storage & Management

1.  **Lawyer Ratings Storage:** Current OpenSkill ratings (`mu`, `sigma`) and the total number of matches played (`total_partidas`) for every lawyer are stored in a CSV file located at `data/ratings.csv` (relative to project root if `src/` layout is adopted, otherwise `causaganha/data/ratings.csv`). This file uses the normalized lawyer name as `advogado_id` and is typically sorted by `mu` in descending order.
2.  **Match History Storage:** A detailed historical log of all processed OpenSkill matches is maintained in a CSV file at `data/partidas.csv` (or `causaganha/data/partidas.csv`). Each record in this file includes:
    *   `data_partida`: Date of the match (derived from the `data` field of the judicial decision).
    *   `equipe_a_ids`: Comma-separated string of normalized lawyer IDs for Team A.
    *   `equipe_b_ids`: Comma-separated string of normalized lawyer IDs for Team B.
    *   `ratings_equipe_a_antes`: JSON string representing a dictionary of {adv_id: [mu, sigma]} for Team A before the match.
    *   `ratings_equipe_b_antes`: JSON string representing a dictionary of {adv_id: [mu, sigma]} for Team B before the match.
    *   `resultado_partida`: The OpenSkill outcome of the match (e.g., "win_a", "win_b", "draw", "partial_a", "partial_b").
    *   `ratings_equipe_a_depois`: JSON string representing a dictionary of {adv_id: [mu, sigma]} for Team A after the match.
    *   `ratings_equipe_b_depois`: JSON string representing a dictionary of {adv_id: [mu, sigma]} for Team B after the match.
    *   `numero_processo`: The case number associated with this match.
3.  **Processed JSON Archival:** Original JSON files (extracted from PDFs) located in `data/json/` (or `causaganha/data/json/`) that result in at least one valid OpenSkill match being successfully processed are moved to an archive directory: `data/json_processed/` (or `causaganha/data/json_processed/`).
4.  **Unprocessed/Skipped JSON Handling:** JSON files that do not yield any valid OpenSkill matches (e.g., if all decisions within are invalid, or all lack necessary lawyer information for pairing) remain in the `data/json/` (or `causaganha/data/json/`) directory and are not moved to the processed archive.

## VI. System Operation & Automation

1.  **Pipeline Execution Model:** The CausaGanha system operates based on a defined Extract, Transform, Load (ETL)-like pipeline, executed in the following sequence of commands:
    *   `collect`: Downloads the PDF documents.
    *   `extract`: Extracts structured data from PDFs into JSON files.
    *   `update`: Processes the JSON files to update OpenSkill ratings and match history.
    *   `run`: Executes the `collect`, `extract`, and `update` stages sequentially for a given date.
2.  **Automation:** The entire pipeline is designed for automated daily execution using GitHub Actions workflows, ensuring regular updates to the lawyer OpenSkill ratings.
3.  **Dry Run Capability:** All major pipeline commands (`collect`, `extract`, `update`, `run`) support a "dry run" operational mode. When activated, this mode simulates the command's actions (e.g., downloads, API calls, file modifications, database updates) and logs what would have happened, but does not make any actual changes to data or external systems. This is used for testing, validation, and safe preview of operations.
