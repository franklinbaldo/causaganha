# DataJud public API key history

The DataJud API key is public and published by CNJ. Production code keeps the
current key as the configured default in `src/causaganha/config.py`, while
`DATAJUD_API_KEY` remains the runtime override for rotations without deploys.

Use this file as the committed rotation log. When CNJ publishes a new key at
<https://datajud-wiki.cnj.jus.br/api-publica/acesso/>, add a new row at the top,
update local `.env` files and rotate the `DATAJUD_API_KEY` secret in CI/production.
Keep old rows so operators can tell which key was active in historical runs.

| First seen | Source | Status | Public API key |
|---|---|---|---|
| 2026-07-15 | CNJ DataJud wiki / previously embedded client default | Current known working key | `cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw==` |
