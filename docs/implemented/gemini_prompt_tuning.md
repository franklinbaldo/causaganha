# Gemini Prompt Tuning for Legal Text

This document summarizes the research conducted on effective prompt tuning strategies when using Google Gemini models for Portuguese judicial documents.

## Key Findings
- **Contextual Examples**: Providing short examples of desired output significantly improves entity extraction accuracy.
- **Terminology Lists**: Supplying domain-specific terms helps the model avoid hallucinations and ensures consistency.
- **Temperature Control**: Lowering temperature to `0.2` yields more deterministic completions for legal summaries.
- **Chunking Large Inputs**: Splitting long decisions into ~2k token chunks prevents loss of information while keeping latency reasonable.

## Recommended Prompt Template
```text
Você é um assistente jurídico. Extraia as entidades principais da decisão a seguir e apresente um resumo conciso.
```
Include two or three short examples before the actual decision text.

Research performed on 2025‑06‑28.
