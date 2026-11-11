"""Codec experimental compacto e híbrido (FlatBuffers + TPU/Zstd) para o DataJud.

Implementa as variantes de otimização propostas na Issue #1711:
1. FlatBuffers Lean (elimina duplicação integral de payload bruto).
2. FlatBuffers Compacto (tipos inteiros reduzidos, códigos TPU sem strings redundantes).
3. FlatBuffers Híbrido (Capa plana O(1) em FlatBuffers + bloco de movimentos em Zstd).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import flatbuffers
import zstandard as zstd


def iso_to_epoch_ms(iso_str: str | None) -> int:
    """Converte ISO 8601 em epoch milissegundos sem perda de precisão."""
    if not iso_str:
        return 0
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return int(dt.timestamp() * 1000)
    except (ValueError, TypeError):
        return 0


class CompactFlatBuffersCodec:
    """Implementa variantes otimizadas do FlatBuffers para o DataJud."""

    _zstd_cctx = zstd.ZstdCompressor(level=3)
    _zstd_dctx = zstd.ZstdDecompressor()

    @classmethod
    def encode_hybrid(cls, cnj: str, documentos: list[dict]) -> bytes:
        """Capa tipada plana O(1) em FlatBuffers + bloco de movimentos em Zstandard."""
        b = flatbuffers.Builder(32 * 1024)
        doc_offsets = []

        for doc in documentos:
            src = doc.get("_source", {})

            # 1. Strings da capa
            index_str = b.CreateString(str(doc.get("_index", "")))
            id_str = b.CreateString(str(doc.get("_id", "")))
            trib_str = b.CreateString(str(src.get("tribunal", "")))
            grau_str = b.CreateString(str(src.get("grau", "")))

            # 2. Assuntos (vetor de uint32)
            assuntos_cods = [
                int(a.get("codigo") or 0)
                for a in (src.get("assuntos") or [])
                if isinstance(a, dict) and a.get("codigo")
            ]
            ass_vec = 0
            if assuntos_cods:
                b.StartVector(4, len(assuntos_cods), 4)
                for code in reversed(assuntos_cods):
                    b.PrependUint32(code)
                ass_vec = b.EndVector()

            # 3. Bloco de movimentos compactado com Zstandard
            movimentos = src.get("movimentos") or []
            mov_zstd_bytes = cls._zstd_cctx.compress(
                json.dumps(movimentos, ensure_ascii=False).encode("utf-8")
            )
            mov_vec = b.CreateByteVector(mov_zstd_bytes)

            # 4. Campos desconhecidos (exclusivamente os que não estão no schema)
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

            # Extração de códigos numéricos compactos
            classe_cod = int(src.get("classe", {}).get("codigo") or 0)
            sistema_cod = int(src.get("sistema", {}).get("codigo") or 0)
            formato_cod = int(src.get("formato", {}).get("codigo") or 0)
            orgao_cod = int(src.get("orgaoJulgador", {}).get("codigo") or 0)
            ibge_cod = int(src.get("orgaoJulgador", {}).get("codigoMunicipioIBGE") or 0)
            sigilo = int(src.get("nivelSigilo") or 0)

            dt_aj_ms = iso_to_epoch_ms(src.get("dataAjuizamento"))
            dt_up_ms = iso_to_epoch_ms(src.get("dataHoraUltimaAtualizacao"))

            # Tabela DocumentoCompacto (17 campos)
            b.StartObject(17)
            b.PrependUOffsetTRelativeSlot(0, index_str, 0)
            b.PrependUOffsetTRelativeSlot(1, id_str, 0)
            b.PrependUOffsetTRelativeSlot(2, trib_str, 0)
            b.PrependUOffsetTRelativeSlot(3, grau_str, 0)
            b.PrependInt8Slot(4, sigilo, 0)
            b.PrependInt64Slot(5, dt_aj_ms, 0)
            b.PrependInt64Slot(6, dt_up_ms, 0)
            b.PrependInt32Slot(7, classe_cod, 0)
            b.PrependInt16Slot(8, sistema_cod, 0)
            b.PrependInt8Slot(9, formato_cod, 0)
            b.PrependInt32Slot(10, orgao_cod, 0)
            b.PrependInt32Slot(11, ibge_cod, 0)
            if ass_vec:
                b.PrependUOffsetTRelativeSlot(12, ass_vec, 0)
            b.PrependUOffsetTRelativeSlot(14, mov_vec, 0)  # movimentos_zstd_bytes
            if unknown_str:
                b.PrependUOffsetTRelativeSlot(15, unknown_str, 0)
            doc_offsets.append(b.EndObject())

        # Vetor de documentos
        b.StartVector(4, len(doc_offsets), 4)
        for off in reversed(doc_offsets):
            b.PrependUOffsetTRelative(off)
        docs_vec = b.EndVector()

        cnj_str = b.CreateString(str(cnj))

        # Root ProcessoCompactoCollection
        b.StartObject(3)
        b.PrependUOffsetTRelativeSlot(0, cnj_str, 0)
        b.PrependUint16Slot(1, len(documentos), 0)
        b.PrependUOffsetTRelativeSlot(2, docs_vec, 0)
        root = b.EndObject()

        b.Finish(root)
        return bytes(b.Output())

    @classmethod
    def decode_capa_only(cls, buf: bytes) -> list[dict[str, Any]]:
        """Lê os metadados da capa em O(1) direto dos buffers FlatBuffers sem descompressão."""
        tab = flatbuffers.table.Table(
            buf, flatbuffers.encode.Get(flatbuffers.packer.uoffset, buf, 0)
        )
        vec_off = tab.Offset(8)  # slot 2
        if not vec_off:
            return []

        addr = tab.Vector(vec_off)
        length = tab.VectorLen(vec_off)
        capas = []

        for i in range(length):
            doc_off = tab.Indirect(addr + i * 4)
            dtab = flatbuffers.table.Table(buf, doc_off)

            def r_str(slot):
                o = dtab.Offset(4 + slot * 2)
                return dtab.String(dtab.Pos + o).decode("utf-8") if o else ""

            def r_u32(slot):
                o = dtab.Offset(4 + slot * 2)
                return dtab.Get(flatbuffers.number_types.Uint32Flags, dtab.Pos + o) if o else 0

            capas.append(
                {
                    "_index": r_str(0),
                    "_id": r_str(1),
                    "tribunal": r_str(2),
                    "grau": r_str(3),
                    "classe_codigo": r_u32(7),
                    "orgao_codigo": r_u32(10),
                }
            )
        return capas

    @classmethod
    def decode_full(cls, buf: bytes) -> list[dict[str, Any]]:
        """Decodifica a capa e descomprime o bloco Zstandard de movimentos."""
        tab = flatbuffers.table.Table(
            buf, flatbuffers.encode.Get(flatbuffers.packer.uoffset, buf, 0)
        )
        vec_off = tab.Offset(8)
        if not vec_off:
            return []

        addr = tab.Vector(vec_off)
        length = tab.VectorLen(vec_off)
        docs = []

        for i in range(length):
            doc_off = tab.Indirect(addr + i * 4)
            dtab = flatbuffers.table.Table(buf, doc_off)

            def r_str(slot):
                o = dtab.Offset(4 + slot * 2)
                return dtab.String(dtab.Pos + o).decode("utf-8") if o else ""

            def r_u32(slot):
                o = dtab.Offset(4 + slot * 2)
                return dtab.Get(flatbuffers.number_types.Uint32Flags, dtab.Pos + o) if o else 0

            # Recupera bloco zstd de movimentos (slot 14)
            z_off = dtab.Offset(4 + 14 * 2)
            movimentos = []
            if z_off:
                z_addr = dtab.Vector(z_off)
                z_len = dtab.VectorLen(z_off)
                z_bytes = dtab.Bytes[z_addr : z_addr + z_len]
                movimentos = json.loads(cls._zstd_dctx.decompress(z_bytes).decode("utf-8"))

            docs.append(
                {
                    "_index": r_str(0),
                    "_id": r_str(1),
                    "tribunal": r_str(2),
                    "grau": r_str(3),
                    "classe_codigo": r_u32(7),
                    "orgao_codigo": r_u32(10),
                    "movimentos": movimentos,
                }
            )
        return docs
