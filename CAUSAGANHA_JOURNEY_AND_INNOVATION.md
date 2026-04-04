# Strategic Data Journey Analysis & Utility Unlocking for CausaGanha

## Executive Summary
CausaGanha collects, archives, and analyzes massive volumes of judicial data from the Brazilian DJEN. While the foundational architecture effectively secures and structures this data, the current user experience remains largely passive. This document analyzes the three core phases of the "Researcher Journey" and proposes high-value UX interventions designed to transform passive data viewing into active legal intelligence. By systematically smoothing friction points, we can unlock new utilities that directly serve legal researchers, lawyers, and public transparency advocates.

---

## A. The Discovery Journey: From Broad Search to Specific Finding

### Current State
Currently, the discovery process relies on manual navigation. The user opens the dashboard, is presented with a list of 91 tribunals, clicks into a specific tribunal, and then must search by date.

### Friction Points
* **Siloed Navigation:** Forcing users to select a tribunal first prevents cross-jurisdictional discovery.
* **Manual Filtering:** Searching by date is restrictive when users are looking for themes, case types, or specific lawyer outcomes.
* **Comparison Difficulty:** It is extremely difficult to compare trends or lawyer performance across different tribunals simultaneously.

### Smoothing the Journey (UX Interventions)
* **Unified Global Search:** Implement a global search bar on the homepage that queries across all tribunals, leveraging the consolidated Parquet data lake.
* **Faceted Filtering:** Allow users to filter by date range, outcome type (e.g., *procedente*, *improcedente*), lawyer (OAB), and legal domain without first selecting a tribunal.
* **Dashboard Aggregation:** Create summary views that highlight top-level trends before the user drills down into specific records.

### Potential Unlocks (High-Value Features)
* **Semantic Search:** Utilize the existing embedding pipelines (`JINA_V4_1024`, `GOOGLE_GEMINI_768`) to allow natural language queries (e.g., "contract dispute wins involving real estate in SP").
* **Cross-Tribunal Trend Analysis:** Enable visualizations that show how specific types of cases or specific lawyers fare across different states.
* **Custom Alerts:** Allow users to save a search (e.g., a specific OAB number or legal keyword) and receive notifications when new matching publications are ingested.

---

## B. The Consumption Journey: From Reading to Understanding

### Current State
When a user finds a relevant record, they click the publication title and are presented with the raw, dense legal text of the judicial communication.

### Friction Points
* **Information Density:** Legal texts are notoriously verbose, making it hard to quickly extract the core decision or relevance.
* **Missing Context:** The raw text often lacks immediate linkage to the broader case history or related entities.
* **Poor Mobile Experience:** Reading long, unformatted legal documents on a mobile device is tedious.

### Smoothing the Journey (UX Interventions)
* **Reader View:** Implement a clean, responsive "reader mode" for publications, utilizing Pico CSS typography for improved legibility, especially on mobile (ensuring 24px touch targets for any interactive elements within the view).
* **Entity Highlighting:** Automatically highlight key entities (Lawyers, Parties, Outcomes) within the text using the structured data already available in the `destinatarios` and `representacoes` tables.

### Potential Unlocks (High-Value Features)
* **AI Summaries:** Leverage the classification pipeline to provide a one-paragraph, plain-language summary of the decision and its outcome at the top of the publication view.
* **Key Excerpts Extraction:** Automatically pull out the "dispositivo" (the actual order or decision) from the surrounding procedural boilerplate.
* **Citation Maps:** Create visual links or side-panels showing other publications in the same `processo` (case) or referencing the same precedents, providing immediate context.

---

## C. The Acquisition Journey: From Found to Saved/Used

### Current State
Currently, the primary acquisition method is downloading the raw ZIP file or viewing a raw link, which is geared towards developers rather than legal professionals.

### Friction Points
* **Unwieldy Formats:** ZIP files containing JSON/raw text are not user-friendly for non-technical users.
* **Lack of Persistence:** Users cannot easily save specific records they find interesting within the platform; they must copy links or download files externally.
* **Zero Analytics Tracking:** It is hard to track which specific documents or searches are most valuable to users if they simply download bulk data.

### Smoothing the Journey (UX Interventions)
* **In-App Saving:** Implement a "Save" or "Bookmark" button (with appropriate zero-JS Astro icons) on publications and search results.
* **Simplified Exports:** Offer one-click exports of individual publications or search result tables.

### Potential Unlocks (High-Value Features)
* **"My Collection" (Workspace):** Create a personalized area where users can organize saved publications into folders or "cases," and save complex search queries.
* **Export to PDF/CSV:** Allow users to export a cleanly formatted PDF of a specific publication (useful for printing or attaching to legal briefs) or a CSV of search results (useful for external spreadsheet analysis).

---

## Conclusion
By shifting the focus from simply *providing* the data to actively *assisting* the researcher in navigating it, CausaGanha can transition from an open-data archive to a powerful legal intelligence platform. The foundational architecture (consolidated Parquet files, embeddings, UUIDv5 deduplication) is already in place to support these advanced features; the next step is building the UX layers that expose this power to the end user.
