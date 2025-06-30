# Documentation: [Tribunal Name/Abbreviation] Adapter

This document provides details for the CausaGanha adapter for the [Tribunal Name] ([Abbreviation], e.g., TJRO).

## 1. Overview

-   **Tribunal Full Name**: [e.g., Tribunal de Justiça do Estado de Rondônia]
-   **Abbreviation Used in System**: [e.g., `tjro`]
-   **Website**: [Link to the main tribunal website]
-   **Diario Publication Page(s)**: [Direct link(s) to where official diaries are published/listed]
-   **Developer(s)**: [Your Name/Team]
-   **Date Implemented**: [YYYY-MM-DD]
-   **Status**: [e.g., Development, Testing, Production, Deprecated]

## 2. Adapter Implementation Details

This section details how the adapter interfaces with the CausaGanha system via the `DiarioDiscovery`, `DiarioDownloader`, and `DiarioAnalyzer` interfaces.

### 2.1. `DiarioDiscovery` Implementation

-   **Module**: `src/tribunais/[abbreviation]/discovery.py`
-   **Class Name**: `[Abbreviation]Discovery`
-   **URL Discovery Method**:
    -   [Describe how diario URLs are found. Is it by querying a specific endpoint, scraping a page, following a predictable URL pattern based on date, etc.?]
    -   [Mention any specific parameters, date formats, or request headers used.]
-   **Key Logic/Challenges**:
    -   [Any specific challenges in finding URLs, like session management, CAPTCHAs (and how they are handled, if at all), rate limiting encountered, etc.?]
-   **Date Range Support**:
    -   `get_diario_url(target_date)`: [Supported? Any known limitations?]
    -   `get_latest_diario_url()`: [Supported? How is "latest" determined?]
    -   `list_diarios_in_range(start_date, end_date)`: [Supported? Efficiently implemented or iterates day-by-day?]

### 2.2. `DiarioDownloader` Implementation

-   **Module**: `src/tribunais/[abbreviation]/downloader.py` (or relevant module)
-   **Class Name**: `[Abbreviation]Downloader`
-   **PDF Download Method**:
    -   [Describe how PDFs are downloaded once the URL is known.]
    -   [Are there specific headers, cookies, or session requirements for downloading?]
-   **Internet Archive (IA) Integration**:
    -   `archive_to_ia(diario)`: [Standard IA upload used? Any custom metadata specific to this tribunal added during IA upload?]
    -   **IA Identifier Pattern**: [Describe the pattern used for IA identifiers for this tribunal's diarios (e.g., `causaganha-[abbrev]-diario-YYYY-MM-DD`).]
-   **Key Logic/Challenges**:
    -   [Any issues with PDF downloads, file validation, large files, etc.?]

### 2.3. `DiarioAnalyzer` Implementation (LLM Extraction)

-   **Module**: `src/tribunais/[abbreviation]/analyzer.py` (or relevant module, might use a generic analyzer initially)
-   **Class Name**: `[Abbreviation]Analyzer` (or e.g., `GeminiDiarioAnalyzer`)
-   **Extraction Prompts**:
    -   [If custom prompts are used for this tribunal, where are they located? Briefly describe any tribunal-specific instructions given to the LLM.]
-   **Output Structure**:
    -   [Does it conform to the standard decision JSON structure? Any tribunal-specific fields or nuances in the extracted data?]
-   **Key Logic/Challenges**:
    -   [Any difficulties in parsing the PDF text? Unique formatting in this tribunal's diarios that affects extraction? Low LLM accuracy for specific sections?]

## 3. Configuration

-   **Environment Variables**:
    -   [List any specific environment variables needed for this adapter (e.g., API keys, specific URLs if not hardcoded).]
-   **`config.toml` Settings**:
    -   [List any sections or keys in `config.toml` relevant to this adapter.]
-   **Registry Entry**:
    -   Ensure the adapter's classes are registered in `src/tribunais/__init__.py`.
        ```python
        # Example for src/tribunais/__init__.py
        _DISCOVERIES = {
            ...,
            '[abbreviation]': [Abbreviation]Discovery,
        }
        # ... and for _DOWNLOADERS, _ANALYZERS
        ```

## 4. Testing

-   **Unit Tests**:
    -   Location: `tests/tribunais/[abbreviation]/`
    -   [Describe key unit tests, e.g., for URL generation, date parsing, specific download logic, sample PDF analysis if applicable.]
-   **Integration Tests**:
    -   [How is end-to-end functionality tested for this adapter? E.g., using `causaganha` CLI commands, specific test scripts.]
-   **Mock Data**:
    -   [Is there mock data or sample PDFs for testing this adapter offline? Where is it located (e.g., `tests/mock_data/[abbreviation]/`)?]

## 5. Known Issues & Limitations

-   [List any known bugs, limitations (e.g., cannot fetch diarios older than X date), or areas for future improvement for this specific adapter.]

## 6. Developer Notes & Troubleshooting

-   [Any tips for other developers working on this adapter? Common pitfalls? Debugging advice?]
-   [Contact person/expert for this adapter if different from main developer list.]

---

*This template should be copied to `docs/tribunais/[abbreviation]_adapter.md` and filled out when a new tribunal adapter is developed.*
