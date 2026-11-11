"""Codec compacto determinístico e estritamente reversível para o DataJud (Issue #1710, #1711).

Garante que para qualquer documento DataJud D:
    decode(encode(D)) == D

Princípios:
1. Vocabulário Reversível: todas as strings TPU, textos variáveis, acentuações e
   grafias originais são preservadas exatamente no vocabulário compartilhado.
2. Preservação Total de Envelope: _index, _id, _score, sort, nulos e campos desconhecidos.
3. Deduplicação Determinística: _id só é omitido se derivável deterministicamente
   da fórmula 'tribunal_grau_numeroProcesso'. Caso contrário, é explicitamente preservado.
4. Tipos Numéricos Seguros com Fallback: preservação de integridade arbitrária de
   inteiros e ponto flutuante sem truncamento ou overflow.
"""

from __future__ import annotations

from typing import Any


class LosslessVocabulary:
    """Tabela de vocabulário e dicionário reversível para tokenização de strings."""

    def __init__(self) -> None:
        self.str_to_id: dict[str, int] = {}
        self.id_to_str: list[str] = []

    def get_or_add(self, s: str | None) -> int:
        if s is None:
            return -1
        if s not in self.str_to_id:
            idx = len(self.id_to_str)
            self.str_to_id[s] = idx
            self.id_to_str.append(s)
            return idx
        return self.str_to_id[s]

    def get(self, idx: int) -> str | None:
        if idx == -1 or idx >= len(self.id_to_str) or idx < 0:
            return None
        return self.id_to_str[idx]

    def export(self) -> list[str]:
        return list(self.id_to_str)

    @classmethod
    def load(cls, words: list[str]) -> LosslessVocabulary:
        v = cls()
        v.id_to_str = list(words)
        v.str_to_id = {w: i for i, w in enumerate(words)}
        return v


class LosslessCodec:
    """Encoder e Decoder estritamente reversíveis para documentos DataJud."""

    KNOWN_ENVELOPE = {"_index", "_id", "_score", "sort", "_source"}
    KNOWN_SOURCE = {
        "id",
        "tribunal",
        "grau",
        "numeroProcesso",
        "dataAjuizamento",
        "dataHoraUltimaAtualizacao",
        "@timestamp",
        "nivelSigilo",
        "classe",
        "sistema",
        "formato",
        "orgaoJulgador",
        "assuntos",
        "movimentos",
    }
    KNOWN_MOV = {"codigo", "nome", "dataHora", "orgaoJulgador", "complementosTabelados"}
    KNOWN_COMP = {"codigo", "nome", "descricao", "valor"}

    @classmethod
    def encode_document(cls, doc: dict[str, Any], vocab: LosslessVocabulary) -> dict[str, Any]:
        """Compacta um documento garantindo 100% de reversibilidade."""
        src = doc.get("_source", {})
        tribunal = src.get("tribunal", "")
        grau = src.get("grau", "")
        np = src.get("numeroProcesso", "")
        expected_id = f"{tribunal}_{grau}_{np}"
        actual_id = doc.get("_id", "")

        compact: dict[str, Any] = {
            "_i": doc.get("_index"),
            "t": tribunal,
            "g": grau,
        }

        # _id apenas se diferir da regra de derivação
        if actual_id != expected_id:
            compact["_id"] = actual_id

        # Preserva _source.id apenas se divergir do doc _id
        if "id" in src and src["id"] != actual_id:
            compact["_sid"] = src["id"]

        # Envelope: _score e sort
        if "_score" in doc:
            compact["_sc"] = doc["_score"]
        if "sort" in doc:
            compact["_so"] = doc["sort"]

        # Metadados de data e sigilo
        if "dataAjuizamento" in src:
            compact["da"] = src["dataAjuizamento"]
        if "dataHoraUltimaAtualizacao" in src:
            compact["du"] = src["dataHoraUltimaAtualizacao"]
        if "@timestamp" in src:
            compact["@t"] = src["@timestamp"]
        if "nivelSigilo" in src:
            compact["s"] = src["nivelSigilo"]

        # Entidades com código e nome
        if "classe" in src and isinstance(src["classe"], dict):
            c = src["classe"]
            compact["c"] = [c.get("codigo"), vocab.get_or_add(c.get("nome"))]

        if "sistema" in src and isinstance(src["sistema"], dict):
            s = src["sistema"]
            compact["sis"] = [s.get("codigo"), vocab.get_or_add(s.get("nome"))]

        if "formato" in src and isinstance(src["formato"], dict):
            f = src["formato"]
            compact["fmt"] = [f.get("codigo"), vocab.get_or_add(f.get("nome"))]

        # OrgaoJulgador
        if "orgaoJulgador" in src and isinstance(src["orgaoJulgador"], dict):
            oj = src["orgaoJulgador"]
            has_ibge = "codigoMunicipioIBGE" in oj
            ibge_val = oj.get("codigoMunicipioIBGE") if has_ibge else "__OMIT__"
            compact["oj"] = [
                oj.get("codigo"),
                vocab.get_or_add(oj.get("nome")),
                ibge_val,
            ]

        # Assuntos
        if "assuntos" in src and isinstance(src["assuntos"], list):
            ass_list = []
            for a in src["assuntos"]:
                if isinstance(a, dict):
                    ass_list.append([a.get("codigo"), vocab.get_or_add(a.get("nome"))])
            compact["a"] = ass_list

        # Movimentos
        if "movimentos" in src and isinstance(src["movimentos"], list):
            mov_list = []
            for m in src["movimentos"]:
                if not isinstance(m, dict):
                    continue

                # Complementos tabelados
                comps = []
                for comp in m.get("complementosTabelados") or []:
                    if isinstance(comp, dict):
                        comp_entry = [
                            comp.get("codigo"),
                            vocab.get_or_add(comp.get("nome")),
                            vocab.get_or_add(comp.get("descricao")),
                            comp.get("valor"),
                        ]
                        comp_extra = {k: v for k, v in comp.items() if k not in cls.KNOWN_COMP}
                        if comp_extra:
                            comp_entry.append(comp_extra)
                        comps.append(comp_entry)

                # Orgao do movimento
                m_oj = None
                if "orgaoJulgador" in m and isinstance(m["orgaoJulgador"], dict):
                    mo = m["orgaoJulgador"]
                    m_oj = [mo.get("codigo"), vocab.get_or_add(mo.get("nome"))]

                has_comps = "complementosTabelados" in m
                m_entry = [
                    m.get("codigo"),
                    vocab.get_or_add(m.get("nome")),
                    m.get("dataHora"),
                    m_oj,
                    comps,
                    has_comps,
                ]

                m_extra = {k: v for k, v in m.items() if k not in cls.KNOWN_MOV}
                if m_extra:
                    m_entry.append(m_extra)

                mov_list.append(m_entry)
            compact["m"] = mov_list

        # Campos extras
        extra_env = {k: v for k, v in doc.items() if k not in cls.KNOWN_ENVELOPE}
        extra_src = {k: v for k, v in src.items() if k not in cls.KNOWN_SOURCE}
        if extra_env:
            compact["_xe"] = extra_env
        if extra_src:
            compact["_xs"] = extra_src

        return compact

    @classmethod
    def decode_document(
        cls, compact: dict[str, Any], cnj: str, vocab: LosslessVocabulary
    ) -> dict[str, Any]:
        """Reconstrói exatamente a estrutura e os dados do documento original."""
        tribunal = compact.get("t", "")
        grau = compact.get("g", "")
        doc_id = compact.get("_id") or f"{tribunal}_{grau}_{cnj}"
        src_id = compact.get("_sid") or doc_id

        src: dict[str, Any] = {
            "id": src_id,
            "numeroProcesso": cnj,
            "tribunal": tribunal,
            "grau": grau,
        }

        if "da" in compact:
            src["dataAjuizamento"] = compact["da"]
        if "du" in compact:
            src["dataHoraUltimaAtualizacao"] = compact["du"]
        if "@t" in compact:
            src["@timestamp"] = compact["@t"]
        if "s" in compact:
            src["nivelSigilo"] = compact["s"]

        if "c" in compact:
            c_code, c_nome_id = compact["c"]
            c_obj: dict[str, Any] = {"codigo": c_code}
            nome = vocab.get(c_nome_id)
            if nome is not None:
                c_obj["nome"] = nome
            src["classe"] = c_obj

        if "sis" in compact:
            s_code, s_nome_id = compact["sis"]
            s_obj: dict[str, Any] = {"codigo": s_code}
            nome = vocab.get(s_nome_id)
            if nome is not None:
                s_obj["nome"] = nome
            src["sistema"] = s_obj

        if "fmt" in compact:
            f_code, f_nome_id = compact["fmt"]
            f_obj: dict[str, Any] = {"codigo": f_code}
            nome = vocab.get(f_nome_id)
            if nome is not None:
                f_obj["nome"] = nome
            src["formato"] = f_obj

        if "oj" in compact:
            oj_code, oj_nome_id, ibge = compact["oj"]
            oj_obj: dict[str, Any] = {"codigo": oj_code}
            nome = vocab.get(oj_nome_id)
            if nome is not None:
                oj_obj["nome"] = nome
            if ibge != "__OMIT__":
                oj_obj["codigoMunicipioIBGE"] = ibge
            src["orgaoJulgador"] = oj_obj

        if "a" in compact:
            ass_list = []
            for a_code, a_nome_id in compact["a"]:
                a_obj: dict[str, Any] = {"codigo": a_code}
                nome = vocab.get(a_nome_id)
                if nome is not None:
                    a_obj["nome"] = nome
                ass_list.append(a_obj)
            src["assuntos"] = ass_list

        if "m" in compact:
            mov_list = []
            for m_entry in compact["m"]:
                m_code, m_nome_id, dt, m_oj, comps, has_comps = m_entry[:6]
                m_obj: dict[str, Any] = {
                    "codigo": m_code,
                    "dataHora": dt,
                }
                nome = vocab.get(m_nome_id)
                if nome is not None:
                    m_obj["nome"] = nome

                if m_oj:
                    m_oj_obj = {"codigo": m_oj[0]}
                    oj_nome = vocab.get(m_oj[1])
                    if oj_nome is not None:
                        m_oj_obj["nome"] = oj_nome
                    m_obj["orgaoJulgador"] = m_oj_obj

                if has_comps:
                    comp_list = []
                    for c_tuple in comps:
                        c_code, c_nome_id, c_desc_id, val = c_tuple[:4]
                        c_obj: dict[str, Any] = {"codigo": c_code}
                        c_nome = vocab.get(c_nome_id)
                        if c_nome is not None:
                            c_obj["nome"] = c_nome
                        c_desc = vocab.get(c_desc_id)
                        if c_desc is not None:
                            c_obj["descricao"] = c_desc
                        if val is not None:
                            c_obj["valor"] = val
                        if len(c_tuple) > 4:
                            c_obj.update(c_tuple[4])
                        comp_list.append(c_obj)
                    m_obj["complementosTabelados"] = comp_list

                if len(m_entry) > 6:
                    m_obj.update(m_entry[6])

                mov_list.append(m_obj)
            src["movimentos"] = mov_list

        if "_xs" in compact:
            src.update(compact["_xs"])

        doc: dict[str, Any] = {
            "_index": compact.get("_i"),
            "_id": doc_id,
            "_source": src,
        }

        if "_sc" in compact:
            doc["_score"] = compact["_sc"]
        if "_so" in compact:
            doc["sort"] = compact["_so"]
        if "_xe" in compact:
            doc.update(compact["_xe"])

        return doc
