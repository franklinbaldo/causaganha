# 🔄 Architectural Pattern: Persistent Task Store

**Status:** Active
**Introduced:** Symbiote Era (Sprint 3)
**Component:** `src/egregora/database/task_store.py`

---

## 💡 The Concept

In the **Batch Era**, processes were fragile. If the `enrichment.py` script crashed halfway through processing 100 URLs, the progress was lost, or worse, the script had to be manually patched to skip the completed items.

The **Symbiote Era** introduces the **Persistent Task Store** pattern. Instead of keeping the "to-do list" in memory or relying on the call stack, we materialize intent into the database.

The `TaskStore` uses the embedded analytical database (DuckDB/Ibis) as a transactional job queue.

## 🏗️ Schema

The `tasks` table is append-only and strictly typed.

| Column | Type | Description |
| :--- | :--- | :--- |
| `task_id` | `UUID` | Unique identifier for the task |
| `task_type` | `VARCHAR` | Discriminator (e.g., `enrich_url`, `generate_banner`) |
| `status` | `VARCHAR` | `pending`, `processing`, `completed`, `failed`, `superseded` |
| `payload` | `JSON` | Complete arguments required to execute the task |
| `created_at` | `TIMESTAMP` | When the task was enqueued |
| `processed_at`| `TIMESTAMP` | When the task reached a terminal state |
| `error` | `VARCHAR` | Error message if failed |

**Constraints:**
- `status` must be one of `['pending', 'processing', 'completed', 'failed', 'superseded']`
- `task_type` must be one of `['generate_banner', 'update_profile', 'enrich_media', 'enrich_url']`

## ⚙️ Workflow

### 1. Enqueue (Producer)
When the core pipeline (`write.py`) encounters work that can be deferred or processed asynchronously (like fetching metadata for a URL), it does not execute it immediately. Instead, it enqueues a task.

```python
task_store.enqueue(
    task_type="enrich_url",
    payload={"url": "https://example.com/article", "message_id": "..."}
)
```

**Key Benefit:** The producer execution is fast and non-blocking. It dumps the intent and moves on.

### 2. Batch Processing (Consumer)
Specialized workers (like `EnrichmentWorker`) wake up, check the queue, and process tasks in efficient batches.

```python
# Fetch 50 pending tasks
tasks = task_store.fetch_pending(task_type="enrich_url", limit=50)

# Process them (e.g., using Google Batch API)
results = worker.process_batch(tasks)

# Mark as completed/failed
for task_id, result in results.items():
    if result.success:
        task_store.mark_completed(task_id)
    else:
        task_store.mark_failed(task_id, result.error)
```

## 🛡️ Resilience & Observability

This pattern provides three critical capabilities:

1.  **Crash-Proofing:** If the worker process dies, the tasks remain in the `pending` (or `processing` w/ timeout) state. When the system restarts, it picks up exactly where it left off.
2.  **Observability:** We can use standard SQL to inspect the state of the system.
    ```sql
    SELECT task_type, count(*)
    FROM tasks
    WHERE status = 'failed'
    GROUP BY task_type;
    ```
3.  **Idempotency:** The store allows us to implement checks (like `mark_superseded`) to avoid doing work that has been rendered obsolete by newer events.

## 📜 Lore: The Memory of the Machine

The TaskStore is the "memory" of the Symbiote. It ensures that no intention is forgotten, even if the body (the process) momentarily fails. It is the mechanism that allows Egregora to say, *"I was interrupted, but I remember what I was doing."*
