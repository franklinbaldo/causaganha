---
id: 20251231-100527-refactor-worker-logic-in-runner
status: todo
title: "Refactor worker logic to be more generic"
created_at: "2025-12-31T10:05:27Z"
target_module: "src/egregora/orchestration/runner.py"
assigned_persona: "artisan"
---

## Description

The `process_background_tasks` method in `PipelineRunner` contains repetitive code for initializing, running, and logging the results of different worker classes (`BannerWorker`, `ProfileWorker`, `EnrichmentWorker`). This duplication makes the code harder to maintain and extend.

## Task

Refactor the worker execution logic to be more generic. This could involve creating a helper function or a list of worker classes to iterate over, reducing code duplication and making it easier to add new workers in the future.

## Code Snippet

```python
        logger.info("⚙️  [bold cyan]Processing background tasks...[/]")

        banner_worker = BannerWorker(self.context)
        banners_processed = banner_worker.run()
        if banners_processed > 0:
            logger.info("Generated %d banners", banners_processed)

        profile_worker = ProfileWorker(self.context)
        profiles_processed = profile_worker.run()
        if profiles_processed > 0:
            logger.info("Updated %d profiles", profiles_processed)

        enrichment_worker = EnrichmentWorker(self.context)
        enrichment_processed = enrichment_worker.run()
        if enrichment_processed > 0:
            logger.info("Enriched %d items", enrichment_processed)
```
