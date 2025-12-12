import pytest

from causaganha_v2.api.models import Intimation


def test_intimation_model_parsing():
    """Test that Intimation model parses expected JSON"""
    data = {
        "id": 123456,
        "numero_processo": "0001234-56.2024.8.22.0001",
        "data_disponibilizacao": "2024-12-01",
        "siglaTribunal": "TJRO",
        "tipoComunicacao": "INTIMACAO",
        "nomeOrgao": "Vara Civel",
        "texto": "Decisao...",
        "link": "https://pje.tjro.jus.br/doc/12345.pdf",
        "tipoDocumento": "Despacho",
        "nomeClasse": "Procedimento Comum",
        "hash": "abc123hash",
        "status": "A",
        "destinatarioadvogados": [
            {
                "advogado": {
                    "id": 1,
                    "nome": "FRANKLIN SILVEIRA BALDO",
                    "numero_oab": "5733",
                    "uf_oab": "RO",
                }
            }
        ],
    }

    intimation = Intimation(**data)

    assert intimation.id == 123456
    assert intimation.siglaTribunal == "TJRO"
    assert len(intimation.destinatarioadvogados) == 1
    assert intimation.destinatarioadvogados[0].advogado.numero_oab == "5733"
