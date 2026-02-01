# 📚 System Glossary

A canonical list of terms and definitions used within the Egregora system.

## Core Concepts

### Contextual Memory (RAG)
The system's ability to recall and reference previous discussions. This allows posts to create connected narratives rather than isolated snippets.

### Content Discovery (Ranking)
The mechanism by which the system automatically surfaces the most meaningful conversations from a stream of chat logs, prioritizing quality and relevance.

### Persona
A distinct "agentic" role within the Egregora team. There are currently 25 active personas (e.g., *Visionary*, *Artisan*, *Lore*), each with specific responsibilities, tools, and "character arcs." Personas are the primary unit of agency.

## Architecture & Data

### Batch Processing
The current architectural paradigm (Sprint 1) where data is processed in discrete chunks ("windows"). See *Window*.

### Window
A transient view of conversation data used for processing. Windows are computed dynamically and can be defined by:
- **Message Count:** (e.g., 100 messages)
- **Time:** (e.g., 2 hours)
- **Bytes:** (Phase 6 "Modern") Packing messages to maximize context usage (~4 bytes/token).

### Enrichment
The process of augmenting raw text with metadata, summaries, and entity extraction *before* the Writer agent sees it.
- **URL Enrichment:** Fetching and summarizing linked web pages.
- **Media Enrichment:** Describing images, videos, and audio files.

### Document
The core unit of content produced by the pipeline. All documents use content-addressed IDs (UUID v5). Types include:
- `POST`: Blog posts.
- `PROFILE`: Author profiles.
- `JOURNAL`: Execution records for idempotency.
- `ENRICHMENT_*`: Metadata for external resources.

## Future / Moonshots

### Symbiote
The "Moonshot" vision (Sprint 2/3) representing a paradigm shift from **passive archivist** (Batch Processing) to **active collaborator**. The Symbiote intends to participate in conversations in real-time.

### Structured Data Sidecar
A "Quick Win" architecture pattern designed to extract a knowledge graph from conversations one post at a time. It serves as the data foundation for the *Symbiote*.
