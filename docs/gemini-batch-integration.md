# Gemini Batch API Integration Pattern

This document outlines the recommended approach for integrating the Gemini Batch API with the CausaGanha pipeline.

## 1. Executive Summary

- **Problem**: The existing analysis pipeline processes documents one by one, which is slow and inefficient for large volumes.
- **Solution**: Use the Gemini Batch API for asynchronous, large-scale processing of analysis requests.
- **Key Finding**: `pydantic-ai`, our current library, does **not** natively support the Gemini Batch API. Its `Agent` is designed for synchronous, single-shot requests.
- **Recommendation**: We will use the official `google-genai` Python library to submit batch jobs. The raw JSON results from the batch job will then be parsed and validated using our existing `DecisionAnalysis` Pydantic model. This gives us the best of both worlds: efficient batch processing and structured, validated data.

## 2. The Batch Processing Pattern

The process involves three main steps: job submission, status polling, and result retrieval.

### Step 1: Job Submission

A batch job is created by submitting a list of `GenerateContentRequest` objects. For our use case, each request will contain the system prompt and the PDF content. The API supports two methods: inline requests (for smaller batches) and file-based submission (JSONL). We will start with inline requests.

**Example: Submitting a Batch Job**

```python
import google.generativeai as genai
from google.generativeai.client import Job, File

# Configure with your API key
# genai.configure(api_key="YOUR_GEMINI_API_KEY")

# 1. Define the requests
# This prompt should match the one in `DecisionAnalyzer`
system_prompt = (
    "You are a legal expert analyzing judicial decisions from Brazil. "
    "Analyze the provided PDF document and extract structured information about the case outcome. "
    "Identify the winning and losing parties and their lawyers (OAB number and state). "
    "Determine the decision type and outcome. Provide a brief summary and the judge's name."
    "The output must be a valid JSON object that conforms to the `DecisionAnalysis` schema."
)

# Assume `pdf_bytes_list` is a list of tuples: (intimation_id, pdf_bytes)
requests = []
for intimation_id, pdf_bytes in pdf_bytes_list:
    requests.append({
        "contents": [
            {"role": "user", "parts": [{"text": system_prompt}]},
            {"role": "model", "parts": [{"text": "OK, please provide the PDF."}]},
            {"role": "user", "parts": [{"inline_data": {"mime_type": "application/pdf", "data": pdf_bytes}}]},
        ],
        # Important: Specify JSON output
        "generation_config": {
            "response_mime_type": "application/json",
        }
    })

# 2. Create the batch job
batch_job: Job = genai.batch_generate_content(requests)

print(f"Submitted batch job: {batch_job.name}")
# Store batch_job.name in our database to track its status
```

### Step 2: Polling for Status

After submitting the job, we need to periodically check its status. This is done by retrieving the job using its name.

**Example: Checking Job Status**

```python
import time

# Retrieve the job by name
retrieved_job = genai.get_job(name=batch_job.name)

while retrieved_job.state.name in ("PROCESSING", "PENDING"):
    print(f"Job state: {retrieved_job.state.name}. Waiting...")
    time.sleep(30)
    retrieved_job = genai.get_job(name=batch_job.name)

print(f"Job finished with state: {retrieved_job.state.name}")
```

### Step 3: Result Retrieval and Parsing

Once the job is complete (`SUCCEEDED`), we can retrieve the results. The results will be a list of JSON strings corresponding to each initial request. We will then parse these JSON strings into our `DecisionAnalysis` Pydantic model.

**Example: Retrieving and Parsing Results**

```python
from causaganha.analysis.models import DecisionAnalysis

if retrieved_job.state.name == "SUCCEEDED":
    for i, response in enumerate(retrieved_job.results):
        intimation_id = pdf_bytes_list[i][0]  # Get the original ID
        try:
            # The response text is a JSON string
            json_text = response.text
            # Use Pydantic to parse and validate
            analysis = DecisionAnalysis.model_validate_json(json_text)

            print(f"Successfully parsed result for intimation {intimation_id}: {analysis.outcome}")
            # Here, we would store the `analysis` object in our database

        except Exception as e:
            print(f"Failed to parse result for intimation {intimation_id}: {e}")
            # Log the error and the raw response for debugging
```

## 3. Next Steps for Orchestrator Implementation

The orchestrator (e.g., a Cloud Function) will need to:
1.  **Consume the manifest** provided by the new `causaganha manifest export` CLI command.
2.  **Download PDF content** for each item in the manifest.
3.  **Submit the batch job** as described above, storing the returned `job.name`.
4.  **Implement a polling mechanism**. This could be a separate scheduled function that checks the status of active jobs.
5.  **Process results** upon job completion, parsing them into the `ParquetSchema` and uploading the final Parquet file to the Internet Archive.
6.  **Required Environment Variables**:
    - `GEMINI_API_KEY`: For authenticating with the Gemini API.
    - `IA_ACCESS_KEY` / `IA_SECRET_KEY`: For uploading results to the Internet Archive.

This approach allows us to leverage the cost and performance benefits of the Gemini Batch API while maintaining the data integrity and structure provided by our Pydantic models.
