# Segmenter Quality Audit (2026-07)

## 1. Per-category Train-Support Report (§5.4)
Computed across the 61 annotation files in `data/segmenter/annotations/`:

| Category | Occurrences |
|---|---|
| acordao_decisorio_fim | 31 |
| acordao_decisorio_inicio | 31 |
| cabecalho_fim | 53 |
| cabecalho_inicio | 53 |
| capitulo_merito_fim | 18 |
| capitulo_merito_inicio | 18 |
| custas_fim | 16 |
| custas_inicio | 16 |
| dispositivo_abertura | 23 |
| ementa_fim | 35 |
| ementa_inicio | 35 |
| encerramento_fim | 27 |
| encerramento_inicio | 27 |
| fundamentacao_legal | 34 |
| honorarios_fim | 12 |
| honorarios_inicio | 12 |
| **preliminar_fim** | **8** |
| **preliminar_inicio** | **8** |
| ref_processual | 57 |
| relatorio_fim | 40 |
| relatorio_inicio | 40 |
| resultado | 58 |
| valor_condenacao | 18 |
| voto_fim | 31 |
| voto_inicio | 31 |

**Categories below §5.4 floor of 10:**
- `preliminar_fim`: 8
- `preliminar_inicio`: 8

No `CRITICAL_CATEGORIES` were below the floor.

## 2. Coverage-Gap Analysis (§5.1)
The following buckets had 0 occurrences for the listed categories:

| Bucket | Categories with 0 occurrences | Classification |
|---|---|---|
| `internet_archive_djen_ocr \| historical_migration_ensemble_verified_train_only \| historical_migration:seed` | custas_fim, custas_inicio, encerramento_fim, preliminar_fim, preliminar_inicio | Suspicious - a directed re-review is warranted, especially for `custas` and `encerramento` which are common. |
| `internet_archive_djen_ocr \| historical_migration_single_pass \| historical_migration:seed` | acordao_decisorio_fim, acordao_decisorio_inicio, capitulo_merito_fim, capitulo_merito_inicio, custas_fim, custas_inicio, dispositivo_abertura, encerramento_fim, encerramento_inicio, fundamentacao_legal, honorarios_fim, honorarios_inicio, preliminar_fim, preliminar_inicio, relatorio_fim, relatorio_inicio, voto_fim, voto_inicio | Suspicious - almost all categories are missing. Directed re-review warranted. |
| `tjro_juris \| historical_migration_model_assisted_correction \| historical_migration:round_e` | capitulo_merito_fim, capitulo_merito_inicio, custas_fim, custas_inicio, dispositivo_abertura, fundamentacao_legal, preliminar_fim, preliminar_inicio | Suspicious - missing `dispositivo_abertura` (critical category). |
| `tjro_juris \| historical_migration_model_assisted_correction \| historical_migration:round_f` | acordao_decisorio_fim, acordao_decisorio_inicio, ementa_fim, ementa_inicio, preliminar_fim, preliminar_inicio, valor_condenacao, voto_fim, voto_inicio | Structurally expected - mostly missing acórdão-specific categories, suggesting this bucket mostly comprises sentenças. |
| `tjro_juris \| historical_migration_single_pass \| historical_migration:juris_expansion` | fundamentacao_legal, honorarios_fim, honorarios_inicio, preliminar_fim, preliminar_inicio | Suspicious - `fundamentacao_legal` should be common. Directed re-review warranted. |
| `tjro_juris \| historical_migration_single_pass \| historical_migration:rounds_abcd_unattributed` | None | N/A |
| `tjro_juris \| independent_full_read \| llm_technique1:batch1` | capitulo_merito_fim, capitulo_merito_inicio, custas_fim, custas_inicio, honorarios_fim, honorarios_inicio, preliminar_fim, preliminar_inicio | Structurally expected - the sample might just lack these specific conditional clauses. |

## 3. Semantic Quality Audit (§3.2)
The semantic audit used heuristics to flag `fundamentacao_legal` and `valor_condenacao` tags collapsed into a single instance per document when `art.` or `R$` appeared multiple times. Manual verification of the 14 flagged documents confirmed that they are true corpus-source data-quality defects (heuristic true positives) where multiple distinct citations/values exist in the text but only one was tagged, violating the guideline to tag "every genuinely distinct amount/citation".

**Flagged Annotations (Corpus-source data-quality defect - §9 risk signal):**
- `doc_0705044238c01d27000e67b6c6f84a6b`: Untagged span: `art. 487, I e III, "b"`
- `doc_10e986e30b77e39227ea3d170755b70a`: Untagged span: `R$ 1.450,00`
- `doc_2239c33a0e57dea3ba4d1759e941be88`: Untagged span: `art. 8º, II, da CF/88`
- `doc_254a21481f0881a28220cd162f7e0c6a`: Untagged span: `art. 38 da Lei 9.099/95`
- `doc_3cffd7961e9fc910f6ae628f5aaa6c40`: Untagged span: `art. 5º, XVII e XX`
- `doc_3d2eb37d242cfb5ebad884e0d1dd109e`: Untagged span: `art. 85, §2º, do CPC/2015`
- `doc_5aebeae7f0c99f1d7e25e14266dffd8f`: Untagged span: `art. 155 do CPP`
- `doc_8dfe37bb8f3a6d0990cf1a74329f4d1a`: Untagged span: `artigo 3º, §2º`
- `doc_9c45d216d09c12dbe0b743e0cff5f139`: Untagged span: `arts. 353 e 354 do CPC c/c art. 355, I`
- `doc_bed363d93062300e16c05c0627d9ac01`: Untagged span: `art. 90, § 3º, do CPC`
- `doc_caaead3cfab9d30deb02c4470bca1274`: Untagged span: `art. 355, I, do CPC`
- `doc_d61aecbf08b525a26f908f655285fe6c`: Untagged span: `R$90.000,00`
- `doc_ee4b584da334febe688125e8d9ad909e`: Untagged span: `R$2.283,32`
- `doc_f22271af51fd1d9e2e0f296aea1b9617`: Untagged span: `art. 840 do Código Civil`

No missing overlapping tags (`ref_normativa` and `fundamentacao_legal`), `ref_processual` mismatching, or excessively long anchor bounds were detected. The heuristic flags for `resultado` on verbs like `negar provimento` were verified as false positives, as these represent the true operative outcome.

## 4. Guideline Gaps & Revision Rationale (§9)
No instruction gaps rising to the bar of a revision were discovered. The manual review found that the guideline is unambiguous in its instructions for multiple single-anchor occurrences (`fundamentacao_legal` and `valor_condenacao`). The defects discovered are cases where the annotators did not follow the clear instructions (data-quality defect), rather than cases where the instructions were ambiguous.

Therefore, **no guideline revision is needed.**
