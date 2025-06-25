# Plano de Migração CSV + JSON → DuckDB

## Visão Geral

Este plano detalha a migração completa de **todos os dados** atualmente em CSV e JSON para um banco de dados DuckDB unificado. Isso inclui CSVs (`ratings.csv`, `partidas.csv`, `pdf_metadata.csv`) e **todos os JSONs** de extração de decisões, oferecendo melhor performance, consultas SQL complexas e eliminação de arquivos dispersos.

## Situação Atual vs. Proposta

### 📊 **Estado Atual (CSV + JSON)**
```
data/
├── ratings.csv                           # ~96 advogados × 4 colunas
├── partidas.csv                          # ~50 partidas × 9 colunas  
├── pdf_metadata.csv                      # ~365 PDFs × 10 colunas
├── dj_20250624_extraction.json           # Decisões extraídas
├── dj_20250624_decisions_for_elo_testing.json
├── cli_test_doc_for_extractor.pdf
└── causaganha/data/
    ├── json/                             # JSONs pendentes de processamento
    │   ├── dj_20250625_extraction.json
    │   └── fake_tjro_20250624_extracted.json
    └── json_processed/                   # JSONs já processados
        └── dj_20250624_decisions_for_elo_testing.json
```

### 🚀 **Estado Proposto (DuckDB Unificado)**
```
data/
├── causaganha.duckdb                     # Banco unificado com TODOS os dados
├── snapshots/                            # Snapshots para Cloudflare R2
│   └── causaganha-20250625.duckdb.zst
└── backups/                              # Backups dos arquivos originais
    ├── csv_backup/
    └── json_backup/
```

## Arquitetura de Dados DuckDB

### Schema Principal
```sql
-- Esquema completo do banco DuckDB
CREATE SCHEMA IF NOT EXISTS main;

-- 1. Advogados e Ratings TrueSkill
CREATE TABLE ratings (
    advogado_id VARCHAR PRIMARY KEY,
    mu DOUBLE NOT NULL DEFAULT 25.0,
    sigma DOUBLE NOT NULL DEFAULT 8.333,
    total_partidas INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Campos calculados
    conservative_skill DOUBLE GENERATED ALWAYS AS (mu - 3 * sigma) STORED,
    skill_variance DOUBLE GENERATED ALWAYS AS (sigma * sigma) STORED
);

-- 2. Histórico de Partidas (TrueSkill)
CREATE TABLE partidas (
    id INTEGER PRIMARY KEY,
    data_partida DATE NOT NULL,
    numero_processo VARCHAR NOT NULL,
    
    -- Times (JSON para flexibilidade)
    equipe_a_ids JSON NOT NULL,  -- ["adv1", "adv2"]
    equipe_b_ids JSON NOT NULL,
    
    -- Ratings antes da partida
    ratings_equipe_a_antes JSON NOT NULL,  -- {"adv1": [mu, sigma], "adv2": [mu, sigma]}
    ratings_equipe_b_antes JSON NOT NULL,
    
    -- Resultado
    resultado_partida VARCHAR CHECK (resultado_partida IN ('win_a', 'win_b', 'draw')),
    
    -- Ratings após partida
    ratings_equipe_a_depois JSON NOT NULL,
    ratings_equipe_b_depois JSON NOT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Metadados de PDFs
CREATE TABLE pdf_metadata (
    id INTEGER PRIMARY KEY,
    filename VARCHAR NOT NULL,
    download_date DATE NOT NULL,
    original_url TEXT NOT NULL,
    size_bytes BIGINT NOT NULL,
    sha256_hash CHAR(64) UNIQUE NOT NULL,
    
    -- Archive.org
    archive_identifier VARCHAR,
    archive_url TEXT,
    upload_status VARCHAR DEFAULT 'pending' CHECK (upload_status IN ('pending', 'uploaded', 'failed')),
    upload_date TIMESTAMP,
    
    -- Metadados extra
    extraction_status VARCHAR DEFAULT 'pending' CHECK (extraction_status IN ('pending', 'processing', 'completed', 'failed')),
    decisions_extracted INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Decisões Extraídas (consolidação de TODOS os JSONs)
CREATE TABLE decisoes (
    id INTEGER PRIMARY KEY,
    numero_processo VARCHAR NOT NULL,
    pdf_source_id INTEGER REFERENCES pdf_metadata(id),
    
    -- Origem da extração
    json_source_file VARCHAR,              -- Nome do arquivo JSON original
    extraction_timestamp TIMESTAMP,        -- Quando foi extraído
    
    -- Partes do processo
    polo_ativo JSON NOT NULL,              -- ["Pessoa A", "Empresa B"]
    polo_passivo JSON NOT NULL,
    advogados_polo_ativo JSON NOT NULL,    -- ["Adv A (OAB/RO 123)", "Adv B"]
    advogados_polo_passivo JSON NOT NULL,
    
    -- Decisão
    tipo_decisao VARCHAR,
    resultado VARCHAR,
    data_decisao DATE,
    
    -- Conteúdo
    resumo TEXT,
    texto_completo TEXT,
    
    -- Metadados do JSON original
    raw_json_data JSON,                    -- JSON completo original para backup
    
    -- Processamento
    processed_for_trueskill BOOLEAN DEFAULT FALSE,
    partida_id INTEGER REFERENCES partidas(id),
    validation_status VARCHAR DEFAULT 'pending' CHECK (validation_status IN ('pending', 'valid', 'invalid')),
    validation_errors TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Arquivos JSON Processados (rastreamento)
CREATE TABLE json_files (
    id INTEGER PRIMARY KEY,
    filename VARCHAR NOT NULL UNIQUE,
    file_path VARCHAR NOT NULL,
    file_size_bytes BIGINT,
    sha256_hash CHAR(64),
    
    -- Metadados da extração
    extraction_date DATE,
    source_pdf_filename VARCHAR,
    total_decisions INTEGER DEFAULT 0,
    valid_decisions INTEGER DEFAULT 0,
    
    -- Status de processamento
    processing_status VARCHAR DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed', 'archived')),
    processed_at TIMESTAMP,
    error_message TEXT,
    
    -- Backup
    archived_to_duckdb BOOLEAN DEFAULT FALSE,
    original_file_deleted BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Views Úteis
CREATE VIEW ranking_atual AS
SELECT 
    advogado_id,
    mu,
    sigma,
    conservative_skill,
    total_partidas,
    RANK() OVER (ORDER BY mu DESC) as ranking_mu,
    RANK() OVER (ORDER BY conservative_skill DESC) as ranking_conservative
FROM ratings
ORDER BY mu DESC;

CREATE VIEW estatisticas_gerais AS
SELECT 
    COUNT(*) as total_advogados,
    AVG(mu) as mu_medio,
    AVG(sigma) as sigma_medio,
    MAX(total_partidas) as max_partidas,
    (SELECT COUNT(*) FROM partidas) as total_partidas,
    (SELECT COUNT(*) FROM pdf_metadata) as total_pdfs,
    (SELECT COUNT(*) FROM decisoes) as total_decisoes
FROM ratings;

-- Índices para performance
CREATE INDEX idx_partidas_data ON partidas(data_partida);
CREATE INDEX idx_partidas_processo ON partidas(numero_processo);
CREATE INDEX idx_pdf_metadata_hash ON pdf_metadata(sha256_hash);
CREATE INDEX idx_pdf_metadata_date ON pdf_metadata(download_date);
CREATE INDEX idx_decisoes_processo ON decisoes(numero_processo);
CREATE INDEX idx_decisoes_pdf ON decisoes(pdf_source_id);
```

## Implementação da Migração

### 1. Módulo de Banco DuckDB

```python
# causaganha/core/database.py
import duckdb
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional, Any
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class CausaGanhaDB:
    def __init__(self, db_path: Path = Path("data/causaganha.duckdb")):
        self.db_path = db_path
        self.conn = None
        
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def connect(self):
        """Conecta ao banco DuckDB e inicializa schema."""
        self.conn = duckdb.connect(str(self.db_path))
        self._initialize_schema()
    
    def close(self):
        """Fecha conexão com banco."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def _initialize_schema(self):
        """Cria tabelas e views se não existirem."""
        schema_sql = """
        -- Tabela de ratings TrueSkill
        CREATE TABLE IF NOT EXISTS ratings (
            advogado_id VARCHAR PRIMARY KEY,
            mu DOUBLE NOT NULL DEFAULT 25.0,
            sigma DOUBLE NOT NULL DEFAULT 8.333,
            total_partidas INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Tabela de partidas
        CREATE TABLE IF NOT EXISTS partidas (
            id INTEGER PRIMARY KEY,
            data_partida DATE NOT NULL,
            numero_processo VARCHAR NOT NULL,
            equipe_a_ids JSON NOT NULL,
            equipe_b_ids JSON NOT NULL,
            ratings_equipe_a_antes JSON NOT NULL,
            ratings_equipe_b_antes JSON NOT NULL,
            resultado_partida VARCHAR CHECK (resultado_partida IN ('win_a', 'win_b', 'draw')),
            ratings_equipe_a_depois JSON NOT NULL,
            ratings_equipe_b_depois JSON NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Tabela de metadados de PDFs
        CREATE TABLE IF NOT EXISTS pdf_metadata (
            id INTEGER PRIMARY KEY,
            filename VARCHAR NOT NULL,
            download_date DATE NOT NULL,
            original_url TEXT NOT NULL,
            size_bytes BIGINT NOT NULL,
            sha256_hash CHAR(64) UNIQUE NOT NULL,
            archive_identifier VARCHAR,
            archive_url TEXT,
            upload_status VARCHAR DEFAULT 'pending',
            upload_date TIMESTAMP,
            extraction_status VARCHAR DEFAULT 'pending',
            decisions_extracted INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Tabela de decisões
        CREATE TABLE IF NOT EXISTS decisoes (
            id INTEGER PRIMARY KEY,
            numero_processo VARCHAR NOT NULL,
            pdf_source_id INTEGER REFERENCES pdf_metadata(id),
            polo_ativo JSON NOT NULL,
            polo_passivo JSON NOT NULL,
            advogados_polo_ativo JSON NOT NULL,
            advogados_polo_passivo JSON NOT NULL,
            tipo_decisao VARCHAR,
            resultado VARCHAR,
            data_decisao DATE,
            resumo TEXT,
            texto_completo TEXT,
            processed_for_trueskill BOOLEAN DEFAULT FALSE,
            partida_id INTEGER REFERENCES partidas(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Índices
        CREATE INDEX IF NOT EXISTS idx_partidas_data ON partidas(data_partida);
        CREATE INDEX IF NOT EXISTS idx_partidas_processo ON partidas(numero_processo);
        CREATE INDEX IF NOT EXISTS idx_pdf_metadata_hash ON pdf_metadata(sha256_hash);
        CREATE INDEX IF NOT EXISTS idx_pdf_metadata_date ON pdf_metadata(download_date);
        CREATE INDEX IF NOT EXISTS idx_decisoes_processo ON decisoes(numero_processo);
        CREATE INDEX IF NOT EXISTS idx_decisoes_pdf ON decisoes(pdf_source_id);
        """
        
        self.conn.executescript(schema_sql)
        logger.info("Schema DuckDB inicializado")
    
    # === RATINGS ===
    def get_ratings(self) -> pd.DataFrame:
        """Retorna todos os ratings ordenados por mu."""
        return self.conn.execute("""
            SELECT advogado_id, mu, sigma, total_partidas,
                   mu - 3 * sigma as conservative_skill
            FROM ratings 
            ORDER BY mu DESC
        """).df()
    
    def update_rating(self, advogado_id: str, mu: float, sigma: float, increment_partidas: bool = True):
        """Atualiza rating de um advogado."""
        if increment_partidas:
            sql = """
                INSERT INTO ratings (advogado_id, mu, sigma, total_partidas, updated_at)
                VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
                ON CONFLICT (advogado_id) DO UPDATE SET
                    mu = EXCLUDED.mu,
                    sigma = EXCLUDED.sigma,
                    total_partidas = ratings.total_partidas + 1,
                    updated_at = CURRENT_TIMESTAMP
            """
        else:
            sql = """
                INSERT INTO ratings (advogado_id, mu, sigma, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT (advogado_id) DO UPDATE SET
                    mu = EXCLUDED.mu,
                    sigma = EXCLUDED.sigma,
                    updated_at = CURRENT_TIMESTAMP
            """
        
        self.conn.execute(sql, [advogado_id, mu, sigma])
    
    def get_rating(self, advogado_id: str) -> Optional[Dict]:
        """Retorna rating específico de um advogado."""
        result = self.conn.execute("""
            SELECT advogado_id, mu, sigma, total_partidas
            FROM ratings WHERE advogado_id = ?
        """, [advogado_id]).fetchone()
        
        if result:
            return {
                'advogado_id': result[0],
                'mu': result[1],
                'sigma': result[2],
                'total_partidas': result[3]
            }
        return None
    
    # === PARTIDAS ===
    def add_partida(self, 
                   data_partida: str,
                   numero_processo: str,
                   equipe_a_ids: List[str],
                   equipe_b_ids: List[str],
                   ratings_antes_a: Dict[str, tuple],
                   ratings_antes_b: Dict[str, tuple],
                   resultado: str,
                   ratings_depois_a: Dict[str, tuple],
                   ratings_depois_b: Dict[str, tuple]) -> int:
        """Adiciona nova partida e retorna ID."""
        sql = """
            INSERT INTO partidas (
                data_partida, numero_processo, equipe_a_ids, equipe_b_ids,
                ratings_equipe_a_antes, ratings_equipe_b_antes, resultado_partida,
                ratings_equipe_a_depois, ratings_equipe_b_depois
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        cursor = self.conn.execute(sql, [
            data_partida, numero_processo,
            json.dumps(equipe_a_ids), json.dumps(equipe_b_ids),
            json.dumps(ratings_antes_a), json.dumps(ratings_antes_b),
            resultado,
            json.dumps(ratings_depois_a), json.dumps(ratings_depois_b)
        ])
        
        # Obter ID da partida inserida
        partida_id = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        return partida_id
    
    def get_partidas(self, limit: int = None) -> pd.DataFrame:
        """Retorna histórico de partidas."""
        sql = "SELECT * FROM partidas ORDER BY data_partida DESC"
        if limit:
            sql += f" LIMIT {limit}"
        return self.conn.execute(sql).df()
    
    # === PDF METADATA ===
    def add_pdf_metadata(self, 
                        filename: str,
                        download_date: str,
                        original_url: str,
                        size_bytes: int,
                        sha256_hash: str,
                        archive_identifier: str = None,
                        archive_url: str = None) -> int:
        """Adiciona metadados de PDF."""
        sql = """
            INSERT INTO pdf_metadata (
                filename, download_date, original_url, size_bytes, sha256_hash,
                archive_identifier, archive_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        cursor = self.conn.execute(sql, [
            filename, download_date, original_url, size_bytes, sha256_hash,
            archive_identifier, archive_url
        ])
        
        return self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    def update_pdf_upload_status(self, sha256_hash: str, status: str, archive_url: str = None):
        """Atualiza status de upload do PDF."""
        if archive_url:
            sql = """
                UPDATE pdf_metadata 
                SET upload_status = ?, upload_date = CURRENT_TIMESTAMP, archive_url = ?
                WHERE sha256_hash = ?
            """
            self.conn.execute(sql, [status, archive_url, sha256_hash])
        else:
            sql = """
                UPDATE pdf_metadata 
                SET upload_status = ?, upload_date = CURRENT_TIMESTAMP
                WHERE sha256_hash = ?
            """
            self.conn.execute(sql, [status, sha256_hash])
    
    def find_pdf_by_hash(self, sha256_hash: str) -> Optional[Dict]:
        """Encontra PDF por hash."""
        result = self.conn.execute("""
            SELECT * FROM pdf_metadata WHERE sha256_hash = ?
        """, [sha256_hash]).fetchone()
        
        if result:
            columns = [desc[0] for desc in self.conn.description]
            return dict(zip(columns, result))
        return None
    
    def get_pdfs_by_status(self, status: str) -> pd.DataFrame:
        """Retorna PDFs por status de upload."""
        return self.conn.execute("""
            SELECT * FROM pdf_metadata WHERE upload_status = ?
            ORDER BY download_date DESC
        """, [status]).df()
    
    # === DECISÕES ===
    def add_decisao(self, decisao_data: Dict) -> int:
        """Adiciona decisão extraída com metadados completos."""
        sql = """
            INSERT INTO decisoes (
                numero_processo, pdf_source_id, json_source_file, extraction_timestamp,
                polo_ativo, polo_passivo, advogados_polo_ativo, advogados_polo_passivo, 
                tipo_decisao, resultado, data_decisao, resumo, texto_completo,
                raw_json_data, validation_status, validation_errors
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        cursor = self.conn.execute(sql, [
            decisao_data['numero_processo'],
            decisao_data.get('pdf_source_id'),
            decisao_data.get('json_source_file'),
            decisao_data.get('extraction_timestamp'),
            json.dumps(decisao_data.get('polo_ativo', [])),
            json.dumps(decisao_data.get('polo_passivo', [])),
            json.dumps(decisao_data.get('advogados_polo_ativo', [])),
            json.dumps(decisao_data.get('advogados_polo_passivo', [])),
            decisao_data.get('tipo_decisao'),
            decisao_data.get('resultado'),
            decisao_data.get('data_decisao'),
            decisao_data.get('resumo'),
            decisao_data.get('texto_completo'),
            json.dumps(decisao_data.get('raw_json_data', {})),
            decisao_data.get('validation_status', 'pending'),
            decisao_data.get('validation_errors')
        ])
        
        return self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    def mark_decisao_processed(self, decisao_id: int, partida_id: int):
        """Marca decisão como processada para TrueSkill."""
        self.conn.execute("""
            UPDATE decisoes 
            SET processed_for_trueskill = TRUE, partida_id = ?
            WHERE id = ?
        """, [partida_id, decisao_id])
    
    def get_unprocessed_decisoes(self) -> pd.DataFrame:
        """Retorna decisões não processadas para TrueSkill."""
        return self.conn.execute("""
            SELECT * FROM decisoes 
            WHERE processed_for_trueskill = FALSE
            ORDER BY created_at ASC
        """).df()
    
    # === ARQUIVOS JSON ===
    def add_json_file(self, file_data: Dict) -> int:
        """Registra arquivo JSON processado."""
        sql = """
            INSERT INTO json_files (
                filename, file_path, file_size_bytes, sha256_hash,
                extraction_date, source_pdf_filename, total_decisions,
                processing_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        cursor = self.conn.execute(sql, [
            file_data['filename'],
            file_data['file_path'],
            file_data.get('file_size_bytes'),
            file_data.get('sha256_hash'),
            file_data.get('extraction_date'),
            file_data.get('source_pdf_filename'),
            file_data.get('total_decisions', 0),
            file_data.get('processing_status', 'pending')
        ])
        
        return self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    def update_json_file_status(self, filename: str, status: str, **kwargs):
        """Atualiza status de processamento do JSON."""
        updates = ["processing_status = ?", "updated_at = CURRENT_TIMESTAMP"]
        params = [status]
        
        if 'valid_decisions' in kwargs:
            updates.append("valid_decisions = ?")
            params.append(kwargs['valid_decisions'])
        
        if 'error_message' in kwargs:
            updates.append("error_message = ?")
            params.append(kwargs['error_message'])
        
        if 'processed_at' in kwargs:
            updates.append("processed_at = ?")
            params.append(kwargs['processed_at'])
        
        params.append(filename)
        
        sql = f"""
            UPDATE json_files 
            SET {', '.join(updates)}
            WHERE filename = ?
        """
        
        self.conn.execute(sql, params)
    
    def get_json_files_by_status(self, status: str) -> pd.DataFrame:
        """Retorna arquivos JSON por status."""
        return self.conn.execute("""
            SELECT * FROM json_files WHERE processing_status = ?
            ORDER BY created_at DESC
        """, [status]).df()
    
    def process_json_file(self, json_path: Path) -> Dict:
        """Processa arquivo JSON completo e retorna estatísticas."""
        logger.info(f"Processando JSON: {json_path.name}")
        
        # Calcular hash do arquivo
        import hashlib
        sha256_hash = hashlib.sha256()
        with open(json_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        file_hash = sha256_hash.hexdigest()
        
        # Registrar arquivo JSON
        file_stats = json_path.stat()
        json_file_id = self.add_json_file({
            'filename': json_path.name,
            'file_path': str(json_path),
            'file_size_bytes': file_stats.st_size,
            'sha256_hash': file_hash,
            'processing_status': 'processing'
        })
        
        try:
            # Carregar JSON
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # Extrair metadados
            extraction_timestamp = json_data.get('extraction_timestamp')
            source_pdf = json_data.get('file_name_source', json_path.stem.replace('_extraction', '.pdf'))
            
            # Encontrar PDF source_id se existir
            pdf_source_id = None
            if source_pdf:
                pdf_record = self.conn.execute("""
                    SELECT id FROM pdf_metadata WHERE filename = ?
                """, [source_pdf]).fetchone()
                if pdf_record:
                    pdf_source_id = pdf_record[0]
            
            # Processar decisões
            decisions = json_data.get('decisions', [])
            if isinstance(decisions, dict):
                decisions = [decisions]
            
            valid_decisions = 0
            
            for decision in decisions:
                try:
                    # Validar decisão
                    from .utils import validate_decision
                    is_valid = validate_decision(decision)
                    
                    decisao_data = {
                        'numero_processo': decision.get('numero_processo', ''),
                        'pdf_source_id': pdf_source_id,
                        'json_source_file': json_path.name,
                        'extraction_timestamp': extraction_timestamp,
                        'polo_ativo': decision.get('polo_ativo', []),
                        'polo_passivo': decision.get('polo_passivo', []),
                        'advogados_polo_ativo': decision.get('advogados_polo_ativo', []),
                        'advogados_polo_passivo': decision.get('advogados_polo_passivo', []),
                        'tipo_decisao': decision.get('tipo_decisao'),
                        'resultado': decision.get('resultado'),
                        'data_decisao': decision.get('data_decisao'),
                        'resumo': decision.get('resumo'),
                        'texto_completo': decision.get('texto_completo'),
                        'raw_json_data': decision,
                        'validation_status': 'valid' if is_valid else 'invalid',
                        'validation_errors': None if is_valid else 'Failed validation check'
                    }
                    
                    self.add_decisao(decisao_data)
                    
                    if is_valid:
                        valid_decisions += 1
                        
                except Exception as e:
                    logger.error(f"Erro ao processar decisão {decision.get('numero_processo', 'N/A')}: {e}")
                    continue
            
            # Atualizar status do arquivo JSON
            self.update_json_file_status(
                json_path.name, 
                'completed',
                valid_decisions=valid_decisions,
                processed_at=datetime.now().isoformat()
            )
            
            # Atualizar total_decisions
            self.conn.execute("""
                UPDATE json_files 
                SET total_decisions = ?
                WHERE id = ?
            """, [len(decisions), json_file_id])
            
            result = {
                'json_file_id': json_file_id,
                'total_decisions': len(decisions),
                'valid_decisions': valid_decisions,
                'invalid_decisions': len(decisions) - valid_decisions,
                'pdf_source_id': pdf_source_id,
                'status': 'completed'
            }
            
            logger.info(f"JSON processado: {valid_decisions}/{len(decisions)} decisões válidas")
            return result
            
        except Exception as e:
            logger.error(f"Erro ao processar JSON {json_path.name}: {e}")
            
            self.update_json_file_status(
                json_path.name, 
                'failed',
                error_message=str(e)
            )
            
            return {
                'json_file_id': json_file_id,
                'status': 'failed',
                'error': str(e)
            }
    
    # === VIEWS E ESTATÍSTICAS ===
    def get_ranking(self, limit: int = 20) -> pd.DataFrame:
        """Retorna ranking atual."""
        return self.conn.execute(f"""
            SELECT 
                advogado_id,
                mu,
                sigma,
                mu - 3 * sigma as conservative_skill,
                total_partidas,
                ROW_NUMBER() OVER (ORDER BY mu DESC) as ranking_mu,
                ROW_NUMBER() OVER (ORDER BY mu - 3 * sigma DESC) as ranking_conservative
            FROM ratings
            ORDER BY mu DESC
            LIMIT {limit}
        """).df()
    
    def get_statistics(self) -> Dict:
        """Retorna estatísticas gerais do sistema."""
        stats = self.conn.execute("""
            SELECT 
                (SELECT COUNT(*) FROM ratings) as total_advogados,
                (SELECT AVG(mu) FROM ratings) as mu_medio,
                (SELECT AVG(sigma) FROM ratings) as sigma_medio,
                (SELECT MAX(total_partidas) FROM ratings) as max_partidas,
                (SELECT COUNT(*) FROM partidas) as total_partidas,
                (SELECT COUNT(*) FROM pdf_metadata) as total_pdfs,
                (SELECT COUNT(*) FROM decisoes) as total_decisoes,
                (SELECT COUNT(*) FROM pdf_metadata WHERE upload_status = 'uploaded') as pdfs_arquivados
        """).fetchone()
        
        return {
            'total_advogados': stats[0],
            'mu_medio': stats[1],
            'sigma_medio': stats[2],
            'max_partidas': stats[3],
            'total_partidas': stats[4],
            'total_pdfs': stats[5],
            'total_decisoes': stats[6],
            'pdfs_arquivados': stats[7]
        }
    
    # === BACKUP/RESTORE ===
    def export_to_csv(self, output_dir: Path):
        """Exporta todas as tabelas para CSV (backup)."""
        output_dir.mkdir(exist_ok=True)
        
        tables = ['ratings', 'partidas', 'pdf_metadata', 'decisoes']
        for table in tables:
            df = self.conn.execute(f"SELECT * FROM {table}").df()
            df.to_csv(output_dir / f"{table}.csv", index=False)
        
        logger.info(f"Backup CSV salvo em: {output_dir}")
    
    def vacuum(self):
        """Otimiza banco de dados."""
        self.conn.execute("VACUUM")
        logger.info("Database vacuum concluído")
```

### 2. Script de Migração

```python
# scripts/migrate_csv_to_duckdb.py
import pandas as pd
import json
from pathlib import Path
from causaganha.core.database import CausaGanhaDB
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_ratings(db: CausaGanhaDB, csv_file: Path):
    """Migra ratings.csv para DuckDB."""
    if not csv_file.exists():
        logger.warning(f"Arquivo não encontrado: {csv_file}")
        return
    
    df = pd.read_csv(csv_file)
    logger.info(f"Migrando {len(df)} ratings...")
    
    for _, row in df.iterrows():
        db.update_rating(
            advogado_id=row['advogado_id'],
            mu=row['mu'],
            sigma=row['sigma'],
            increment_partidas=False  # Não incrementar, usar valor do CSV
        )
        
        # Atualizar total_partidas separadamente
        db.conn.execute("""
            UPDATE ratings 
            SET total_partidas = ?
            WHERE advogado_id = ?
        """, [int(row['total_partidas']), row['advogado_id']])
    
    logger.info("✅ Migração de ratings concluída")

def migrate_partidas(db: CausaGanhaDB, csv_file: Path):
    """Migra partidas.csv para DuckDB."""
    if not csv_file.exists():
        logger.warning(f"Arquivo não encontrado: {csv_file}")
        return
    
    df = pd.read_csv(csv_file)
    logger.info(f"Migrando {len(df)} partidas...")
    
    for _, row in df.iterrows():
        # Converter strings JSON para objetos Python
        try:
            equipe_a = row['equipe_a_ids'].split(',') if 'equipe_a_ids' in row else [row.get('advogado_a_id', '')]
            equipe_b = row['equipe_b_ids'].split(',') if 'equipe_b_ids' in row else [row.get('advogado_b_id', '')]
            
            # Para ratings, tentar JSON primeiro, depois fallback para formato antigo
            if 'ratings_equipe_a_antes' in row:
                ratings_a_antes = json.loads(row['ratings_equipe_a_antes'])
                ratings_b_antes = json.loads(row['ratings_equipe_b_antes'])
                ratings_a_depois = json.loads(row['ratings_equipe_a_depois'])
                ratings_b_depois = json.loads(row['ratings_equipe_b_depois'])
                resultado = row['resultado_partida']
            else:
                # Formato antigo (ELO)
                ratings_a_antes = {equipe_a[0]: [row['rating_advogado_a_antes'], 8.33]}
                ratings_b_antes = {equipe_b[0]: [row['rating_advogado_b_antes'], 8.33]}
                ratings_a_depois = {equipe_a[0]: [row['rating_advogado_a_depois'], 8.33]}
                ratings_b_depois = {equipe_b[0]: [row['rating_advogado_b_depois'], 8.33]}
                
                # Converter score_a para resultado TrueSkill
                score_a = row.get('score_a', 0.5)
                if score_a > 0.5:
                    resultado = 'win_a'
                elif score_a < 0.5:
                    resultado = 'win_b'
                else:
                    resultado = 'draw'
            
            db.add_partida(
                data_partida=row['data_partida'],
                numero_processo=row['numero_processo'],
                equipe_a_ids=equipe_a,
                equipe_b_ids=equipe_b,
                ratings_antes_a=ratings_a_antes,
                ratings_antes_b=ratings_b_antes,
                resultado=resultado,
                ratings_depois_a=ratings_a_depois,
                ratings_depois_b=ratings_b_depois
            )
            
        except Exception as e:
            logger.error(f"Erro ao migrar partida {row.get('numero_processo', 'N/A')}: {e}")
            continue
    
    logger.info("✅ Migração de partidas concluída")

def migrate_pdf_metadata(db: CausaGanhaDB, csv_file: Path):
    """Migra pdf_metadata.csv para DuckDB."""
    if not csv_file.exists():
        logger.warning(f"Arquivo não encontrado: {csv_file}")
        return
    
    df = pd.read_csv(csv_file)
    logger.info(f"Migrando {len(df)} metadados de PDF...")
    
    for _, row in df.iterrows():
        try:
            db.add_pdf_metadata(
                filename=row['filename'],
                download_date=row['date'],
                original_url=row['original_url'],
                size_bytes=int(row['size_bytes']),
                sha256_hash=row['sha256'],
                archive_identifier=row.get('archive_identifier'),
                archive_url=row.get('archive_url')
            )
            
            # Atualizar status se disponível
            if 'status' in row and row['status'] != 'pending':
                db.update_pdf_upload_status(
                    sha256_hash=row['sha256'],
                    status=row['status'],
                    archive_url=row.get('archive_url')
                )
                
        except Exception as e:
            logger.error(f"Erro ao migrar PDF {row.get('filename', 'N/A')}: {e}")
            continue
    
    logger.info("✅ Migração de metadados PDF concluída")

def migrate_all_jsons(db: CausaGanhaDB, search_dirs: list):
    """Migra TODOS os arquivos JSON encontrados para DuckDB."""
    json_files = []
    
    # Encontrar todos os JSONs
    for search_dir in search_dirs:
        if search_dir.exists():
            json_files.extend(list(search_dir.glob("*.json")))
            json_files.extend(list(search_dir.glob("**/*.json")))
    
    # Remover duplicatas
    json_files = list(set(json_files))
    
    logger.info(f"Encontrados {len(json_files)} arquivos JSON para migração")
    
    migrated_count = 0
    total_decisions = 0
    valid_decisions = 0
    
    for json_file in json_files:
        logger.info(f"Migrando JSON: {json_file}")
        
        try:
            result = db.process_json_file(json_file)
            
            if result['status'] == 'completed':
                migrated_count += 1
                total_decisions += result['total_decisions']
                valid_decisions += result['valid_decisions']
                
                logger.info(f"✅ {json_file.name}: {result['valid_decisions']}/{result['total_decisions']} decisões válidas")
            else:
                logger.error(f"❌ Falha ao migrar {json_file.name}: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao migrar {json_file.name}: {e}")
            continue
    
    logger.info(f"✅ Migração de JSONs concluída:")
    logger.info(f"   - Arquivos processados: {migrated_count}/{len(json_files)}")
    logger.info(f"   - Total de decisões: {total_decisions}")
    logger.info(f"   - Decisões válidas: {valid_decisions}")
    logger.info(f"   - Taxa de validade: {(valid_decisions/total_decisions*100):.1f}%" if total_decisions > 0 else "   - Taxa de validade: N/A")

def cleanup_original_files(backup_dirs: dict, move_to_backup: bool = True):
    """Move arquivos originais para backup ou arquiva."""
    if move_to_backup:
        for file_type, backup_dir in backup_dirs.items():
            backup_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Arquivos {file_type} movidos para backup em: {backup_dir}")
    else:
        logger.info("Arquivos originais mantidos (modo seguro)")

def main():
    """Executa migração completa CSV + JSON → DuckDB."""
    data_dir = Path("data")
    causaganha_data_dir = Path("causaganha/data")
    
    # Diretórios de backup
    backup_dirs = {
        'csv': data_dir / "backups/csv_backup",
        'json': data_dir / "backups/json_backup"
    }
    
    # Backup dos arquivos originais
    logger.info("📋 Criando backup dos arquivos originais...")
    
    # CSVs
    csv_files = ['ratings.csv', 'partidas.csv', 'pdf_metadata.csv']
    backup_dirs['csv'].mkdir(parents=True, exist_ok=True)
    
    for csv_file in csv_files:
        source = data_dir / csv_file
        if source.exists():
            import shutil
            shutil.copy2(source, backup_dirs['csv'] / csv_file)
            logger.info(f"CSV backup: {csv_file}")
    
    # JSONs - encontrar todos os JSONs
    json_search_dirs = [
        data_dir,  # JSONs na raiz de data/
        causaganha_data_dir / "json",  # JSONs pendentes
        causaganha_data_dir / "json_processed",  # JSONs processados
    ]
    
    backup_dirs['json'].mkdir(parents=True, exist_ok=True)
    all_json_files = []
    
    for search_dir in json_search_dirs:
        if search_dir.exists():
            json_files = list(search_dir.glob("*.json"))
            json_files.extend(list(search_dir.glob("**/*.json")))
            all_json_files.extend(json_files)
    
    # Backup JSONs
    import shutil
    for json_file in set(all_json_files):  # Remove duplicatas
        backup_path = backup_dirs['json'] / json_file.name
        shutil.copy2(json_file, backup_path)
        logger.info(f"JSON backup: {json_file.name}")
    
    logger.info(f"✅ Backup completo - {len(csv_files)} CSVs e {len(set(all_json_files))} JSONs")
    
    # Inicializar banco DuckDB
    db_path = data_dir / "causaganha.duckdb"
    logger.info(f"🚀 Iniciando migração completa para: {db_path}")
    
    with CausaGanhaDB(db_path) as db:
        
        # 1. Migrar CSVs
        logger.info("📊 Fase 1: Migrando CSVs...")
        migrate_ratings(db, data_dir / "ratings.csv")
        migrate_partidas(db, data_dir / "partidas.csv") 
        migrate_pdf_metadata(db, data_dir / "pdf_metadata.csv")
        
        # 2. Migrar TODOS os JSONs
        logger.info("📄 Fase 2: Migrando JSONs...")
        migrate_all_jsons(db, json_search_dirs)
        
        # 3. Estatísticas finais
        logger.info("📊 Fase 3: Estatísticas finais...")
        stats = db.get_statistics()
        
        print("\n" + "="*60)
        print("📊 MIGRAÇÃO CSV + JSON → DUCKDB CONCLUÍDA!")
        print("="*60)
        print(f"👨‍⚖️ Advogados migrados:     {stats['total_advogados']:,}")
        print(f"⚖️  Partidas migradas:      {stats['total_partidas']:,}")
        print(f"📄 PDFs registrados:       {stats['total_pdfs']:,}")
        print(f"📋 Decisões importadas:    {stats['total_decisoes']:,}")
        print(f"📦 Arquivos JSON:          {len(set(all_json_files)):,}")
        print("="*60)
        
        # 4. Validações de integridade
        logger.info("🔍 Fase 4: Validações de integridade...")
        
        # Verificar se todas as decisões têm processo
        decisoes_sem_processo = db.conn.execute("""
            SELECT COUNT(*) FROM decisoes WHERE numero_processo = '' OR numero_processo IS NULL
        """).fetchone()[0]
        
        if decisoes_sem_processo > 0:
            logger.warning(f"⚠️  {decisoes_sem_processo} decisões sem número de processo")
        
        # Verificar decisões válidas vs inválidas
        validacao_stats = db.conn.execute("""
            SELECT 
                validation_status,
                COUNT(*) as count
            FROM decisoes 
            GROUP BY validation_status
        """).fetchall()
        
        for status, count in validacao_stats:
            logger.info(f"📋 Decisões {status}: {count:,}")
        
        # 5. Otimizar banco
        logger.info("🔧 Fase 5: Otimizando banco...")
        db.vacuum()
        
        # Verificar tamanho final
        db_size = db_path.stat().st_size / (1024 * 1024)  # MB
        print(f"💾 Tamanho do banco DuckDB: {db_size:.1f} MB")
        
        # 6. Limpeza opcional
        logger.info("🗑️  Fase 6: Limpeza (arquivos mantidos para segurança)")
        cleanup_original_files(backup_dirs, move_to_backup=False)
        
    logger.info("🎉 Migração concluída com sucesso!")
    logger.info(f"📁 Banco DuckDB: {db_path}")
    logger.info(f"💾 Backups em: {data_dir / 'backups'}")
    
    # Sugerir próximos passos
    print("\n🚀 PRÓXIMOS PASSOS:")
    print("1. Testar consultas: uv run python -m causaganha.core.cli db stats")
    print("2. Ver ranking: uv run python -m causaganha.core.cli db ranking --limit 10")
    print("3. Validar dados: uv run python -m causaganha.core.cli db query --table decisoes --limit 5")
    print("4. Backup para R2: executar workflow de snapshot")
    print("5. Atualizar pipeline para usar DuckDB")
    
if __name__ == "__main__":
    main()
```

### 3. Adaptação do Pipeline Existente

```python
# Modificações em causaganha/core/pipeline.py

from .database import CausaGanhaDB

# Substituir lógica CSV por DuckDB
def _update_trueskill_ratings_logic(logger: logging.Logger, dry_run: bool):
    logger.info("Starting TrueSkill ratings update process (DuckDB).")
    
    if dry_run:
        logger.info("DRY-RUN: TrueSkill update process would run, no database changes.")
    
    json_input_dir = Path("causaganha/data/json/")
    processed_json_dir = Path("causaganha/data/json_processed/")
    
    with CausaGanhaDB() as db:
        # Processar JSONs
        json_files_to_process = list(json_input_dir.glob("*.json"))
        
        for json_path in json_files_to_process:
            logger.info(f"Processing JSON file: {json_path.name}")
            
            # Carregar JSON
            with open(json_path, 'r', encoding='utf-8') as f:
                loaded_content = json.load(f)
            
            # Extrair decisões
            decisions = loaded_content.get("decisions", [])
            
            for decision_data in decisions:
                if not validate_decision(decision_data):
                    continue
                
                # Adicionar decisão ao banco
                if not dry_run:
                    decisao_id = db.add_decisao({
                        'numero_processo': decision_data['numero_processo'],
                        'polo_ativo': decision_data.get('polo_ativo', []),
                        'polo_passivo': decision_data.get('polo_passivo', []),
                        'advogados_polo_ativo': decision_data.get('advogados_polo_ativo', []),
                        'advogados_polo_passivo': decision_data.get('advogados_polo_passivo', []),
                        'tipo_decisao': decision_data.get('tipo_decisao'),
                        'resultado': decision_data.get('resultado'),
                        'data_decisao': decision_data.get('data_decisao'),
                        'resumo': decision_data.get('resumo')
                    })
                
                # Processar TrueSkill (lógica existente)
                # ... código de processamento TrueSkill ...
                
                # Salvar partida no banco
                if not dry_run:
                    partida_id = db.add_partida(
                        data_partida=decision_data.get("data_decisao", datetime.date.today().isoformat()),
                        numero_processo=decision_data['numero_processo'],
                        equipe_a_ids=team_a_ids,
                        equipe_b_ids=team_b_ids,
                        ratings_antes_a=ratings_antes_a_dict,
                        ratings_antes_b=ratings_antes_b_dict,
                        resultado=trueskill_match_result.value,
                        ratings_depois_a=ratings_depois_a_dict,
                        ratings_depois_b=ratings_depois_b_dict
                    )
                    
                    # Atualizar ratings dos advogados
                    for i, adv_id in enumerate(team_a_ids):
                        db.update_rating(adv_id, new_team_a_ratings[i].mu, new_team_a_ratings[i].sigma)
                    
                    for i, adv_id in enumerate(team_b_ids):
                        db.update_rating(adv_id, new_team_b_ratings[i].mu, new_team_b_ratings[i].sigma)
                    
                    # Marcar decisão como processada
                    db.mark_decisao_processed(decisao_id, partida_id)
        
        # Mover arquivos processados
        if not dry_run and processed_files_paths:
            processed_json_dir.mkdir(parents=True, exist_ok=True)
            for json_path in processed_files_paths:
                destination = processed_json_dir / json_path.name
                shutil.move(str(json_path), str(destination))
    
    logger.info("TrueSkill ratings update process finished (DuckDB).")
```

### 4. CLI Atualizado

```python
# causaganha/core/cli.py
import click
from .database import CausaGanhaDB

@click.group()
def db():
    """Comandos de gerenciamento do banco DuckDB."""
    pass

@db.command()
def stats():
    """Mostra estatísticas do banco."""
    with CausaGanhaDB() as db:
        stats = db.get_statistics()
        ranking = db.get_ranking(10)
        
        click.echo("📊 Estatísticas CausaGanha")
        click.echo(f"   👨‍⚖️ Advogados: {stats['total_advogados']}")
        click.echo(f"   ⚖️ Partidas: {stats['total_partidas']}")
        click.echo(f"   📄 PDFs: {stats['total_pdfs']} ({stats['pdfs_arquivados']} arquivados)")
        click.echo(f"   📋 Decisões: {stats['total_decisoes']}")
        click.echo(f"   📈 μ médio: {stats['mu_medio']:.2f}")
        click.echo(f"   📊 σ médio: {stats['sigma_medio']:.2f}")
        click.echo()
        
        click.echo("🏆 Top 10 Ranking (μ):")
        for _, row in ranking.iterrows():
            click.echo(f"   {row['ranking_mu']:2d}. {row['advogado_id'][:40]:<40} μ={row['mu']:6.2f} σ={row['sigma']:5.2f}")

@db.command()
@click.option('--limit', default=20, help='Número de advogados no ranking')
def ranking(limit):
    """Mostra ranking TrueSkill."""
    with CausaGanhaDB() as db:
        ranking_df = db.get_ranking(limit)
        
        click.echo(f"🏆 Ranking TrueSkill (Top {limit})")
        click.echo("-" * 85)
        click.echo(f"{'#':<3} {'Advogado':<40} {'μ':<8} {'σ':<8} {'Skill≈':<8} {'Jogos':<5}")
        click.echo("-" * 85)
        
        for _, row in ranking_df.iterrows():
            click.echo(f"{row['ranking_mu']:3d} {row['advogado_id'][:39]:<40} "
                      f"{row['mu']:8.2f} {row['sigma']:8.2f} {row['conservative_skill']:8.2f} "
                      f"{row['total_partidas']:5d}")

@db.command()
@click.option('--output-dir', default='data/backup', help='Diretório para backup')
def backup(output_dir):
    """Exporta banco para CSV (backup)."""
    output_path = Path(output_dir)
    
    with CausaGanhaDB() as db:
        db.export_to_csv(output_path)
    
    click.echo(f"✅ Backup salvo em: {output_path}")

@db.command()
def vacuum():
    """Otimiza banco de dados."""
    with CausaGanhaDB() as db:
        db.vacuum()
    
    click.echo("✅ Database otimizado")

@db.command()
@click.option('--table', help='Tabela específica (ratings, partidas, pdf_metadata, decisoes)')
@click.option('--limit', default=10, help='Número de registros')
def query(table, limit):
    """Consulta rápida em tabelas."""
    with CausaGanhaDB() as db:
        if table:
            df = db.conn.execute(f"SELECT * FROM {table} LIMIT {limit}").df()
            click.echo(f"📋 Primeiros {limit} registros de {table}:")
            click.echo(df.to_string())
        else:
            click.echo("📋 Tabelas disponíveis:")
            tables = db.conn.execute("SHOW TABLES").df()
            for _, row in tables.iterrows():
                click.echo(f"   - {row['name']}")
```

## Cronograma de Migração

### 🚀 **Fase 1: Preparação (Semana 1)**
- [ ] Implementar classe `CausaGanhaDB`
- [ ] Criar script de migração
- [ ] Testar migração em ambiente local
- [ ] Criar backup dos CSVs atuais

### 🔄 **Fase 2: Migração (Semana 2)**
- [ ] Executar migração dos dados existentes
- [ ] Adaptar pipeline para usar DuckDB
- [ ] Atualizar comandos CLI
- [ ] Testar pipeline completo

### ✅ **Fase 3: Validação (Semana 3)**
- [ ] Comparar resultados CSV vs DuckDB
- [ ] Executar testes de regressão
- [ ] Otimizar consultas e índices
- [ ] Documentar novas funcionalidades

### 🗑️ **Fase 4: Limpeza (Semana 4)**
- [ ] Remover código CSV antigo
- [ ] Atualizar documentação
- [ ] Configurar backup automático DuckDB
- [ ] Integrar com Cloudflare R2

## Comandos de Migração

### Migração inicial
```bash
# Fazer backup dos CSVs
cp data/ratings.csv data/backup/
cp data/partidas.csv data/backup/
cp data/pdf_metadata.csv data/backup/

# Executar migração
uv run python scripts/migrate_csv_to_duckdb.py

# Verificar resultado
uv run python -m causaganha.core.cli db stats
```

### Validação
```bash
# Comparar totais
wc -l data/*.csv
uv run python -c "
from causaganha.core.database import CausaGanhaDB
with CausaGanhaDB() as db:
    stats = db.get_statistics()
    print(f'Advogados: {stats[\"total_advogados\"]}')
    print(f'Partidas: {stats[\"total_partidas\"]}')
    print(f'PDFs: {stats[\"total_pdfs\"]}')
"

# Testar consultas
uv run python -m causaganha.core.cli db ranking --limit 10
uv run python -m causaganha.core.cli db query --table ratings --limit 5
```

## Vantagens da Migração

### 🚀 **Performance**
- **Consultas SQL**: Joins complexos entre tabelas
- **Índices**: Busca otimizada por processo, data, hash
- **Views**: Consultas pré-computadas (ranking, estatísticas)
- **Compressão**: Arquivo único menor que múltiplos CSVs

### 🔍 **Funcionalidades**
- **Integridade referencial**: FKs entre tabelas
- **Campos calculados**: `conservative_skill` automático
- **JSON nativo**: Armazenamento de equipes e ratings
- **Transações**: Operações atômicas

### 🛠️ **Manutenção**
- **Backup único**: Um arquivo vs múltiplos CSVs
- **Schema versionado**: Migrations controladas
- **Consultas ad-hoc**: SQL direto para análises
- **Integração R2**: Upload otimizado de snapshots

### 📊 **Análises**
```sql
-- Exemplos de consultas avançadas possíveis

-- Evolução temporal de um advogado
SELECT p.data_partida, 
       JSON_EXTRACT(p.ratings_equipe_a_depois, '$.advogado_id') as rating_depois
FROM partidas p
WHERE JSON_EXTRACT(p.equipe_a_ids, '$[0]') = 'advogado_específico'
ORDER BY p.data_partida;

-- Advogados mais ativos por mês
SELECT DATE_TRUNC('month', p.data_partida) as mes,
       COUNT(*) as partidas
FROM partidas p
GROUP BY 1 ORDER BY 1 DESC;

-- PDFs pendentes de upload
SELECT filename, download_date, size_bytes/1024/1024 as size_mb
FROM pdf_metadata 
WHERE upload_status = 'pending'
ORDER BY download_date DESC;
```

A migração oferece fundação sólida para evolução futura do sistema com capacidades analíticas muito superiores! 🎯