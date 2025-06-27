# Refactoring the Archive Command & Adopting a Single Master Internet Archive Identifier with Incremental Metadata

## 1. Motivation

The current command-line interface (`cli.py`) has multiple ways to archive judicial gazettes (diários) to the Internet Archive (IA), leading to inconsistencies and complexity. This refactor aims to:

*   **Simplify the CLI:** Provide a clear, unified way for direct and batch archiving.
*   **Standardize IA Strategy:** Adopt a **single master IA identifier** (e.g., `causaganha_diarios_collection`) to host all diários from all tribunals. Individual diários will be files organized under tribunal-specific paths within this single IA item. This strategy maximizes collection coherence, simplifies backup/mirroring via a single torrent, and allows users to perform partial downloads if desired.
*   **Enable Rich, Incremental Metadata:** Allow metadata on IA to be augmented as diários are processed through different pipeline stages (e.g., after NLP analysis).
*   **Ensure Consistent Archiving:** All diários archived via the CLI will follow this single master IA item model.
*   **Centralize Logic:** Consolidate archiving logic for better maintainability.

The `ia upload` CLI tool is robust, handling aspects like upload retries, which simplifies the application's responsibility regarding the upload queue for individual files to an IA item.

## 2. Proposed Changes: Single Master IA Identifier & Incremental Metadata

The core change is to use **one single master IA item for all tribunals**. Each diário PDF will be a uniquely named file under a path representing its tribunal. Metadata will be added incrementally, especially after analysis.

### 2.1. Internet Archive (IA) Interaction Model

*   **Master IA Item Identifier:** A single, standardized identifier for the entire collection, e.g., `causaganha_diarios_collection` (configurable).
*   **File Upload & Path Structure:** New diários are added as files to the master IA item, organized by paths.
    `ia upload <master_ia_item_id> <local_filepath_to_pdf> --remote-name "<tribunal_code>/<pdf_filename_on_ia>"`
    *   Example: `ia upload causaganha_diarios_collection path/to/tjro_2023.pdf --remote-name "tjro/tjro_diario_2023-01-15.pdf"`
*   **Item Creation:** The first diário uploaded creates the master IA item with initial general metadata.
*   **Metadata Handling:**
    *   **Item-Level Metadata (Master Item):** General metadata (e.g., `collection:opensource`, `mediatype:texts`, `creator: CausaGanha`, `title: CausaGanha - Coleção de Diários Oficiais Judiciais`). Set on item creation and can be updated.
    *   **File-Specific Basic Metadata (Local DB):** The `job_queue` table in the local database is the primary store for essential per-diário metadata (publication date, original URL, SHA256, tribunal, path within IA).
    *   **Incremental/Derived Metadata (File-Level on IA via Summary File):**
        *   After stages like NLP analysis (e.g., Gemini), extracted information for each diário (e.g., number of decisions, key topics) will be used to update a dedicated JSON metadata file within the master IA item (e.g., `file_level_metadata.json` or `analysis_summary.json`).
        *   This JSON file will map individual diário paths (e.g., `tjro/tjro_diario_2023-01-15.pdf`) to their respective rich metadata objects.
        *   The `analyze` pipeline stage will be responsible for fetching this summary JSON, updating it with new results, and re-uploading it to the master IA item. This keeps the IA item's metadata progressively richer.

### 2.2. Database Changes (`job_queue` Table)

*   `url` (TEXT): Original URL.
*   `date` (DATE): Publication date.
*   `tribunal` (TEXT): Tribunal code (e.g., 'tjro').
*   `filename` (TEXT): Temporary local filename.
*   `ia_identifier` (TEXT): **Stores the single master IA item ID** (e.g., `causaganha_diarios_collection`).
*   `ia_remote_filename` (TEXT): Full path within the master IA item (e.g., `tjro/tjro_diario_2023-01-15.pdf`).
*   `metadata` (JSON): Stores *initial* or operational metadata for the individual diário.
*   `analyze_result` (JSON): Stores the structured output from the analysis stage (e.g., Gemini results). This data will be used to update the `file_level_metadata.json` on IA.
*   `status` (TEXT): Tracks processing (`queued`, `archived`, `analyzed`, `ia_metadata_updated`, `scored`). 'Archived' means PDF is on IA. 'ia_metadata_updated' could signify its analysis results are reflected in the IA summary metadata file.
*   Other existing columns remain relevant.

**SQL (Conceptual for `job_queue`):**
No schema changes are strictly needed if `analyze_result` already exists and can hold the Gemini output. The change is in how this data is then propagated to IA. We might add a status like `ia_metadata_synced BOOLEAN DEFAULT FALSE`.

### 2.3. `src/cli.py` Modifications

#### A. Archiving Helper Functions

*   `async def execute_ia_upload(...)`: As previously defined, for uploading files.
*   `async def archive_diario_to_master_item(...)`: As previously defined, for archiving a single diário PDF.
*   `async def update_ia_file_level_metadata_summary(master_ia_id: str, new_analysis_data: Dict[str, Any], file_remote_path: str)`:
    1.  Downloads the current `file_level_metadata.json` from the `master_ia_id` (if it exists).
    2.  Parses it (or initializes an empty dictionary).
    3.  Adds/updates the entry for `file_remote_path` with `new_analysis_data`.
    4.  Uploads the modified `file_level_metadata.json` back to the `master_ia_id`.

#### B. `get-urls` Command

*   Unchanged from the previous revision of this document (adds `--archive-now` for direct archiving to master item). When a file is directly archived, its analysis metadata isn't available yet, so no update to `file_level_metadata.json` happens at this stage.

#### C. Removal of `archive` Typer Command

*   Remains removed.

#### D. `pipeline` Command Stages

*   **Archive Stage:**
    *   Processes 'queued' items from `job_queue`.
    *   Calls `archive_diario_to_master_item` for each.
    *   Updates `job_queue` status to 'archived', populates `ia_identifier` and `ia_remote_filename`.
*   **Analyze Stage:**
    *   Processes 'archived' items (or those not yet 'analyzed').
    *   Downloads PDF from master IA item using `ia_identifier` and `ia_remote_filename`.
    *   Performs analysis (e.g., Gemini).
    *   Stores detailed analysis results in `job_queue.analyze_result`.
    *   **NEW SUB-STEP:** Calls `update_ia_file_level_metadata_summary` to update the JSON summary on IA with the new analysis data from `analyze_result`.
    *   Updates `job_queue` status to 'analyzed' (or 'ia_metadata_updated').
*   **Score Stage:** Operates on data from `job_queue` (presumably after analysis).

#### E. `analyze` Command (Standalone)

*   If run standalone, after local analysis results are stored, it should also perform the "NEW SUB-STEP" described above: call `update_ia_file_level_metadata_summary`.

### 2.4. Impact on `src/tribunais/tjro/collect_and_archive.py`

*   Remains deprecated for CLI-initiated archiving.

## 3. Benefits

*   **Single Master IA Item:** As per previous revision (torrents, simplified management).
*   **Rich, Evolving IA Presence:** The `file_level_metadata.json` within the IA item becomes a rich, queryable (by downloading and parsing it) source of information about the diários, updated as they are processed.
*   **Decoupling:** PDF archival is separated from full metadata generation, allowing for faster initial archival.

## 4. Challenges and Considerations

*   **Concurrency for Metadata Summary File:** If multiple `analyze` processes run in parallel, they could race to update the `file_level_metadata.json` on IA. A locking mechanism or a queue for updates to this specific file might be needed if high parallelism is expected for the analysis/IA metadata update step. Simpler first approach: pipeline processes this step serially or in a way that updates are batched.
*   **Size of Metadata Summary File:** For a very large number of diários, this JSON file could become large. IA handles large files, but it's a consideration for clients downloading/parsing it.
*   Other challenges as per previous revision (master item management, filename uniqueness, local DB importance, migration).

## 5. Summary of User Workflow Changes

*   Largely the same as the previous revision. The incremental metadata update is an internal enhancement to the `analyze` stage of the `pipeline` or standalone `analyze` command.

This approach balances the desire for a unified IA item with the need for rich, evolving, file-specific metadata by leveraging a summary file within the IA item itself, updated by the application's pipeline.
