# Plan and Reasoning for the Winner Prediction Feature

## Feature Idea and Motivation

The core idea is to introduce a secondary, optional mechanism for determining the winning party in a judicial decision, using a lightweight machine learning (ML) model. This ML model will operate alongside the existing LLM-based analysis (`DecisionAnalyzer`).

### Why is this a good thing?

1.  **Cost and Speed Efficiency:** The primary analysis relies on a powerful but potentially slow and expensive Large Language Model (LLM). A smaller, specialized ML model, once trained, can perform the specific task of winner prediction much faster and at a fraction of the cost.
2.  **Scalability:** For scenarios involving the analysis of tens of thousands of documents, the cost and latency of using an LLM for every single document can be prohibitive. The ML model provides a highly scalable alternative.
3.  **Continuous Improvement:** The feature is designed for the ML model to learn and improve over time. By using the LLM as a "teacher" in an online learning setup, the ML model can be continuously trained on new decisions, becoming more accurate as it sees more data. This creates a powerful feedback loop where the expensive LLM is used to train a cheap and fast model.
4.  **Resilience and Fallback:** The ML model can serve as a fallback or a preliminary classifier. For example, it could be used to make a first pass on all documents, with the more expensive LLM analysis being reserved for cases where the ML model has low confidence.

### Relationship with the Current Code

This feature is designed as a **synergistic and non-intrusive extension** of the existing `CausaGanha` pipeline.

-   **Hooks into the Analysis Pipeline:** The new ML components are integrated into the existing `analyze` pipeline step (`application/pipeline/analyze.py`). They are activated only when a specific CLI flag (`--winner-classifier`) is used, ensuring that the default behavior of the application is unchanged.
-   **Leverages Existing Infrastructure:** The feature reuses the existing `DocumentService` to get the text from judicial decisions. It also extends the existing `DecisionAnalysis` data model to store the results of the ML prediction, ensuring that the data remains consistent and easy to access.
-   **Parallel and Independent:** The ML tasks (embedding, prediction, and training) are designed to run in a separate process pool. This means they will not block the main application thread, which handles I/O operations like downloading files and database interactions. This ensures that the performance of the existing pipeline is not degraded when the ML feature is enabled.
-   **Complementary, Not a Replacement:** The ML model is not intended to replace the main LLM-based analysis. Instead, it complements it by providing a faster, cheaper, and more scalable way to perform a specific sub-task. The results from both the LLM and the ML model can be stored and compared, providing a richer set of data for analysis.

---

This document details the plan and the reasoning behind the implementation of the optional and parallel winner prediction feature for the CausaGanha project.

## Introduction

The primary goal of this feature is to introduce a machine learning model that can predict the winning side of a judicial decision. This model is designed to be lightweight, to learn incrementally from new data, and to run in parallel with the existing analysis pipeline without affecting its performance. The feature is optional and disabled by default.

## Phase 1: Setup and BDD (Behavior-Driven Development)

### 1.1. BDD Feature Files

- **Action:** Create a `winner_prediction.feature` file in `tests/features`.
- **Reasoning:**
    - **Clear Requirements:** BDD starts with writing human-readable scenarios that describe the feature's behavior from a user's perspective. This ensures that we have a clear and shared understanding of what we are building before writing any code.
    - **Test-Driven:** BDD is a form of Test-Driven Development (TDD). By writing the feature files first, we create a set of executable specifications that will guide the implementation and serve as acceptance tests.
    - **Focus on Behavior:** BDD helps us focus on the *what* (the behavior of the system) rather than the *how* (the implementation details).

### 1.2. Scaffolding New Modules

- **Action:** Create a new `src/causaganha/ml` directory with empty Python files for the ML components (`embeddings.py`, `online_learner.py`, `teacher.py`, `worker_pool.py`).
- **Reasoning:**
    - **Organization:** Creating a dedicated `ml` module keeps the machine learning related code separate from the main application logic, improving modularity and maintainability.
    - **Clear Structure:** Scaffolding the files upfront provides a clear picture of the components that need to be built and how they will be organized.

## Phase 2: Core ML Implementation

### 2.1. Embedding Generation (`GeminiEmbedder`)

- **Action:** Implement a `GeminiEmbedder` class to generate text embeddings using the `gemini-embedding-001` model.
- **Reasoning:**
    - **State-of-the-Art Embeddings:** Using a modern embedding model like `gemini-embedding-001` is crucial for capturing the semantic meaning of the judicial texts, which is essential for the performance of the downstream ML model.
    - **Consistency:** The user specified this embedding model, ensuring we meet their requirements.
    - **API Key Management:** The implementation relies on environment variables for the API key, which is a good practice for managing secrets and is consistent with the existing `DecisionAnalyzer`.

### 2.2. Online Learning Model (`WinnerPredictor`)

- **Action:** Implement a `WinnerPredictor` class using `scikit-learn`'s `SGDClassifier`.
- **Reasoning:**
    - **Online Learning:** The user requested an "online learning" or "contextual bandit-like" model. `SGDClassifier` is a perfect fit for this, as it can be updated incrementally with new data using its `partial_fit` method, without needing to retrain on the entire dataset.
    - **Lightweight:** `SGDClassifier` is a very efficient and lightweight model, which aligns with the user's requirement to keep the feature lightweight.
    - **Probabilistic Output:** We use `loss='log_loss'` to make the model a logistic regression classifier, which allows us to get prediction probabilities (confidence scores) in addition to the predicted class.
    - **Persistence:** The model's state is saved to disk using `joblib`, allowing it to be reused across different runs of the application.

### 2.3. LLM-based Teacher (`LLMTeacher`)

- **Action:** Implement an `LLMTeacher` class that uses `pydantic-ai` to get a "ground truth" label for the winning side from an LLM.
- **Reasoning:**
    - **Automated Labeling:** The user specified that the LLM should act as a "teacher." This approach automates the process of labeling new data, which is essential for the online learning model to improve over time.
    - **Focused Prompt:** The `LLMTeacher` uses a very specific prompt to get a clear, structured output (`plaintiff_won`, `defendant_won`, or `unclear`). This makes the labeling process more reliable.
    - **Resilience:** The teacher is designed to handle failures gracefully. If the LLM fails to provide a label, it returns `unclear`, preventing the pipeline from breaking.

## Phase 3: Integration and Parallel Execution

### 3.1. Data Model Modification

- **Action:** Add new fields to the `DecisionAnalysis` model to store the ML prediction, confidence, teacher label, and model version.
- **Reasoning:**
    - **Data Persistence:** To make the results of the ML analysis useful, they need to be stored in the database. Adding these fields to `DecisionAnalysis` is the most direct way to achieve this.
    - **Traceability:** Storing the model version is a good practice for MLOps, as it allows us to track which version of the model made which prediction.

### 3.2. CLI Flag (`--winner-classifier`)

- **Action:** Add a `--winner-classifier` flag to the `analyze` and `pipeline` commands with three modes: `off`, `infer`, and `teach`.
- **Reasoning:**
    - **Optional Feature:** This directly implements the user's requirement to make the feature optional and disabled by default.
    - **Fine-Grained Control:** The three modes provide fine-grained control over the feature's behavior, allowing the user to run it in inference-only mode or in training mode.

### 3.3. Worker Pool for Parallel Execution

- **Action:** Implement a `WorkerPool` using `concurrent.futures.ProcessPoolExecutor`.
- **Reasoning:**
    - **Non-Blocking Execution:** ML model inference and training can be CPU-intensive. Running these tasks in a separate process pool prevents them from blocking the main `asyncio` event loop, which is responsible for I/O-bound tasks like downloading files and interacting with the database.
    - **Parallelism:** A worker pool allows us to process multiple ML tasks concurrently, which is crucial for performance when analyzing a large number of decisions.
    - **User Control:** The number of workers in the pool will be configurable via a `--jobs` CLI flag, giving the user control over the resource usage.

## Phase 4: Testing and Documentation

### 4.1. Unit/Integration Tests

- **Action:** Add unit tests for the new ML components.
- **Reasoning:**
    - **Quality Assurance:** Unit tests are essential for ensuring that each component works as expected in isolation.
    - **Regression Prevention:** A solid test suite helps prevent regressions as the codebase evolves.
    - **Note on Failures:** Although the tests were written, they could not be run successfully due to environment issues. This is noted as a risk and should be addressed in the future.

### 4.2. Documentation

- **Action:** Update `README.md` with instructions on how to use the new feature.
- **Reasoning:**
    - **Usability:** Good documentation is crucial for making the new feature discoverable and usable.
    - **Clarity:** The documentation clearly explains the purpose of the `--winner-classifier` flag and its different modes, with examples.
