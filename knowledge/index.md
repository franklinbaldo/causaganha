# CausaGanha knowledge

This bundle makes stable project-level facts queryable instead of leaving them duplicated across code and RFC prose.

The first slice models the four product data sources and the pipelines that consume them. Pipeline documents keep a natural-key `fonte` field and also link to the corresponding source document, so the bundle supports both relational validation and graph traversal.

The CI check uses `okf-parser`'s current relational-schema implementation to enforce unique source/pipeline names and `Pipeline.fonte -> Fonte.nome` referential integrity.

This layer is intentionally separate from the archived judicial datasets themselves: OKF describes the product's knowledge and contracts; Parquet/DuckDB remain the data plane.
