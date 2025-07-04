# Multi-Tribunal Data Collection

## Problem Statement

- **What problem does this solve?**
  Currently, CausaGanha's data collection is limited to the Tribunal de Justiça de Rondônia (TJRO). This feature aims to expand data collection capabilities to include all (or a significant number of) Brazilian tribunals.
- **Why is this important?**
  Expanding data sources to multiple tribunals will significantly enhance the scope and representativeness of the judicial data. This will lead to a more robust and accurate OpenSkill rating system for lawyer performance, reflecting a broader range of legal practices and regional variations across Brazil.
- **Current limitations**
  The existing data collection mechanism (`src/tribunais/tjro/`) is tightly coupled with TJRO's specific website structure and PDF naming conventions. It lacks the flexibility to adapt to other tribunals' diverse systems for publishing Diários de Justiça.

## Proposed Solution

- **High-level approach**
  Develop a modular, extensible, and configurable data collection framework. This framework will abstract common collection tasks while allowing for tribunal-specific implementations for discovery, download, and metadata extraction of Diários de Justiça.
- **Technical architecture**
  1.  **`TribunalCollector` Base Class**: An abstract base class defining a common interface for all tribunal collectors. It will include methods like `discover_diarios(date_range)`, `download_diario(diario_info)`, `get_metadata(diario_info)`.
  2.  **Specific Collector Implementations**: Concrete classes for each supported tribunal (e.g., `TJROCollector`, `TJSPCollector`, `TJMGCollector`) inheriting from `TribunalCollector`. Each will implement the specific logic for interacting with its respective tribunal's systems.
  3.  **Tribunal Configuration System**: A configuration mechanism (likely using TOML files, consistent with existing `config.toml`) to store tribunal-specific details such as base URLs, API endpoints, date formats, specific parsing rules, rate limits, and authentication requirements if any.
  4.  **Discovery Service**: A component that can identify available Diários from a tribunal for a given period, handling different listing mechanisms (e.g., web scraping, API calls, standardized naming patterns).
  5.  **Downloader Service**: A robust downloader capable of handling various download protocols, managing retries, and respecting tribunal-specific rate limits.
  6.  **CLI Integration**:
      - Modify `causaganha queue` to accept a tribunal identifier (e.g., `causaganha queue --tribunal TJSP --from-csv ...` or `causaganha queue --tribunal all ...`).
      - The system should be able to iterate through configured tribunals if an "all" or multi-tribunal option is specified.
  7.  **Data Model Update**: Potentially extend the `pdf_metadata` table or associated data structures to include a `tribunal_id` field to allow for filtering and tribunal-specific analysis.

- **Implementation steps**
  1.  **Research (Phase 1)**:
      - Identify a list of target tribunals for initial implementation (e.g., TJSP, TJMG, TRF1, STJ, STF).
      - For each, investigate and document their methods for accessing/downloading Diários de Justiça (websites, APIs, file naming conventions, authentication).
  2.  **Base Framework Design (Phase 1)**:
      - Design and implement the `TribunalCollector` abstract base class and its interface.
      - Design the structure for tribunal-specific configuration files.
  3.  **TJRO Refactor (Phase 2)**:
      - Refactor the existing TJRO collection logic (`src/tribunais/tjro/`) to conform to the new `TribunalCollector` interface, creating a `TJROCollector` class. This ensures the new framework supports existing functionality.
  4.  **New Collector Implementation (Proof of Concept - Phase 3)**:
      - Implement a collector for a second tribunal (e.g., `TJSPCollector`) based on the research from Step 1. This will serve as a proof of concept and help refine the base framework.
  5.  **Configuration and CLI Integration (Phase 4)**:
      - Implement the tribunal configuration loading system.
      - Update the `causaganha queue` command and relevant parts of the `async_diario_pipeline.py` to use the new collection framework, allowing selection of tribunals and iterating through them.
      - Update database schemas if necessary (e.g., add `tribunal_id`).
  6.  **Further Collector Implementations (Phase 5 - Ongoing)**:
      - Incrementally add collectors for other prioritized tribunals.
  7.  **Testing and Documentation (Ongoing)**:
      - Write unit and integration tests for the new framework and each collector.
      - Document how to add support for new tribunals.

## Success Criteria

- **Functional Collection**: The system can successfully discover, queue, download, and archive Diários de Justiça from at least three different tribunals (e.g., TJRO, TJSP, TJMG).
- **Extensibility**: The framework allows adding support for new tribunals by creating a new collector class and a configuration file, without major changes to the core system.
- **Configurability**: Tribunal-specific parameters (URLs, rate limits, etc.) are managed through external configuration.
- **CLI Control**: Users can specify target tribunals via the CLI for the `queue` command.
- **Data Integrity**: Data collected from different tribunals is correctly identified (e.g., with a `tribunal_id`) and can be processed by downstream stages (analyze, score).
- **Documentation**: Clear documentation exists for using the multi-tribunal feature and for developers on how to add new tribunal collectors.

## Implementation Plan (High-Level for this document)

1.  **Phase 1: Research & Base Framework Design**:
    - Research data access methods for TJSP, TJMG, TRF1.
    - Design `TribunalCollector` ABC and configuration structure.
2.  **Phase 2: TJRO Collector Refactor**:
    - Adapt existing TJRO logic into `TJROCollector`.
    - Test TJRO collection through the new framework.
3.  **Phase 3: TJSP Collector Implementation (PoC)**:
    - Implement `TJSPCollector`.
    - Test TJSP collection. Refine framework based on learnings.
4.  **Phase 4: Generalize Configuration and CLI**:
    - Implement dynamic loading of collectors based on configuration.
    - Update `causaganha queue` and pipeline logic.
    - Implement database changes (e.g., `tribunal_id`).
5.  **Phase 5: Further Implementation & Documentation**:
    - Implement collector for one more tribunal (e.g., TJMG).
    - Write comprehensive tests and user/developer documentation.

## Risks & Mitigations

- **Risk 1: Diverse and Inconsistent Tribunal Systems**: Each tribunal's website/API for accessing Diários can be vastly different, undocumented, or frequently changing.
  - _Mitigation_:
    - Design a highly flexible adapter pattern within each collector.
    - Prioritize tribunals with more stable or developer-friendly access methods.
    - Implement robust error handling and logging for each collector.
    - Plan for ongoing maintenance and updates as tribunal systems change.
- **Risk 2: Rate Limiting, CAPTCHAs, and Access Restrictions**: Tribunals may employ aggressive rate limiting, CAPTCHAs, or require specific headers/authentication, blocking automated collection.
  - _Mitigation_:
    - Implement configurable per-tribunal rate limiting and polite request intervals.
    - Use sophisticated retry mechanisms with exponential backoff.
    - For CAPTCHAs, investigate if alternative (e.g., API) access routes exist. Human-assisted CAPTCHA solving is out of scope for automated collection. Prioritize tribunals without such aggressive measures for initial implementation.
    - Support common authentication patterns if necessary and documented by tribunals.
- **Risk 3: Scalability and Maintenance Overhead**: Supporting a large number of tribunals will significantly increase the complexity and maintenance burden.
  - _Mitigation_:
    - Prioritize implementation for major national and state tribunals first.
    - Design the collector framework to be as self-contained as possible per tribunal, minimizing cascading changes.
    - Provide excellent documentation and contribution guidelines to encourage community support for adding and maintaining collectors.
    - Implement a monitoring system to detect when a collector might be broken due to changes in a tribunal's website.
- **Risk 4: Legal and Ethical Considerations**: Ensuring compliance with each tribunal's terms of service for data access.
  - _Mitigation_:
    - For each tribunal, review any stated terms of service or data usage policies.
    - Focus on publicly available data and mimic respectful browsing behavior (e.g., appropriate User-Agent, respecting `robots.txt` where applicable, conservative request rates).
    - Be transparent about the data sources and collection methods.
- **Risk 5: Data Normalization**: Diários from different tribunals might have different formats, content structures, or metadata.
  - _Mitigation_: While this plan focuses on collection, the design should anticipate that downstream processes (extraction, analysis) will need to handle this variability. The collector should aim to capture as much raw metadata as possible. The `tribunal_id` will be crucial for context-specific parsing rules later.
    [end of docs/plans/multi_tribunal_collection.md]
