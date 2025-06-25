# causaganha/core/migration.py
"""
Script de migração para converter dados CSV e JSON existentes para DuckDB.

Migra:
- ratings.csv -> tabela ratings
- partidas.csv -> tabela partidas
- *.json (extração) -> tabelas decisoes + json_files
"""

import json
import csv
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, date
import pandas as pd
import logging

from .database import CausaGanhaDB

logger = logging.getLogger(__name__)


class CausaGanhaMigration:
    """Classe para migração de dados CSV/JSON para DuckDB."""
    
    def __init__(self, 
                 data_dir: Path = Path("causaganha/data"),
                 root_data_dir: Path = Path("data"),
                 db_path: Path = Path("data/causaganha.duckdb")):
        self.data_dir = data_dir
        self.root_data_dir = root_data_dir
        self.db_path = db_path
        self.stats = {
            'ratings_migrated': 0,
            'partidas_migrated': 0,
            'decisoes_migrated': 0,
            'json_files_migrated': 0,
            'errors': []
        }
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """Calcula SHA-256 hash de um arquivo."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def migrate_ratings_csv(self, db: CausaGanhaDB) -> bool:
        """Migra dados do ratings.csv para tabela ratings."""
        ratings_file = self.data_dir / "ratings.csv"
        
        if not ratings_file.exists():
            logger.warning(f"Arquivo não encontrado: {ratings_file}")
            return False
        
        try:
            logger.info(f"Migrando ratings de: {ratings_file}")
            
            # Ler CSV
            ratings_df = pd.read_csv(ratings_file)
            
            # Migrar cada registro usando métodos do CausaGanhaDB
            for _, row in ratings_df.iterrows():
                # Verificar se já existe
                existing = db.get_rating(row['advogado_id'])
                
                if not existing:
                    # Inserir diretamente com total_partidas correto
                    db.conn.execute("""
                        INSERT INTO ratings (advogado_id, mu, sigma, total_partidas, created_at, updated_at)
                        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, [row['advogado_id'], float(row['mu']), float(row['sigma']), int(row['total_partidas'])])
                    
                    self.stats['ratings_migrated'] += 1
                else:
                    logger.debug(f"Rating já existe: {row['advogado_id']}")
            
            logger.info(f"✅ Ratings migrados: {self.stats['ratings_migrated']}")
            return True
            
        except Exception as e:
            error_msg = f"Erro migrando ratings: {e}"
            logger.error(error_msg)
            self.stats['errors'].append(error_msg)
            return False
    
    def migrate_partidas_csv(self, db: CausaGanhaDB) -> bool:
        """Migra dados do partidas.csv para tabela partidas."""
        partidas_file = self.data_dir / "partidas.csv"
        
        if not partidas_file.exists():
            logger.warning(f"Arquivo não encontrado: {partidas_file}")
            return False
        
        try:
            logger.info(f"Migrando partidas de: {partidas_file}")
            
            # Ler CSV
            partidas_df = pd.read_csv(partidas_file)
            
            # Migrar cada registro
            # Obter próximo ID
            max_id_result = db.conn.execute("SELECT COALESCE(MAX(id), 0) FROM partidas").fetchone()
            max_id = max_id_result[0] if max_id_result else 0
            next_id = max_id + 1
            
            for _, row in partidas_df.iterrows():
                # Parsear dados JSON dos CSVs
                try:
                    # Converter strings de times para listas
                    if isinstance(row['equipe_a_ids'], str):
                        equipe_a_ids = row['equipe_a_ids'].split(',') if ',' in row['equipe_a_ids'] else [row['equipe_a_ids']]
                    else:
                        equipe_a_ids = [row['equipe_a_ids']]
                    
                    if isinstance(row['equipe_b_ids'], str):
                        equipe_b_ids = row['equipe_b_ids'].split(',') if ',' in row['equipe_b_ids'] else [row['equipe_b_ids']]
                    else:
                        equipe_b_ids = [row['equipe_b_ids']]
                    
                    # Parsear ratings JSON
                    ratings_a_antes = json.loads(row['ratings_equipe_a_antes'])
                    ratings_b_antes = json.loads(row['ratings_equipe_b_antes'])
                    ratings_a_depois = json.loads(row['ratings_equipe_a_depois'])
                    ratings_b_depois = json.loads(row['ratings_equipe_b_depois'])
                    
                    # Verificar se já existe
                    existing = db.conn.execute("""
                        SELECT COUNT(*) FROM partidas 
                        WHERE numero_processo = ? AND data_partida = ?
                    """, [row['numero_processo'], row['data_partida']]).fetchone()
                    
                    if existing[0] == 0:
                        # Inserir nova partida
                        db.conn.execute("""
                            INSERT INTO partidas (
                                id, data_partida, numero_processo, equipe_a_ids, equipe_b_ids,
                                ratings_equipe_a_antes, ratings_equipe_b_antes, resultado_partida,
                                ratings_equipe_a_depois, ratings_equipe_b_depois, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """, [
                            next_id, row['data_partida'], row['numero_processo'],
                            json.dumps(equipe_a_ids), json.dumps(equipe_b_ids),
                            json.dumps(ratings_a_antes), json.dumps(ratings_b_antes),
                            row['resultado_partida'],
                            json.dumps(ratings_a_depois), json.dumps(ratings_b_depois)
                        ])
                        
                        self.stats['partidas_migrated'] += 1
                        next_id += 1
                    else:
                        logger.debug(f"Partida já existe: {row['numero_processo']}")
                        
                except Exception as row_error:
                    logger.error(f"Erro processando linha: {row_error}")
                    continue
            
            logger.info(f"✅ Partidas migradas: {self.stats['partidas_migrated']}")
            return True
            
        except Exception as e:
            error_msg = f"Erro migrando partidas: {e}"
            logger.error(error_msg)
            self.stats['errors'].append(error_msg)
            return False
    
    def migrate_json_files(self, db: CausaGanhaDB) -> bool:
        """Migra arquivos JSON de extração para tabelas decisoes e json_files."""
        json_patterns = [
            self.root_data_dir / "*.json",
            self.data_dir / "json" / "*.json",
            self.data_dir / "json_processed" / "*.json"
        ]
        
        json_files = []
        for pattern_path in json_patterns:
            json_files.extend(pattern_path.parent.glob(pattern_path.name))
        
        if not json_files:
            logger.warning("Nenhum arquivo JSON encontrado")
            return False
        
        try:
            logger.info(f"Migrando {len(json_files)} arquivos JSON")
            
            # Obter próximos IDs
            max_decisao_result = db.conn.execute("SELECT COALESCE(MAX(id), 0) FROM decisoes").fetchone()
            max_json_result = db.conn.execute("SELECT COALESCE(MAX(id), 0) FROM json_files").fetchone()
            max_decisao_id = max_decisao_result[0] if max_decisao_result else 0
            max_json_id = max_json_result[0] if max_json_result else 0
            next_decisao_id = max_decisao_id + 1
            next_json_id = max_json_id + 1
            
            for json_file in json_files:
                try:
                    logger.info(f"Processando: {json_file}")
                    
                    # Verificar se arquivo JSON já foi migrado
                    existing_json = db.conn.execute("""
                        SELECT COUNT(*) FROM json_files WHERE filename = ?
                    """, [json_file.name]).fetchone()
                    
                    if existing_json[0] > 0:
                        logger.debug(f"Arquivo JSON já migrado: {json_file.name}")
                        continue
                    
                    # Ler arquivo JSON
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Calcular hash e metadados do arquivo
                    file_hash = self.calculate_file_hash(json_file)
                    file_stats = json_file.stat()
                    
                    # Extrair data do nome do arquivo (ex: dj_20250624_extraction.json)
                    extraction_date = None
                    if 'dj_' in json_file.name:
                        try:
                            date_str = json_file.name.split('_')[1]  # 20250624
                            extraction_date = datetime.strptime(date_str, '%Y%m%d').date()
                        except:
                            pass
                    
                    # Criar registro do arquivo JSON
                    db.conn.execute("""
                        INSERT INTO json_files (
                            id, filename, file_path, file_size_bytes, sha256_hash,
                            extraction_date, source_pdf_filename, total_decisions, valid_decisions,
                            processing_status, processed_at, archived_to_duckdb, 
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, [
                        next_json_id, json_file.name, str(json_file), file_stats.st_size, file_hash,
                        extraction_date, data.get('file_name_source'), len(data.get('decisions', [])), 0,
                        'completed', datetime.now(), True
                    ])
                    
                    self.stats['json_files_migrated'] += 1
                    next_json_id += 1
                    
                    # Migrar decisões (versão simplificada)
                    valid_decisions = 0
                    for decision_data in data.get('decisions', []):
                        try:
                            numero_processo = decision_data.get('numero_processo', '')
                            if not numero_processo:
                                continue
                            
                            # Verificar se decisão já existe
                            existing_decisao = db.conn.execute("""
                                SELECT COUNT(*) FROM decisoes 
                                WHERE numero_processo = ? AND json_source_file = ?
                            """, [numero_processo, json_file.name]).fetchone()
                            
                            if existing_decisao[0] > 0:
                                continue
                            
                            # Inserir decisão
                            db.conn.execute("""
                                INSERT INTO decisoes (
                                    id, numero_processo, json_source_file, 
                                    polo_ativo, polo_passivo, advogados_polo_ativo, advogados_polo_passivo,
                                    tipo_decisao, resultado, resumo, raw_json_data,
                                    processed_for_trueskill, validation_status, created_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                            """, [
                                next_decisao_id, numero_processo, json_file.name,
                                json.dumps(decision_data.get('polo_ativo', [])),
                                json.dumps(decision_data.get('polo_passivo', [])),
                                json.dumps(decision_data.get('advogados_polo_ativo', [])),
                                json.dumps(decision_data.get('advogados_polo_passivo', [])),
                                decision_data.get('tipo_decisao'),
                                decision_data.get('resultado'),
                                decision_data.get('resumo'),
                                json.dumps(decision_data),
                                False, 'pending'
                            ])
                            
                            self.stats['decisoes_migrated'] += 1
                            valid_decisions += 1
                            next_decisao_id += 1
                            
                        except Exception as decision_error:
                            logger.error(f"Erro processando decisão: {decision_error}")
                            continue
                    
                    # Atualizar contagem de decisões válidas
                    db.conn.execute("""
                        UPDATE json_files SET valid_decisions = ? WHERE id = ?
                    """, [valid_decisions, next_json_id - 1])
                    
                except Exception as file_error:
                    logger.error(f"Erro processando arquivo {json_file}: {file_error}")
                    continue
            
            logger.info(f"✅ Arquivos JSON migrados: {self.stats['json_files_migrated']}")
            logger.info(f"✅ Decisões migradas: {self.stats['decisoes_migrated']}")
            return True
            
        except Exception as e:
            error_msg = f"Erro migrando arquivos JSON: {e}"
            logger.error(error_msg)
            self.stats['errors'].append(error_msg)
            return False
    
    def create_backup(self) -> bool:
        """Cria backup dos arquivos originais antes da migração."""
        backup_dir = self.root_data_dir / "backup_pre_migration"
        backup_dir.mkdir(exist_ok=True)
        
        try:
            # Backup CSVs
            for csv_file in [self.data_dir / "ratings.csv", self.data_dir / "partidas.csv"]:
                if csv_file.exists():
                    backup_file = backup_dir / csv_file.name
                    backup_file.write_bytes(csv_file.read_bytes())
                    logger.info(f"Backup criado: {backup_file}")
            
            # Backup JSONs seria muito grande, apenas logar localização
            logger.info(f"Backup de CSVs salvo em: {backup_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Erro criando backup: {e}")
            return False
    
    def run_migration(self, create_backup: bool = True) -> Dict[str, Any]:
        """Executa migração completa."""
        logger.info("🚀 Iniciando migração CSV/JSON → DuckDB")
        
        # Criar backup
        if create_backup:
            self.create_backup()
        
        # Conectar ao banco
        with CausaGanhaDB(self.db_path) as db:
            logger.info(f"Conectado ao DuckDB: {self.db_path}")
            
            # Migrar ratings
            self.migrate_ratings_csv(db)
            
            # Migrar partidas
            self.migrate_partidas_csv(db)
            
            # Migrar JSONs
            self.migrate_json_files(db)
            
            # Estatísticas finais
            final_stats = db.get_statistics()
        
        # Relatório final
        logger.info("📊 RELATÓRIO DE MIGRAÇÃO:")
        logger.info(f"  Ratings migrados: {self.stats['ratings_migrated']}")
        logger.info(f"  Partidas migradas: {self.stats['partidas_migrated']}")
        logger.info(f"  Decisões migradas: {self.stats['decisoes_migrated']}")
        logger.info(f"  Arquivos JSON migrados: {self.stats['json_files_migrated']}")
        
        if self.stats['errors']:
            logger.warning(f"  Erros encontrados: {len(self.stats['errors'])}")
            for error in self.stats['errors']:
                logger.warning(f"    - {error}")
        
        logger.info("📈 ESTATÍSTICAS DO BANCO:")
        for key, value in final_stats.items():
            logger.info(f"  {key}: {value}")
        
        # Retornar resultado
        return {
            'success': len(self.stats['errors']) == 0,
            'migration_stats': self.stats,
            'database_stats': final_stats
        }


def main():
    """Função principal para executar migração via CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrar dados CSV/JSON para DuckDB')
    parser.add_argument('--no-backup', action='store_true', help='Não criar backup dos arquivos originais')
    parser.add_argument('--db-path', default='data/causaganha.duckdb', help='Caminho do banco DuckDB')
    parser.add_argument('--data-dir', default='causaganha/data', help='Diretório de dados')
    parser.add_argument('--root-data-dir', default='data', help='Diretório raiz de dados')
    
    args = parser.parse_args()
    
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Executar migração
    migration = CausaGanhaMigration(
        data_dir=Path(args.data_dir),
        root_data_dir=Path(args.root_data_dir),
        db_path=Path(args.db_path)
    )
    
    result = migration.run_migration(create_backup=not args.no_backup)
    
    if result['success']:
        logger.info("✅ Migração concluída com sucesso!")
        exit(0)
    else:
        logger.error("❌ Migração concluída com erros!")
        exit(1)


if __name__ == "__main__":
    main()