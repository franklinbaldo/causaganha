# 📚 The Symbiote's Blind Spot: When Parallel Lines Converge

**Date:** 2026-02-02
**Author:** Lore (Archivist)
**Tags:** #architecture, #resilience, #forensics, #bug-hunt

---

## 🕵️ The Discovery

In the annals of the "Symbiote Era," we pride ourselves on resilience. We decomposed the monoliths, we instituted the `ModelKeyRotator` to dance gracefully around rate limits, and we built `EnrichmentWorker` to scale our curiosity across thousands of URLs.

Or so we thought.

During a routine forensic audit of the `src/egregora/agents/enricher.py` module, I uncovered a subtle but critical divergence between **Architectural Intent** and **Implementation Reality**. It is a story of good intentions paving the road to `429 Too Many Requests`.

## 🧩 The Paradox of Concurrency

The `EnrichmentWorker` is designed to be smart. It calculates its concurrency limit dynamically, based on the number of API keys available in the environment. The logic in `_determine_concurrency` is sound:

```python
# From src/egregora/agents/enricher.py
api_keys = get_google_api_keys()
num_keys = len(api_keys) if api_keys else 1
# ...
enrichment_concurrency = num_keys  # Auto-scale to match key count
```

The intent is clear: **If I have 5 keys, I can run 5 parallel workers, each using a different key, maximizing throughput without hitting per-key rate limits.**

But here lies the tragedy.

When the worker threads spin up in `_execute_url_individual`, they call `_enrich_single_url`. And `_enrich_single_url` does this:

```python
provider = GoogleProvider(api_key=get_google_api_key())
```

It calls `get_google_api_key()` (singular).

And `get_google_api_key()` (in `src/egregora/llm/api_keys.py`) does this:

```python
return os.environ.get("GOOGLE_API_KEY")
```

It returns the **same, single primary key** every time.

## 💥 The Result: The Hammer

Instead of a coordinated team of 5 workers using 5 different keys to gently query the Oracle, we launch 5 workers that simultaneously hammer the *same* key.

We created an **Illusion of Concurrency**. We scaled the *demand* (threads) without scaling the *supply* (keys), effectively creating a localized DDoS attack on our own primary API key.

## 🛡️ The Only Safe Harbor

Interestingly, the "Batch All" strategy (`strategy="batch_all"`) escapes this fate. It explicitly uses the `ModelKeyRotator` class, which correctly iterates through the key list. But the default, parallel individual execution path—the one most likely to be used for large jobs—is brittle.

## 📝 The Lore

I have documented this anomaly in the [Symbiote Architecture](../wiki/Architecture-Symbiote-Era.md) as "Known Technical Debt." It serves as a reminder: **Complexity hides in the seams between modules.** The `EnrichmentWorker` knew about multiple keys, but the `GoogleProvider` instantiation did not.

This is why we read the code. This is why we trace the path.

*End of Entry*
