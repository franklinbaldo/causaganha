# Multi-Tribunal Expansion Plan

## Context
Currently, the pipeline is hardcoded or defaults to "TJRO". We need to expand this to support multiple tribunals as per the V2 roadmap.

## Problem
1. `run_collection` pipeline defaults to `["TJRO"]` instead of using the configured `settings.COURTS`.
2. `archive` pipeline generates Internet Archive item IDs with a hardcoded `tjro` infix (e.g., `causaganha-tjro-123`).

## Goals
1. Update `collect.py` to use `settings.COURTS` when no specific courts are provided.
2. Update `archive.py` to dynamically generate item IDs based on the intimation's `sigla_tribunal` (e.g., `causaganha-tjmt-123`).

## Implementation Details

### Collection Pipeline
- **File**: `src/causaganha/pipeline/collect.py`
- **Change**: Import `settings` from `causaganha.config` and replace `["TJRO"]` default with `settings.COURTS`.

### Archive Pipeline
- **File**: `src/causaganha/pipeline/archive.py`
- **Change**: In `_process_intimation`, extract `sigla_tribunal` from the intimation dictionary.
- **Change**: Construct `item_id` using `f"causaganha-{tribunal.lower()}-{intimation_id}"`.
- **Fallback**: If `sigla_tribunal` is missing, fallback to `tjro` or raise an error (decision: fallback to `tjro` for backward compatibility or strict? -> Strict is better for V2, but let's check if existing data has it. Intimation schema has it, so it should be there. Fallback to `tjro` if missing to avoid breaking legacy items if any).

## Testing Strategy
- **Unit/Integration Tests**:
    - `test_pipeline_collect_config.py`: Mock settings and verify `get_intimations_by_court` is called for each configured court.
    - `test_archive_item_id.py`: Mock repository/services and verify `upload_file` is called with correctly formatted `item_id` for different tribunals.
