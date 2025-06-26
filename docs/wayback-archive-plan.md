# Integração com Wayback/Archive.org

Este documento resume como arquivar PDFs do projeto no Internet Archive ("Wayback") usando a API S3-like (via CLI `ia`). A estratégia garante perenidade, gera permalinks e evita custos locais de armazenamento, registrando os metadados em um banco DuckDB local.

## 1. Credenciais e Identificadores

1.  Crie ou utilize sua conta no Archive.org e obtenha as chaves de acesso S3 em <https://archive.org/account/s3.php>. Estas chaves são usadas pela CLI `ia`.
2.  Cada item arquivado precisa de um identificador único no Internet Archive. Utilizamos um slug determinístico gerado a partir do hash SHA256 do conteúdo do PDF:
    ```python
    item_id = "cg-" + sha256_hash[:12]
    # "cg-" é um prefixo para o projeto Causa Ganha.
    ```
3.  O upload é feito usando a CLI `ia upload`.
4.  O Internet Archive aceita arquivos de vários gigabytes.

## 2. Fluxo no Pipeline de Arquivamento

O processo de arquivamento, geralmente executado diariamente para o diário do dia anterior, segue os passos:

```mermaid
graph TD
    A[Baixar PDF do TJRO] --> B[Calcular SHA256 & Coletar Metadata (URL de origem, Data de Publicação)]
    B --> C{PDF já existe no IA? (Verifica via 'ia metadata item_id')}
    C -- Sim --> D[Registra/Atualiza URL do IA e metadata no DuckDB]
    C -- Não --> E[Faz upload para o IA via 'ia upload' com metadata relevante]
    E --> D
```

**Exemplo de Interação (Conceitual):**
O código real está em `causaganha/core/downloader.py` na função `archive_pdf`.

```python
# Exemplo conceitual baseado na implementação atual
import hashlib, subprocess, pathlib, duckdb, datetime

# Supondo que pdf_path, origem_url, data_publicacao são obtidos
pdf_path = pathlib.Path("data/diarios/2024/07/dj_20240701.pdf") # Exemplo
origem_url = "https://www.tjro.jus.br/novodiario/2024/07012024-NR123.pdf" # Exemplo
data_publicacao = datetime.date(2024, 7, 1) # Exemplo

sha256_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
item_id = f"cg-{sha256_hash[:12]}"
ia_filename = pdf_path.name # Nome do arquivo no IA será o mesmo do local

# Verifica se já existe no IA (simplificado)
exists_check = subprocess.run(["ia", "metadata", item_id, "--raw"], capture_output=True, text=True)
if exists_check.returncode != 0:
    # Upload com metadata
    metadata_args = [
        "--metadata", "mediatype:texts",
        "--metadata", "subject:causa_ganha",
        "--metadata", "subject:tjro",
        "--metadata", f"sha256:{sha256_hash}",
        "--metadata", f"originalfilename:{ia_filename}",
        "--metadata", f"sourceurl:{origem_url}",
        "--metadata", f"date:{data_publicacao.isoformat()}" # Publication date
    ]
    subprocess.check_call(
        ["ia", "upload", item_id, str(pdf_path), *metadata_args, "--retries", "5", "--delay", "1"]
    )

archive_ia_url = f"https://archive.org/download/{item_id}/{ia_filename}"

# Conexão e registro no DuckDB
db_connection_path = "data/causaganha.duckdb"
with duckdb.connect(db_connection_path) as con:
    con.execute("""
        CREATE TABLE IF NOT EXISTS pdfs (
            sha256 TEXT PRIMARY KEY,
            item_id TEXT NOT NULL UNIQUE,
            ia_url TEXT NOT NULL,
            origem_url TEXT,
            processo TEXT,
            data_publicacao DATE,
            archived_at TIMESTAMPTZ DEFAULT now()
        );
    """)
    con.execute(
        """
        INSERT INTO pdfs (sha256, item_id, ia_url, origem_url, data_publicacao, processo)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(sha256) DO UPDATE SET
            item_id = excluded.item_id, ia_url = excluded.ia_url,
            origem_url = excluded.origem_url, data_publicacao = excluded.data_publicacao,
            archived_at = now();
        """,
        (sha256_hash, item_id, archive_ia_url, origem_url, data_publicacao, None) # processo é None
    )
```

## 3. GitHub Action para Arquivamento Automático

O arquivamento é automatizado através de uma GitHub Action.

**Arquivo da Workflow:** `.github/workflows/02_archive_to_ia.yml`

```yaml
name: 02 - Archive PDF to Internet Archive

on:
  workflow_dispatch: # Permite disparo manual
  schedule:
    - cron: '15 3 * * *' # Executa diariamente às 03:15 UTC

env:
  IA_ACCESS_KEY: ${{ secrets.IA_ACCESS_KEY }}
  IA_SECRET_KEY: ${{ secrets.IA_SECRET_KEY }}

jobs:
  archive_pdf_to_ia:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install uv (Python package installer)
        uses: astral-sh/setup-uv@v1
      - name: Install dependencies
        run: uv sync --system-site-packages # ou apenas 'uv sync'
      - name: Run Archival Script for Yesterday's PDF
        run: uv run python pipeline/collect_and_archive.py
        # O script pipeline/collect_and_archive.py, quando chamado sem --date ou --latest,
        # automaticamente processa o PDF do dia anterior.
```
Este workflow utiliza as credenciais do Internet Archive armazenadas como secrets no GitHub (`IA_ACCESS_KEY`, `IA_SECRET_KEY`).

## 4. Esquema da Tabela `pdfs` no DuckDB

A tabela `pdfs` armazena os metadados dos arquivos PDF arquivados.

```sql
CREATE TABLE IF NOT EXISTS pdfs (
    sha256 TEXT PRIMARY KEY,          -- Hash SHA256 completo do conteúdo do PDF.
    item_id TEXT NOT NULL UNIQUE,     -- Identificador único do item no Internet Archive (ex: cg-xxxx).
    ia_url TEXT NOT NULL,             -- URL completa para o PDF no Internet Archive.
    origem_url TEXT,                  -- URL original de onde o PDF foi baixado.
    processo TEXT,                    -- Campo para números de processo extraídos do PDF (atualmente NULL, para trabalho futuro).
    data_publicacao DATE,             -- Data oficial de publicação do diário/PDF.
    archived_at TIMESTAMPTZ DEFAULT now() -- Timestamp de quando o registro foi criado/atualizado no banco.
);
```
**Nota sobre `processo` e "Segredo de Justiça":**
*   A coluna `processo` está reservada para armazenar números de processo que podem ser extraídos do conteúdo dos PDFs. Atualmente, esta coluna é populada com `NULL`. A extração e população desta coluna são consideradas trabalhos futuros.
*   A filtragem de PDFs que contenham "Segredo de Justiça" antes do arquivamento é um requisito importante. Esta funcionalidade ainda **não está implementada** no pipeline de arquivamento e necessitará de integração com uma etapa de extração e análise de conteúdo do PDF. Um `TODO` foi adicionado no script `pipeline/collect_and_archive.py` para rastrear esta pendência.

## 5. Pontos de Atenção e Mitigações

| Risco                                       | Mitigação                                                                                                |
|---------------------------------------------|----------------------------------------------------------------------------------------------------------|
| Duplicidade de uploads no Internet Archive  | `item_id` é baseado no `sha256` do arquivo. `ia metadata` verifica a existência antes do upload.           |
| Rate limiting pela API do Internet Archive  | A CLI `ia` implementa retentativas (`--retries 5`) e um pequeno delay (`--delay 1` ou `2`) entre elas.   |
| Arquivamento de PDFs sob Segredo de Justiça | **PENDENTE:** Requer integração com extração de texto para identificar e filtrar tais PDFs antes do upload. |
| Remoção de arquivos do Internet Archive     | Improvável, mas o registro local do hash SHA256 e da URL de origem permite re-upload ou busca em outras fontes. |
| Lock-in com o Internet Archive              | O uso de hashes SHA256 e URLs de origem permite a migração/re-upload para outros serviços de arquivamento. |
| Falhas no download do PDF original          | O pipeline de coleta (`01_collect.yml`) e o script de arquivamento possuem logging para identificar falhas. |

## 6. Roadmap Simplificado (Status Atualizado)

1.  **CONCLUÍDO:** Chaves IA-S3 configuradas como `Actions Secrets`. Testes manuais da CLI `ia` realizados.
2.  **CONCLUÍDO:** Função `archive_pdf()` integrada ao `causaganha/core/downloader.py`, com lógica de verificação de existência, upload e registro no DuckDB.
3.  **CONCLUÍDO:** Tabela `pdfs` no DuckDB criada com o esquema atualizado. Action (`02_archive_to_ia.yml`) configurada para rodar diariamente, processando o PDF do dia anterior.
4.  **PENDENTE (Próxima Sprint):** Implementar worker/verificador que busca por 404s nos `ia_url` registrados e tenta reenviar/corrigir se necessário.
5.  **PENDENTE (Médio Prazo):** Integrar extração de conteúdo para popular a coluna `processo` e implementar o filtro de "Segredo de Justiça".

---
Armazenar os metadados localmente e os PDFs no Internet Archive é uma estratégia robusta e de baixo custo para garantir a perenidade e acessibilidade dos documentos do projeto Causa Ganha.
