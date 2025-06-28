# Prompt Versioning Strategy

This document consolidates the adopted strategy to version all LLM prompts in CausaGanha.
The approach is based on the plan `prompt_versioning_strategy.md` and is now implemented across the pipeline.

Key points:
1. **Semantic naming with content hash** to guarantee immutability.
2. **Automated renaming** via a script that appends the hash and enforces configuration updates.
3. **Central configuration** in `config.toml` storing the exact prompt file in use.

With this procedure, prompt updates remain explicit and reproducible.
