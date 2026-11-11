"""Codec canônico FlatBuffers para o esquema processo.fbs (Issue #1710).

Implementa a especificação binária exata do FlatBuffers conforme declarada em
src/datajud/schema/processo.fbs, suportando:
1. Codificação e decodificação tipada completa de todos os campos declarados.
2. Preservação de campos desconhecidos em campos_desconhecidos_json.
3. Preservação opcional do payload bruto compactado (payload_original_bruto_gz).
4. Projeção seletiva (leitura da capa sem decodificar movimentos).
"""

from __future__ import annotations

import gzip
import json
from typing import Any

import flatbuffers
from flatbuffers import number_types


class FlatBuffersCodec:
    """Encoder e Decoder FlatBuffers em estrita conformidade com processo.fbs."""

    # ── HELPERS DE ESCRITA (ENCODING) ──────────────────────────────────

    @staticmethod
    def _pack_codigo_nome(b: flatbuffers.Builder, item: dict | None) -> int:
        if not item:
            return 0
        nome_str = b.CreateString(str(item.get("nome", ""))) if item.get("nome") else 0
        b.StartObject(2)
        b.PrependInt64Slot(0, int(item.get("codigo") or 0), 0)
        if nome_str:
            b.PrependUOffsetTRelativeSlot(1, nome_str, 0)
        return b.EndObject()

    @staticmethod
    def _pack_orgao_julgador(b: flatbuffers.Builder, item: dict | None) -> int:
        if not item:
            return 0
        nome_str = b.CreateString(str(item.get("nome", ""))) if item.get("nome") else 0
        b.StartObject(3)
        b.PrependInt64Slot(0, int(item.get("codigo") or 0), 0)
        if nome_str:
            b.PrependUOffsetTRelativeSlot(1, nome_str, 0)
        b.PrependInt64Slot(2, int(item.get("codigoMunicipioIBGE") or 0), 0)
        return b.EndObject()

    @staticmethod
    def _pack_complemento(b: flatbuffers.Builder, comp: dict) -> int:
        nome_str = b.CreateString(str(comp.get("nome", ""))) if comp.get("nome") else 0
        desc_str = b.CreateString(str(comp.get("descricao", ""))) if comp.get("descricao") else 0
        val_str = b.CreateString(str(comp.get("valor", ""))) if comp.get("valor") else 0

        b.StartObject(4)
        b.PrependInt64Slot(0, int(comp.get("codigo") or 0), 0)
        if nome_str:
            b.PrependUOffsetTRelativeSlot(1, nome_str, 0)
        if desc_str:
            b.PrependUOffsetTRelativeSlot(2, desc_str, 0)
        if val_str:
            b.PrependUOffsetTRelativeSlot(3, val_str, 0)
        return b.EndObject()

    @classmethod
    def _pack_movimento(cls, b: flatbuffers.Builder, mov: dict) -> int:
        nome_str = b.CreateString(str(mov.get("nome", ""))) if mov.get("nome") else 0
        dt_str = b.CreateString(str(mov.get("dataHora", ""))) if mov.get("dataHora") else 0
        orgao_off = cls._pack_codigo_nome(b, mov.get("orgaoJulgador"))

        comp_offsets = []
        for c in mov.get("complementosTabelados") or []:
            if isinstance(c, dict):
                comp_offsets.append(cls._pack_complemento(b, c))

        comp_vec = 0
        if comp_offsets:
            b.StartVector(4, len(comp_offsets), 4)
            for off in reversed(comp_offsets):
                b.PrependUOffsetTRelative(off)
            comp_vec = b.EndVector()

        b.StartObject(5)
        b.PrependInt64Slot(0, int(mov.get("codigo") or 0), 0)
        if nome_str:
            b.PrependUOffsetTRelativeSlot(1, nome_str, 0)
        if dt_str:
            b.PrependUOffsetTRelativeSlot(2, dt_str, 0)
        if orgao_off:
            b.PrependUOffsetTRelativeSlot(3, orgao_off, 0)
        if comp_vec:
            b.PrependUOffsetTRelativeSlot(4, comp_vec, 0)
        return b.EndObject()

    @classmethod
    def _pack_documento(cls, b: flatbuffers.Builder, doc: dict) -> int:
        src = doc.get("_source", {})

        # 1. Strings
        index_str = b.CreateString(str(doc.get("_index", "")))
        id_str = b.CreateString(str(doc.get("_id", "")))
        np_str = b.CreateString(str(src.get("numeroProcesso", "")))
        trib_str = b.CreateString(str(src.get("tribunal", "")))
        grau_str = b.CreateString(str(src.get("grau", "")))
        dt_aj_str = (
            b.CreateString(str(src.get("dataAjuizamento", ""))) if src.get("dataAjuizamento") else 0
        )
        dt_up_str = (
            b.CreateString(str(src.get("dataHoraUltimaAtualizacao", "")))
            if src.get("dataHoraUltimaAtualizacao")
            else 0
        )
        ts_str = b.CreateString(str(src.get("@timestamp", ""))) if src.get("@timestamp") else 0

        # 2. Tabelas aninhadas da capa
        classe_off = cls._pack_codigo_nome(b, src.get("classe"))
        sistema_off = cls._pack_codigo_nome(b, src.get("sistema"))
        formato_off = cls._pack_codigo_nome(b, src.get("formato"))
        orgao_off = cls._pack_orgao_julgador(b, src.get("orgaoJulgador"))

        # 3. Vetor de assuntos
        assunto_offsets = []
        for ass in src.get("assuntos") or []:
            if isinstance(ass, dict):
                assunto_offsets.append(cls._pack_codigo_nome(b, ass))
        assuntos_vec = 0
        if assunto_offsets:
            b.StartVector(4, len(assunto_offsets), 4)
            for off in reversed(assunto_offsets):
                b.PrependUOffsetTRelative(off)
            assuntos_vec = b.EndVector()

        # 4. Vetor de movimentos
        mov_offsets = []
        for m in src.get("movimentos") or []:
            if isinstance(m, dict):
                mov_offsets.append(cls._pack_movimento(b, m))
        movs_vec = 0
        if mov_offsets:
            b.StartVector(4, len(mov_offsets), 4)
            for off in reversed(mov_offsets):
                b.PrependUOffsetTRelative(off)
            movs_vec = b.EndVector()

        # 5. Campos desconhecidos e payload bruto (zero-loss guarantee)
        known_keys = {
            "id",
            "tribunal",
            "grau",
            "numeroProcesso",
            "dataAjuizamento",
            "nivelSigilo",
            "orgaoJulgador",
            "classe",
            "sistema",
            "formato",
            "dataHoraUltimaAtualizacao",
            "@timestamp",
            "movimentos",
            "assuntos",
        }
        unknown = {k: v for k, v in src.items() if k not in known_keys}
        unknown_str = b.CreateString(json.dumps(unknown, ensure_ascii=False)) if unknown else 0

        raw_bytes = gzip.compress(json.dumps(doc, ensure_ascii=False).encode("utf-8"))
        raw_vec = b.CreateByteVector(raw_bytes)

        sort_epoch = 0
        if doc.get("sort") and isinstance(doc["sort"], list) and doc["sort"]:
            try:
                sort_epoch = int(doc["sort"][0])
            except (ValueError, TypeError):
                sort_epoch = 0

        # Monta a tabela DocumentoDataJud (18 slots exatamente correspondentes ao .fbs)
        b.StartObject(18)
        b.PrependUOffsetTRelativeSlot(0, index_str, 0)
        b.PrependUOffsetTRelativeSlot(1, id_str, 0)
        b.PrependInt64Slot(2, sort_epoch, 0)
        b.PrependUOffsetTRelativeSlot(3, np_str, 0)
        b.PrependUOffsetTRelativeSlot(4, trib_str, 0)
        b.PrependUOffsetTRelativeSlot(5, grau_str, 0)
        b.PrependInt32Slot(6, int(src.get("nivelSigilo") or 0), 0)
        if dt_aj_str:
            b.PrependUOffsetTRelativeSlot(7, dt_aj_str, 0)
        if dt_up_str:
            b.PrependUOffsetTRelativeSlot(8, dt_up_str, 0)
        if ts_str:
            b.PrependUOffsetTRelativeSlot(9, ts_str, 0)
        if classe_off:
            b.PrependUOffsetTRelativeSlot(10, classe_off, 0)
        if sistema_off:
            b.PrependUOffsetTRelativeSlot(11, sistema_off, 0)
        if formato_off:
            b.PrependUOffsetTRelativeSlot(12, formato_off, 0)
        if orgao_off:
            b.PrependUOffsetTRelativeSlot(13, orgao_off, 0)
        if assuntos_vec:
            b.PrependUOffsetTRelativeSlot(14, assuntos_vec, 0)
        if movs_vec:
            b.PrependUOffsetTRelativeSlot(15, movs_vec, 0)
        if unknown_str:
            b.PrependUOffsetTRelativeSlot(16, unknown_str, 0)
        b.PrependUOffsetTRelativeSlot(17, raw_vec, 0)
        return b.EndObject()

    @classmethod
    def encode_collection(cls, cnj: str, documentos: list[dict]) -> bytes:
        """Serializa uma coleção de documentos de um CNJ no formato ProcessoCNJCollection."""
        b = flatbuffers.Builder(64 * 1024)

        doc_offsets = [cls._pack_documento(b, d) for d in documentos]

        b.StartVector(4, len(doc_offsets), 4)
        for off in reversed(doc_offsets):
            b.PrependUOffsetTRelative(off)
        docs_vec = b.EndVector()

        cnj_str = b.CreateString(str(cnj))

        # Tabela ProcessoCNJCollection (3 slots)
        b.StartObject(3)
        b.PrependUOffsetTRelativeSlot(0, cnj_str, 0)
        b.PrependInt32Slot(1, len(documentos), 0)
        b.PrependUOffsetTRelativeSlot(2, docs_vec, 0)
        root = b.EndObject()

        b.Finish(root)
        return bytes(b.Output())

    # ── HELPERS DE LEITURA (DECODING) ──────────────────────────────────

    @staticmethod
    def _read_str(tab: flatbuffers.table.Table, slot_idx: int) -> str:
        v_off = tab.Offset(4 + slot_idx * 2)
        if not v_off:
            return ""
        return tab.String(tab.Pos + v_off).decode("utf-8", errors="replace")

    @staticmethod
    def _read_int64(tab: flatbuffers.table.Table, slot_idx: int) -> int:
        v_off = tab.Offset(4 + slot_idx * 2)
        if not v_off:
            return 0
        return tab.Get(number_types.Int64Flags, tab.Pos + v_off)

    @staticmethod
    def _read_int32(tab: flatbuffers.table.Table, slot_idx: int) -> int:
        v_off = tab.Offset(4 + slot_idx * 2)
        if not v_off:
            return 0
        return tab.Get(number_types.Int32Flags, tab.Pos + v_off)

    @classmethod
    def _read_codigo_nome(
        cls, tab: flatbuffers.table.Table, slot_idx: int
    ) -> dict[str, Any] | None:
        v_off = tab.Offset(4 + slot_idx * 2)
        if not v_off:
            return None
        sub_tab = flatbuffers.table.Table(tab.Bytes, tab.Indirect(tab.Pos + v_off))
        code = cls._read_int64(sub_tab, 0)
        nome = cls._read_str(sub_tab, 1)
        res = {}
        if code:
            res["codigo"] = code
        if nome:
            res["nome"] = nome
        return res if res else None

    @classmethod
    def _read_orgao_julgador(
        cls, tab: flatbuffers.table.Table, slot_idx: int
    ) -> dict[str, Any] | None:
        v_off = tab.Offset(4 + slot_idx * 2)
        if not v_off:
            return None
        sub_tab = flatbuffers.table.Table(tab.Bytes, tab.Indirect(tab.Pos + v_off))
        res = {}
        code = cls._read_int64(sub_tab, 0)
        nome = cls._read_str(sub_tab, 1)
        ibge = cls._read_int64(sub_tab, 2)
        if code:
            res["codigo"] = code
        if nome:
            res["nome"] = nome
        if ibge:
            res["codigoMunicipioIBGE"] = ibge
        return res if res else None

    @classmethod
    def _read_complemento(cls, tab: flatbuffers.table.Table) -> dict[str, Any]:
        res = {}
        code = cls._read_int64(tab, 0)
        nome = cls._read_str(tab, 1)
        desc = cls._read_str(tab, 2)
        val = cls._read_str(tab, 3)
        if code:
            res["codigo"] = code
        if nome:
            res["nome"] = nome
        if desc:
            res["descricao"] = desc
        if val:
            res["valor"] = val
        return res

    @classmethod
    def _read_movimento(cls, tab: flatbuffers.table.Table) -> dict[str, Any]:
        res = {
            "codigo": cls._read_int64(tab, 0),
            "nome": cls._read_str(tab, 1),
            "dataHora": cls._read_str(tab, 2),
        }
        orgao = cls._read_codigo_nome(tab, 3)
        if orgao:
            res["orgaoJulgador"] = orgao

        v_off = tab.Offset(4 + 4 * 2)  # slot 4
        if v_off:
            vec_addr = tab.Vector(v_off)
            vec_len = tab.VectorLen(v_off)
            comps = []
            for i in range(vec_len):
                comp_tab = flatbuffers.table.Table(tab.Bytes, tab.Indirect(vec_addr + i * 4))
                comps.append(cls._read_complemento(comp_tab))
            if comps:
                res["complementosTabelados"] = comps
        return res

    @classmethod
    def decode_document_typed(cls, doc_tab: flatbuffers.table.Table) -> dict[str, Any]:
        """Decodifica campo a campo a árvore tipada exata do DocumentoDataJud."""
        index_origem = cls._read_str(doc_tab, 0)
        id_origem = cls._read_str(doc_tab, 1)
        sort_epoch = cls._read_int64(doc_tab, 2)

        src = {
            "id": id_origem,
            "numeroProcesso": cls._read_str(doc_tab, 3),
            "tribunal": cls._read_str(doc_tab, 4),
            "grau": cls._read_str(doc_tab, 5),
            "nivelSigilo": cls._read_int32(doc_tab, 6),
            "dataAjuizamento": cls._read_str(doc_tab, 7),
            "dataHoraUltimaAtualizacao": cls._read_str(doc_tab, 8),
            "@timestamp": cls._read_str(doc_tab, 9),
        }

        classe = cls._read_codigo_nome(doc_tab, 10)
        if classe:
            src["classe"] = classe
        sistema = cls._read_codigo_nome(doc_tab, 11)
        if sistema:
            src["sistema"] = sistema
        formato = cls._read_codigo_nome(doc_tab, 12)
        if formato:
            src["formato"] = formato
        orgao = cls._read_orgao_julgador(doc_tab, 13)
        if orgao:
            src["orgaoJulgador"] = orgao

        # Assuntos
        ass_off = doc_tab.Offset(4 + 14 * 2)
        if ass_off:
            vec_addr = doc_tab.Vector(ass_off)
            vec_len = doc_tab.VectorLen(ass_off)
            assuntos = []
            for i in range(vec_len):
                sub_tab = flatbuffers.table.Table(doc_tab.Bytes, doc_tab.Indirect(vec_addr + i * 4))
                code = cls._read_int64(sub_tab, 0)
                nome = cls._read_str(sub_tab, 1)
                assuntos.append({"codigo": code, "nome": nome})
            src["assuntos"] = assuntos

        # Movimentos
        mov_off = doc_tab.Offset(4 + 15 * 2)
        if mov_off:
            vec_addr = doc_tab.Vector(mov_off)
            vec_len = doc_tab.VectorLen(mov_off)
            movimentos = []
            for i in range(vec_len):
                m_tab = flatbuffers.table.Table(doc_tab.Bytes, doc_tab.Indirect(vec_addr + i * 4))
                movimentos.append(cls._read_movimento(m_tab))
            src["movimentos"] = movimentos

        # Campos desconhecidos
        unknown_str = cls._read_str(doc_tab, 16)
        if unknown_str:
            try:
                src.update(json.loads(unknown_str))
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

        doc = {
            "_index": index_origem,
            "_id": id_origem,
            "_source": src,
        }
        if sort_epoch:
            doc["sort"] = [sort_epoch]
        return doc

    @classmethod
    def decode_capa_only(cls, doc_tab: flatbuffers.table.Table) -> dict[str, Any]:
        """Projeção seletiva: lê apenas a capa da tabela sem decodificar movimentos."""
        return {
            "_index": cls._read_str(doc_tab, 0),
            "_id": cls._read_str(doc_tab, 1),
            "numeroProcesso": cls._read_str(doc_tab, 3),
            "tribunal": cls._read_str(doc_tab, 4),
            "grau": cls._read_str(doc_tab, 5),
            "dataAjuizamento": cls._read_str(doc_tab, 7),
            "dataHoraUltimaAtualizacao": cls._read_str(doc_tab, 8),
            "classe": cls._read_codigo_nome(doc_tab, 10),
            "orgaoJulgador": cls._read_orgao_julgador(doc_tab, 13),
        }

    @classmethod
    def decode_raw_payload(cls, doc_tab: flatbuffers.table.Table) -> dict[str, Any]:
        """Recupera o payload bruto compactado armazenado no slot 17."""
        v_off = doc_tab.Offset(4 + 17 * 2)
        if not v_off:
            return {}
        addr = doc_tab.Vector(v_off)
        length = doc_tab.VectorLen(v_off)
        gz_bytes = doc_tab.Bytes[addr : addr + length]
        return json.loads(gzip.decompress(gz_bytes).decode("utf-8"))

    @classmethod
    def decode_collection(cls, buf: bytes, mode: str = "typed") -> list[dict[str, Any]]:
        """Decodifica TODOS os documentos da coleção.

        mode: 'typed' (decodificação completa tipada), 'capa' (projeção rápida) ou 'raw' (payload original).
        """
        root_tab = flatbuffers.table.Table(
            buf, flatbuffers.encode.Get(flatbuffers.packer.uoffset, buf, 0)
        )
        docs_vec_off = root_tab.Offset(8)  # slot 2
        if not docs_vec_off:
            return []

        vec_addr = root_tab.Vector(docs_vec_off)
        vec_len = root_tab.VectorLen(docs_vec_off)
        documentos = []

        for i in range(vec_len):
            doc_offset = root_tab.Indirect(vec_addr + i * 4)
            doc_tab = flatbuffers.table.Table(buf, doc_offset)

            if mode == "capa":
                documentos.append(cls.decode_capa_only(doc_tab))
            elif mode == "raw":
                documentos.append(cls.decode_raw_payload(doc_tab))
            else:
                documentos.append(cls.decode_document_typed(doc_tab))

        return documentos
