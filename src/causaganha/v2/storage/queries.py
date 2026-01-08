"""Common analytical queries using Ibis"""

import ibis
from ibis import _
from datetime import date, timedelta
import structlog

logger = structlog.get_logger()

def get_unanalyzed_intimations(
    con: ibis.BaseBackend,
    limit: int = 100
) -> list:
    """Get intimations that need PDF analysis"""

    intimations = con.table('intimations')

    result = (
        intimations
        .filter(_.analyzed == False)
        .filter(_.link.notnull())
        .order_by(_.data_disponibilizacao.desc())
        .limit(limit)
    )

    return result.to_pandas().to_dict('records')

def store_intimations(
    con: ibis.BaseBackend,
    intimations: list
) -> int:
    """
    Store intimations in database

    Returns count of new records inserted
    """
    if not intimations:
        return 0

    # Prepare records
    records = []
    for item in intimations:
        records.append({
            'id': item.id,
            'numero_processo': item.numero_processo,
            'numeroprocessocommascara': item.numeroprocessocommascara,
            'data_disponibilizacao': item.data_disponibilizacao,
            'sigla_tribunal': item.siglaTribunal,
            'id_orgao': item.idOrgao,
            'tipo_comunicacao': item.tipoComunicacao,
            'nome_orgao': item.nomeOrgao,
            'texto': item.texto,
            'link': item.link,
            'tipo_documento': item.tipoDocumento,
            'nome_classe': item.nomeClasse,
            'codigo_classe': item.codigoClasse,
            'hash': item.hash,
            'status': item.status,
            'analyzed': False
        })

    # Use raw SQL for upsert (Ibis doesn't have native upsert yet)
    inserted = 0
    for record in records:
        try:
            # Escape strings safely
            nome_orgao = record['nome_orgao'].replace("'", "''")
            texto = record['texto'].replace("'", "''")
            link = record['link'].replace("'", "''")
            tipo_documento = record['tipo_documento'].replace("'", "''")
            nome_classe = record['nome_classe'].replace("'", "''")

            con.raw_sql(f"""
                INSERT INTO intimations (
                    id, numero_processo, numeroprocessocommascara,
                    data_disponibilizacao, sigla_tribunal, id_orgao,
                    tipo_comunicacao, nome_orgao, texto, link,
                    tipo_documento, nome_classe, codigo_classe,
                    hash, status, analyzed
                ) VALUES (
                    {record['id']},
                    '{record['numero_processo']}',
                    '{record['numeroprocessocommascara'] or ''}',
                    '{record['data_disponibilizacao']}',
                    '{record['sigla_tribunal']}',
                    {record['id_orgao'] or 'NULL'},
                    '{record['tipo_comunicacao']}',
                    '{nome_orgao}',
                    '{texto}',
                    '{link}',
                    '{tipo_documento}',
                    '{nome_classe}',
                    '{record['codigo_classe'] or ''}',
                    '{record['hash']}',
                    '{record['status']}',
                    FALSE
                )
                ON CONFLICT (id) DO UPDATE SET
                    updated_at = CURRENT_TIMESTAMP
            """)
            inserted += 1
        except Exception as e:
            logger.warning("insert_failed",
                          intimation_id=record['id'],
                          error=str(e))

    logger.info("intimations_stored", inserted=inserted, total=len(records))
    return inserted

def store_lawyer_associations(
    con: ibis.BaseBackend,
    intimation_id: int,
    lawyers: list
) -> int:
    """Store lawyer associations for an intimation"""

    inserted = 0
    for lawyer_data in lawyers:
        advogado = lawyer_data.get('advogado', {})

        try:
            con.raw_sql(f"""
                INSERT INTO intimation_lawyers (
                    intimation_id, oab_number, oab_state, lawyer_name
                ) VALUES (
                    {intimation_id},
                    '{advogado.get('numero_oab', '')}',
                    '{advogado.get('uf_oab', '')}',
                    '{advogado.get('nome', '').replace("'", "''")}'
                )
                ON CONFLICT DO NOTHING
            """)
            inserted += 1
        except Exception as e:
            logger.warning("lawyer_association_failed",
                          intimation_id=intimation_id,
                          error=str(e))

    return inserted

def get_recent_analyses(
    con: ibis.BaseBackend,
    days: int = 7
) -> list:
    """Get recent decision analyses"""

    analysis = con.table('decision_analysis')

    cutoff = date.today() - timedelta(days=days)

    result = (
        analysis
        .filter(_.created_at >= cutoff)
        .order_by(_.created_at.desc())
    )

    return result.to_pandas().to_dict('records')

def get_lawyer_stats(
    con: ibis.BaseBackend,
    oab_number: str,
    oab_state: str
) -> dict:
    """Get statistics for a specific lawyer"""

    analysis = con.table('decision_analysis')

    # Wins
    wins = (
        analysis
        .filter(_.winner_lawyer_oab == oab_number)
        .filter(_.winner_lawyer_state == oab_state)
        .count()
        .execute()
    )

    # Losses
    losses = (
        analysis
        .filter(_.loser_lawyer_oab == oab_number)
        .filter(_.loser_lawyer_state == oab_state)
        .count()
        .execute()
    )

    return {
        'oab_number': oab_number,
        'oab_state': oab_state,
        'wins': wins,
        'losses': losses,
        'total': wins + losses,
        'win_rate': wins / (wins + losses) if (wins + losses) > 0 else 0
    }
