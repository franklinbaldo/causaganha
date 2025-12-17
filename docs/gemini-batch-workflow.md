# Gemini Batch Workflow

This document describes the new, high-throughput workflow for analyzing judicial decisions using the Gemini Batch API and the Internet Archive (IA).

## 1. Overview

The new workflow is designed to be scalable and cost-effective. It decouples the process of metadata collection from the computationally expensive analysis step. Instead of analyzing documents one by one, we now follow a three-stage process:

1.  **Manifest Generation**: `causaganha` exports a JSON manifest of all documents that need to be analyzed.
2.  **Orchestration & Batch Processing**: An external orchestrator (e.g., a Google Cloud Function) consumes the manifest, submits a batch analysis job to the Gemini Batch API, and polls for its completion.
3.  **Result Ingestion**: The orchestrator parses the results from the batch job, creates a Parquet file containing the structured analysis data, and uploads it to the Internet Archive.

This approach allows us to process thousands of documents in a single, asynchronous job, significantly reducing both processing time and cost.

## 2. The Workflow in Detail

### Step 1: Manifest Generation

The first step is to generate a manifest of all intimations that require analysis. This is done using the new `manifest export` CLI command:

```bash
uv run causaganha manifest export --limit 1000 > manifest.json
```

This command queries the local DuckDB database and produces a JSON file containing an array of objects, each conforming to the `ParquetSchema`.

**Manifest Entry Example (`manifest.json`)**:

```json
[
  {
    "intimation_id": 12345,
    "process_number": "0001-01.2024.8.22.0001",
    "tribunal": "TJRO",
    "decision_date": "2024-01-15",
    "download_url": "http://example.com/document.pdf",
    "needs_download": true,
    "ia_url": null,
    "gemini_summary": null,
    "full_decision_text": null,
    "outcome": null,
    "winner_lawyers": [],
    "loser_lawyers": []
  }
]
```

### Step 2: Orchestration and Batch Analysis

An orchestrator function is responsible for managing the batch analysis process. This function is not part of the `causaganha` repository but will consume its output.

The orchestrator performs the following actions:

1.  **Downloads the manifest** generated in the previous step.
2.  For each item in the manifest, it **downloads the PDF document** from the `download_url`.
3.  It **submits a batch job** to the Gemini Batch API. For technical details on this process, see the [Gemini Batch API Integration Guide](./gemini-batch-integration.md).
4.  It **polls the batch job's status** until it is complete.
5.  Upon completion, it **retrieves the analysis results**.

**Sample Gemini Prompt**:

The prompt sent to the Gemini API for each document is designed to elicit a JSON response that conforms to our `DecisionAnalysis` model.

```
You are a legal expert analyzing judicial decisions from Brazil. Analyze the provided PDF document and extract structured information about the case outcome. Identify the winning and losing parties and their lawyers (OAB number and state). Determine the decision type and outcome. Provide a brief summary and the judge's name. The output must be a valid JSON object that conforms to the `DecisionAnalysis` schema.
```

### Step 3: Result Ingestion and Archiving

Once the batch job is complete, the orchestrator processes the results:

1.  It **parses the JSON output** from the Gemini API and validates it against the `DecisionAnalysis` model.
2.  It **merges the analysis results** with the original metadata from the manifest.
3.  It **creates a Parquet file** containing the enriched data. The schema of this file is defined by our `ParquetSchema`.
4.  It **uploads the Parquet file** to a dedicated collection on the Internet Archive.

**Internet Archive Upload Metadata**:

When uploading the Parquet file, the orchestrator should include the following metadata:

-   `title`: "CausaGanha Analysis Results - YYYY-MM-DD"
-   `creator`: "CausaGanha Batch Orchestrator"
-   `mediatype`: "data"
-   `collection`: "causaganha-analysis-results"
-   `date`: The date of the batch job submission.

## 3. Consuming the Parquet Data

The final step in the pipeline is to consume the Parquet files for ranking and further analysis. The `causaganha score` command (or a similar, future implementation) will:

1.  **Download the Parquet files** from the Internet Archive.
2.  **Read the structured data** using a library like `pyarrow`.
3.  **Update the `lawyer_ratings` table** in the local DuckDB based on the `outcome` and lawyer information in each record.

This new workflow provides a robust, scalable, and efficient foundation for the CausaGanha platform.
