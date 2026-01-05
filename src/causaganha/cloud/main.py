import functions_framework

from causaganha.cloud.functions.ingest import ingest_worker
from causaganha.cloud.functions.llm import llm_worker, process_llm
from causaganha.cloud.functions.scheduler import scheduler_tick


# Expose functions for Cloud Functions runtime

@functions_framework.http
def scheduler_http(request):
    """HTTP entry point for Scheduler."""
    import asyncio
    return asyncio.run(scheduler_tick(request))

@functions_framework.cloud_event
def ingest_pubsub(cloud_event) -> None:
    """Pub/Sub entry point for Ingest."""
    import asyncio
    # CloudEvent to dict
    event_data = {
        "data": cloud_event.data,
        "attributes": cloud_event.attributes,
    }
    asyncio.run(ingest_worker(event_data, None))

@functions_framework.cloud_event
def llm_pubsub(cloud_event) -> None:
    """Pub/Sub entry point for LLM."""
    import asyncio
    event_data = {
        "data": cloud_event.data,
        "attributes": cloud_event.attributes,
    }
    asyncio.run(llm_worker(event_data, None))

@functions_framework.http
def llm_http(request):
    """HTTP entry point for LLM (Cloud Tasks target)."""
    import asyncio
    request_json = request.get_json(silent=True)
    if request_json and "docKey" in request_json:
        asyncio.run(process_llm(request_json["docKey"]))
        return "OK"
    return "Missing docKey", 400
