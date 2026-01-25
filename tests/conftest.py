"""Shared fixtures for tests."""


def create_mock_intimation_item(item_id: int) -> dict:
    """Creates a single mock intimation item compliant with the schema."""
    return {
        "id": item_id,
        "data_disponibilizacao": "2024-12-01",
        "siglaTribunal": "TJRO",
        "tipoComunicacao": "Intimacao",
        "nomeOrgao": "Vara Civel",
        "texto": f"Decisao {item_id}...",
        "numero_processo": f"0001234-56.2024.8.22.{item_id:04d}",
        "meio": "Diário de Justiça Eletrônico",
        "link": f"https://pje.tjro.jus.br/doc/{item_id}.pdf",
        "tipoDocumento": "Despacho",
        "nomeClasse": "Procedimento Comum",
        "codigoClasse": "123",
        "numeroComunicacao": 9876 + item_id,
        "ativo": True,
        "hash": f"abc{item_id}hash",
        "datadisponibilizacao": "2024-12-01T00:00:00",
        "meiocompleto": "DJ",
        "numeroprocessocommascara": f"0001234-56.2024.8.22.{item_id:04d}",
        "destinatarios": [],
        "destinatarioadvogados": [],
    }
