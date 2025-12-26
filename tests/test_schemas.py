
from causaganha.api.schemas import Intimation


def test_intimation_schema_parsing() -> None:
    """Test that Intimation schema parses expected JSON."""
    data = {
        "id": 123456,
        "data_disponibilizacao": "2024-12-01",
        "siglaTribunal": "TJRO",
        "tipoComunicacao": "Intimacao",
        "nomeOrgao": "Vara Civel",
        "texto": "Decisao...",
        "numero_processo": "0001234-56.2024.8.22.0001",
        "meio": "Diário de Justiça Eletrônico",
        "link": "https://pje.tjro.jus.br/doc/12345.pdf",
        "tipoDocumento": "Despacho",
        "nomeClasse": "Procedimento Comum",
        "codigoClasse": "123",
        "numeroComunicacao": 9876,
        "ativo": True,
        "hash": "abc123hash",
        "datadisponibilizacao": "2024-12-01T00:00:00",
        "meiocompleto": "DJ",
        "numeroprocessocommascara": "0001234-56.2024.8.22.0001",
        "destinatarios": [],
        "destinatarioadvogados": [
            {
                "advogado": {
                    "id": 1,
                    "nome": "FRANKLIN SILVEIRA BALDO",
                    "numero_oab": "5733",
                    "uf_oab": "RO",
                },
            },
        ],
    }

    intimation = Intimation(**data)

    assert intimation.id == 123456
    assert intimation.sigla_tribunal == "TJRO"
    assert len(intimation.destinatarioadvogados) == 1
    assert intimation.destinatarioadvogados[0].advogado.numero_oab == "5733"
