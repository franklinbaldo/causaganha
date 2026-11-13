"""Lossless Protobuf v2 (PB v2) codec for DJEN communication batches.

Encodes DJEN JSON records into compact ``{hash}.pb`` (or ``{hash}.pb.zst``)
entries inside a ZIP archive, using the DJEN ``hash`` as the member name
instead of generating a UUIDv5, and applying:
- Batch dictionary (``_dict.pb``) for repeated categorical strings, link
  prefixes, unique lawyers (``advogados``), and a 32k text token vocabulary.
- Split CNJ process numbers (varints for sequential, check digit, year,
  justice+tribunal, origin) with string fallback for non-20-digit values.
- Epoch-day / Unix-second integers for dates and timestamps, omitting
  redundant ``datadisponibilizacao`` and ``updated_at`` when derivable.
- Omission of redundant foreign keys (``comunicacao_id``, ``advogado_id``)
  when equal to their parent record IDs.
"""

from __future__ import annotations

import io
import json
import re
import zipfile
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

CompressionMode = Literal["stored", "deflated", "zstd", "zstd_dict"]

EPOCH_DATE = date(1970, 1, 1)
EPOCH_DT = datetime(1970, 1, 1, tzinfo=UTC)
TOKEN_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]+|\s+|[^\sA-Za-zÀ-ÖØ-öø-ÿ0-9]+")
DEFAULT_VOCAB_SIZE = 32_000
MIN_DICT_SAMPLES = 50
MIN_DICT_TOTAL_BYTES = 16_384


def encode_varint(val: int) -> bytes:
    """Encode a non-negative integer as Protobuf base-128 varint."""
    if val < 0:
        msg = f"Varint value must be non-negative, got {val}"
        raise ValueError(msg)
    out = bytearray()
    while val >= 0x80:
        out.append((val & 0x7F) | 0x80)
        val >>= 7
    out.append(val)
    return bytes(out)


def decode_varint(buf: bytes, pos: int) -> tuple[int, int]:
    """Decode a Protobuf base-128 varint starting at ``pos``."""
    val = 0
    shift = 0
    while True:
        b = buf[pos]
        pos += 1
        val |= (b & 0x7F) << shift
        if not (b & 0x80):
            return val, pos
        shift += 7


def _encode_tag(field_num: int, wire_type: int) -> bytes:
    return encode_varint((field_num << 3) | wire_type)


def _encode_str(field_num: int, s: str | None) -> bytes:
    if s is None:
        return b""
    b = s.encode("utf-8")
    return _encode_tag(field_num, 2) + encode_varint(len(b)) + b


def _encode_int(field_num: int, v: int | None) -> bytes:
    if v is None:
        return b""
    return _encode_tag(field_num, 0) + encode_varint(int(v))


def _encode_bytes_field(field_num: int, b: bytes) -> bytes:
    if not b:
        return b""
    return _encode_tag(field_num, 2) + encode_varint(len(b)) + b


def _iter_pb_fields(buf: bytes):
    pos = 0
    n = len(buf)
    while pos < n:
        tag, pos = decode_varint(buf, pos)
        field_num = tag >> 3
        wire_type = tag & 0x7
        if wire_type == 0:
            val, pos = decode_varint(buf, pos)
            yield field_num, 0, val
        elif wire_type == 2:
            length, pos = decode_varint(buf, pos)
            val = buf[pos : pos + length]
            pos += length
            yield field_num, 2, val
        else:
            msg = f"Unsupported protobuf wire_type {wire_type}"
            raise ValueError(msg)


def tokenize_text(text: str, vocab: dict[str, int]) -> bytes:
    """Losslessly encode text using a token-ID vocabulary with UTF-8 fallback."""
    if not text:
        return b""
    buf = bytearray()
    for tok in TOKEN_RE.findall(text):
        tid = vocab.get(tok)
        if tid is not None:
            buf.extend(encode_varint(tid))
        else:
            rb = tok.encode("utf-8")
            buf.append(0)
            buf.extend(encode_varint(len(rb)))
            buf.extend(rb)
    return bytes(buf)


def detokenize_text(buf: bytes, inv_vocab: list[str]) -> str:
    """Reconstruct exact text from tokenized bytes and inverse vocabulary."""
    if not buf:
        return ""
    out: list[str] = []
    pos = 0
    n = len(buf)
    while pos < n:
        tid, pos = decode_varint(buf, pos)
        if tid == 0:
            length, pos = decode_varint(buf, pos)
            out.append(buf[pos : pos + length].decode("utf-8"))
            pos += length
        else:
            out.append(inv_vocab[tid - 1])
    return "".join(out)


def _parse_iso_days(s: str | None) -> int | None:
    if not s or len(s) != 10 or s[4] != "-" or s[7] != "-":
        return None
    try:
        return (date(int(s[:4]), int(s[5:7]), int(s[8:10])) - EPOCH_DATE).days
    except ValueError:
        return None


def _parse_br_days(s: str | None) -> int | None:
    if not s or len(s) != 10 or s[2] != "/" or s[5] != "/":
        return None
    try:
        return (date(int(s[6:10]), int(s[3:5]), int(s[:2])) - EPOCH_DATE).days
    except ValueError:
        return None


def _fmt_iso_days(days: int) -> str:
    d = date.fromordinal(EPOCH_DATE.toordinal() + days)
    return f"{d.year:04d}-{d.month:02d}-{d.day:02d}"


def _fmt_br_days(days: int) -> str:
    d = date.fromordinal(EPOCH_DATE.toordinal() + days)
    return f"{d.day:02d}/{d.month:02d}/{d.year:04d}"


def _parse_ts(s: str | None) -> int | None:
    if not s or len(s) != 19:
        return None
    try:
        dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
        return int((dt - EPOCH_DT).total_seconds())
    except ValueError:
        return None


def _fmt_ts(sec: int) -> str:
    return datetime.fromtimestamp(sec, tz=UTC).strftime("%Y-%m-%d %H:%M:%S")


def _split_link(url: str | None) -> tuple[str, str]:
    if not url:
        return "", ""
    idx = url.find("=")
    if idx != -1:
        return url[: idx + 1], url[idx + 1 :]
    idx = url.rfind("/")
    if idx != -1:
        return url[: idx + 1], url[idx + 1 :]
    return "", url


class BatchDict:
    """Shared dictionary for a batch of PB v2 records."""

    def __init__(self) -> None:
        self.strings: list[str] = []
        self.str_to_id: dict[str, int] = {}
        self.link_prefixes: list[str] = []
        self.prefix_to_id: dict[str, int] = {}
        self.advogados: list[tuple[int, str, str, str]] = []
        self.adv_to_id: dict[tuple[int, str, str, str], int] = {}
        self.vocab: list[str] = []

    def intern_str(self, s: str | None) -> int:
        if s is None:
            return 0
        idx = self.str_to_id.get(s)
        if idx is None:
            idx = len(self.strings) + 1
            self.strings.append(s)
            self.str_to_id[s] = idx
        return idx

    def intern_prefix(self, p: str) -> int:
        if not p:
            return 0
        idx = self.prefix_to_id.get(p)
        if idx is None:
            idx = len(self.link_prefixes) + 1
            self.link_prefixes.append(p)
            self.prefix_to_id[p] = idx
        return idx

    def intern_adv(self, adv: dict) -> int:
        key = (
            int(adv["id"]),
            adv.get("nome") or "",
            adv.get("numero_oab") or "",
            adv.get("uf_oab") or "",
        )
        idx = self.adv_to_id.get(key)
        if idx is None:
            idx = len(self.advogados) + 1
            self.advogados.append(key)
            self.adv_to_id[key] = idx
        return idx

    def to_pb(self) -> bytes:
        parts: list[bytes] = []
        for s in self.strings:
            parts.append(_encode_str(1, s))
        for p in self.link_prefixes:
            parts.append(_encode_str(2, p))
        for adv_id, nome, oab, uf in self.advogados:
            inner = (
                _encode_int(1, adv_id)
                + _encode_str(2, nome)
                + _encode_str(3, oab)
                + _encode_str(4, uf)
            )
            parts.append(_encode_bytes_field(3, inner))
        for tok in self.vocab:
            parts.append(_encode_str(4, tok))
        return b"".join(parts)

    @classmethod
    def from_pb(cls, data: bytes) -> BatchDict:
        bd = cls()
        for fnum, _, val in _iter_pb_fields(data):
            if fnum == 1:
                s = val.decode("utf-8")
                bd.strings.append(s)
                bd.str_to_id[s] = len(bd.strings)
            elif fnum == 2:
                p = val.decode("utf-8")
                bd.link_prefixes.append(p)
                bd.prefix_to_id[p] = len(bd.link_prefixes)
            elif fnum == 3:
                adv_id = 0
                nome = oab = uf = ""
                for af, _, av in _iter_pb_fields(val):
                    if af == 1:
                        adv_id = av
                    elif af == 2:
                        nome = av.decode("utf-8")
                    elif af == 3:
                        oab = av.decode("utf-8")
                    elif af == 4:
                        uf = av.decode("utf-8")
                key = (adv_id, nome, oab, uf)
                bd.advogados.append(key)
                bd.adv_to_id[key] = len(bd.advogados)
            elif fnum == 4:
                bd.vocab.append(val.decode("utf-8"))
        return bd


def encode_item_pb(item: dict, bd: BatchDict, vocab_map: dict[str, int]) -> bytes:
    """Encode a single DJEN JSON communication dict into PB v2 bytes."""
    parts: list[bytes] = []
    cid = item.get("id")
    parts.append(_encode_int(1, cid))

    disp_iso = item.get("data_disponibilizacao")
    disp_br = item.get("datadisponibilizacao")
    days_disp = _parse_iso_days(disp_iso)
    if days_disp is not None:
        parts.append(_encode_int(2, days_disp))
        if disp_br != _fmt_br_days(days_disp):
            parts.append(_encode_str(20, disp_br))
    else:
        parts.append(_encode_str(19, disp_iso))
        parts.append(_encode_str(20, disp_br))

    envio = item.get("dataenvio")
    days_envio = _parse_br_days(envio)
    if days_envio is not None:
        parts.append(_encode_int(3, days_envio))
    elif envio is not None:
        parts.append(_encode_str(21, envio))

    parts.append(_encode_int(4, bd.intern_str(item.get("siglaTribunal"))))
    parts.append(_encode_int(5, bd.intern_str(item.get("tipoComunicacao"))))
    parts.append(_encode_int(6, bd.intern_str(item.get("nomeOrgao"))))
    parts.append(_encode_int(7, bd.intern_str(item.get("tipoDocumento"))))
    parts.append(_encode_int(8, bd.intern_str(item.get("nomeClasse"))))
    parts.append(_encode_int(9, bd.intern_str(item.get("codigoClasse"))))
    parts.append(_encode_int(10, bd.intern_str(item.get("meio"))))
    parts.append(_encode_int(11, bd.intern_str(item.get("status"))))

    txt = item.get("texto")
    if txt is not None:
        parts.append(_encode_bytes_field(12, tokenize_text(txt, vocab_map)))

    cnj = item.get("numero_processo")
    if cnj and len(cnj) == 20 and cnj.isdigit():
        cnj_pb = (
            _encode_int(1, int(cnj[0:7]))
            + _encode_int(2, int(cnj[7:9]))
            + _encode_int(3, int(cnj[9:13]))
            + _encode_int(4, int(cnj[13:16]))
            + _encode_int(5, int(cnj[16:20]))
        )
        parts.append(_encode_bytes_field(13, cnj_pb))
    elif cnj is not None:
        parts.append(_encode_str(22, cnj))

    link = item.get("link")
    if link is not None:
        pref, suff = _split_link(link)
        parts.append(_encode_int(14, bd.intern_prefix(pref)))
        parts.append(_encode_str(15, suff))

    parts.append(_encode_int(16, item.get("numeroComunicacao")))
    ativo = item.get("ativo")
    if ativo is not None:
        parts.append(_encode_int(17, 1 if ativo else 0))

    if item.get("motivo_cancelamento") is not None:
        parts.append(_encode_str(23, item.get("motivo_cancelamento")))
    if item.get("data_cancelamento") is not None:
        parts.append(_encode_str(24, item.get("data_cancelamento")))

    for d in item.get("destinatarios") or []:
        inner: list[bytes] = []
        if d.get("nome") is not None:
            inner.append(_encode_str(1, d["nome"]))
        if d.get("polo") is not None:
            inner.append(_encode_str(2, d["polo"]))
        if d.get("comunicacao_id") != cid:
            inner.append(_encode_int(3, d.get("comunicacao_id")))
        parts.append(_encode_bytes_field(25, b"".join(inner)))

    for da in item.get("destinatarioadvogados") or []:
        inner = [_encode_int(1, da.get("id"))]
        if da.get("comunicacao_id") != cid:
            inner.append(_encode_int(2, da.get("comunicacao_id")))
        adv = da.get("advogado")
        if adv is not None:
            adv_idx = bd.intern_adv(adv)
            inner.append(_encode_int(3, adv_idx))
            if da.get("advogado_id") != adv.get("id"):
                inner.append(_encode_int(4, da.get("advogado_id")))
        elif da.get("advogado_id") is not None:
            inner.append(_encode_int(4, da.get("advogado_id")))

        ca = da.get("created_at")
        ua = da.get("updated_at")
        ca_ts = _parse_ts(ca)
        if ca_ts is not None:
            inner.append(_encode_int(5, ca_ts))
            if ua != ca:
                ua_ts = _parse_ts(ua)
                if ua_ts is not None:
                    inner.append(_encode_int(6, ua_ts))
                elif ua is not None:
                    inner.append(_encode_str(8, ua))
        else:
            if ca is not None:
                inner.append(_encode_str(7, ca))
            if ua is not None:
                inner.append(_encode_str(8, ua))
        parts.append(_encode_bytes_field(26, b"".join(inner)))

    return b"".join(parts)


def decode_item_pb(data: bytes, item_hash: str, bd: BatchDict) -> dict:
    """Decode PB v2 bytes + DJEN ``hash`` back to the exact DJEN JSON dict."""
    out: dict = {
        "id": None,
        "data_disponibilizacao": None,
        "siglaTribunal": None,
        "tipoComunicacao": None,
        "nomeOrgao": None,
        "texto": "",
        "numero_processo": None,
        "meio": None,
        "link": None,
        "tipoDocumento": None,
        "nomeClasse": None,
        "codigoClasse": None,
        "numeroComunicacao": None,
        "ativo": None,
        "hash": item_hash,
        "status": None,
        "motivo_cancelamento": None,
        "data_cancelamento": None,
        "datadisponibilizacao": None,
        "dataenvio": None,
        "destinatarios": [],
        "destinatarioadvogados": [],
    }

    link_pref_id = 0
    link_suff: str | None = None

    for fnum, _, val in _iter_pb_fields(data):
        if fnum == 1:
            out["id"] = val
        elif fnum == 2:
            out["data_disponibilizacao"] = _fmt_iso_days(val)
            out["datadisponibilizacao"] = _fmt_br_days(val)
        elif fnum == 3:
            out["dataenvio"] = _fmt_br_days(val)
        elif fnum == 4:
            out["siglaTribunal"] = bd.strings[val - 1] if val else None
        elif fnum == 5:
            out["tipoComunicacao"] = bd.strings[val - 1] if val else None
        elif fnum == 6:
            out["nomeOrgao"] = bd.strings[val - 1] if val else None
        elif fnum == 7:
            out["tipoDocumento"] = bd.strings[val - 1] if val else None
        elif fnum == 8:
            out["nomeClasse"] = bd.strings[val - 1] if val else None
        elif fnum == 9:
            out["codigoClasse"] = bd.strings[val - 1] if val else None
        elif fnum == 10:
            out["meio"] = bd.strings[val - 1] if val else None
        elif fnum == 11:
            out["status"] = bd.strings[val - 1] if val else None
        elif fnum == 12:
            out["texto"] = detokenize_text(val, bd.vocab)
        elif fnum == 13:
            seq = dv = ano = jt = orig = 0
            for cf, _, cv in _iter_pb_fields(val):
                if cf == 1:
                    seq = cv
                elif cf == 2:
                    dv = cv
                elif cf == 3:
                    ano = cv
                elif cf == 4:
                    jt = cv
                elif cf == 5:
                    orig = cv
            out["numero_processo"] = f"{seq:07d}{dv:02d}{ano:04d}{jt:03d}{orig:04d}"
        elif fnum == 14:
            link_pref_id = val
        elif fnum == 15:
            link_suff = val.decode("utf-8")
        elif fnum == 16:
            out["numeroComunicacao"] = val
        elif fnum == 17:
            out["ativo"] = bool(val)
        elif fnum == 19:
            out["data_disponibilizacao"] = val.decode("utf-8")
        elif fnum == 20:
            out["datadisponibilizacao"] = val.decode("utf-8")
        elif fnum == 21:
            out["dataenvio"] = val.decode("utf-8")
        elif fnum == 22:
            out["numero_processo"] = val.decode("utf-8")
        elif fnum == 23:
            out["motivo_cancelamento"] = val.decode("utf-8")
        elif fnum == 24:
            out["data_cancelamento"] = val.decode("utf-8")
        elif fnum == 25:
            d = {"nome": None, "polo": None, "comunicacao_id": out["id"]}
            for df, _, dv in _iter_pb_fields(val):
                if df == 1:
                    d["nome"] = dv.decode("utf-8")
                elif df == 2:
                    d["polo"] = dv.decode("utf-8")
                elif df == 3:
                    d["comunicacao_id"] = dv
            out["destinatarios"].append(d)
        elif fnum == 26:
            da: dict = {
                "id": None,
                "comunicacao_id": out["id"],
                "advogado_id": None,
                "created_at": None,
                "updated_at": None,
                "advogado": None,
            }
            for af, _, av in _iter_pb_fields(val):
                if af == 1:
                    da["id"] = av
                elif af == 2:
                    da["comunicacao_id"] = av
                elif af == 3:
                    adv_id, nome, oab, uf = bd.advogados[av - 1]
                    da["advogado"] = {
                        "id": adv_id,
                        "nome": nome,
                        "numero_oab": oab,
                        "uf_oab": uf,
                    }
                    if da["advogado_id"] is None:
                        da["advogado_id"] = adv_id
                elif af == 4:
                    da["advogado_id"] = av
                elif af == 5:
                    ts = _fmt_ts(av)
                    da["created_at"] = ts
                    if da["updated_at"] is None:
                        da["updated_at"] = ts
                elif af == 6:
                    da["updated_at"] = _fmt_ts(av)
                elif af == 7:
                    da["created_at"] = av.decode("utf-8")
                elif af == 8:
                    da["updated_at"] = av.decode("utf-8")
            out["destinatarioadvogados"].append(da)

    if link_suff is not None or link_pref_id:
        pref = bd.link_prefixes[link_pref_id - 1] if link_pref_id else ""
        out["link"] = pref + (link_suff or "")

    return out


def encode_records_to_pb_zip_bytes(
    records: list[dict],
    *,
    mode: CompressionMode = "zstd_dict",
    vocab_size: int = DEFAULT_VOCAB_SIZE,
    zstd_level: int = 9,
) -> bytes:
    """Encode a list of DJEN communication dicts into a PB v2 ZIP archive."""
    freq: Counter[str] = Counter()
    for it in records:
        txt = it.get("texto") or ""
        if txt:
            freq.update(TOKEN_RE.findall(txt))

    bd = BatchDict()
    bd.vocab = [tok for tok, _ in freq.most_common(vocab_size)]
    vocab_map = {tok: i + 1 for i, tok in enumerate(bd.vocab)}

    pb_map: dict[str, bytes] = {}
    for it in records:
        h = it.get("hash")
        if not h:
            msg = f"Record id={it.get('id')} is missing required DJEN 'hash'"
            raise ValueError(msg)
        pb_map[h] = encode_item_pb(it, bd, vocab_map)

    dict_pb = bd.to_pb()
    buf = io.BytesIO()

    if mode in ("stored", "deflated"):
        zip_comp = zipfile.ZIP_STORED if mode == "stored" else zipfile.ZIP_DEFLATED
        kwargs = {"compresslevel": 9} if mode == "deflated" else {}
        with zipfile.ZipFile(buf, "w", compression=zip_comp, **kwargs) as z:
            z.writestr("_dict.pb", dict_pb)
            for h, b in pb_map.items():
                z.writestr(f"{h}.pb", b)
        return buf.getvalue()

    import zstandard as zstd

    cctx = zstd.ZstdCompressor(level=zstd_level)
    samples = list(pb_map.values())[:2000]
    can_train_dict = (
        mode == "zstd_dict"
        and len(samples) >= MIN_DICT_SAMPLES
        and sum(len(s) for s in samples) >= MIN_DICT_TOTAL_BYTES
    )

    if can_train_dict:
        zdict = zstd.train_dictionary(32_768, samples)
        cctx_entry = zstd.ZstdCompressor(level=zstd_level, dict_data=zdict)
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as z:
            z.writestr("_dict.pb.zst", cctx.compress(dict_pb))
            z.writestr("_zdict.zstd", zdict.as_bytes())
            for h, b in pb_map.items():
                z.writestr(f"{h}.pb.zst", cctx_entry.compress(b))
    else:
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as z:
            z.writestr("_dict.pb.zst", cctx.compress(dict_pb))
            for h, b in pb_map.items():
                z.writestr(f"{h}.pb.zst", cctx.compress(b))

    return buf.getvalue()


def decode_pb_zip_bytes(zip_bytes: bytes) -> list[dict]:
    """Decode a PB v2 ZIP archive back into the exact list of DJEN dicts."""
    z_in = zipfile.ZipFile(io.BytesIO(zip_bytes), "r")
    names = set(z_in.namelist())

    if "_dict.pb" in names:
        bd = BatchDict.from_pb(z_in.read("_dict.pb"))
        return [
            decode_item_pb(z_in.read(name), name[:-3], bd)
            for name in z_in.namelist()
            if name.endswith(".pb") and name != "_dict.pb"
        ]

    if "_dict.pb.zst" in names:
        import zstandard as zstd

        dctx = zstd.ZstdDecompressor()
        bd = BatchDict.from_pb(dctx.decompress(z_in.read("_dict.pb.zst")))
        if "_zdict.zstd" in names:
            zdict = zstd.ZstdCompressionDict(z_in.read("_zdict.zstd"))
            dctx_entry = zstd.ZstdDecompressor(dict_data=zdict)
        else:
            dctx_entry = dctx
        return [
            decode_item_pb(dctx_entry.decompress(z_in.read(name)), name[:-7], bd)
            for name in z_in.namelist()
            if name.endswith(".pb.zst") and name != "_dict.pb.zst"
        ]

    msg = "Unrecognized PB v2 ZIP layout: missing _dict.pb or _dict.pb.zst"
    raise ValueError(msg)


def convert_djen_zip_to_pb_zip(
    src_zip: Path,
    dst_zip: Path,
    *,
    mode: CompressionMode = "zstd_dict",
    verify_roundtrip: bool = True,
) -> dict[str, int]:
    """Convert a raw DJEN daily ZIP to a PB v2 ZIP, optionally verifying 100% lossless round-trip."""
    records: list[dict] = []
    with zipfile.ZipFile(src_zip, "r") as zf:
        for name in zf.namelist():
            if name.endswith(".json"):
                parsed = json.loads(zf.read(name))
                records.extend(parsed if isinstance(parsed, list) else parsed.get("items", []))

    out_bytes = encode_records_to_pb_zip_bytes(records, mode=mode)
    if verify_roundtrip:
        decoded = decode_pb_zip_bytes(out_bytes)
        if decoded != records:
            msg = f"Round-trip verification failed for {src_zip}"
            raise ValueError(msg)

    dst_zip.parent.mkdir(parents=True, exist_ok=True)
    dst_zip.write_bytes(out_bytes)
    return {
        "records": len(records),
        "src_bytes": src_zip.stat().st_size,
        "dst_bytes": len(out_bytes),
    }
