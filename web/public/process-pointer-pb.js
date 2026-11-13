/** Decoder for process_pointer.proto, no runtime dependency or document copies. */

function varint(bytes, index) {
  let value = 0n;
  for (let i = 0; i < 10; i++) {
    if (index >= bytes.length) throw new Error("Protobuf truncado");
    const byte = bytes[index++];
    if (i === 9 && byte > 1) throw new Error("Protobuf varint overflow");
    value |= BigInt(byte & 127) << BigInt(i * 7);
    if (!(byte & 128)) return [value, index];
  }
  throw new Error("Protobuf varint longo demais");
}

function fields(bytes) {
  const out = [];
  for (let index = 0; index < bytes.length;) {
    const [tag, next] = varint(bytes, index);
    index = next;
    const number = Number(tag >> 3n);
    const wire = Number(tag & 7n);
    if (!number) throw new Error("Campo protobuf inválido");
    let value;
    if (wire === 0) {
      [value, index] = varint(bytes, index);
    } else if (wire === 2) {
      const [length, afterLength] = varint(bytes, index);
      index = afterLength;
      if (length > BigInt(bytes.length - index)) throw new Error("Campo truncado");
      const end = index + Number(length);
      value = bytes.subarray(index, end);
      index = end;
    } else if (wire === 1 || wire === 5) {
      const length = wire === 1 ? 8 : 4;
      if (index + length > bytes.length) throw new Error("Campo truncado");
      value = bytes.subarray(index, index + length);
      index += length;
    } else {
      throw new Error("Wire type protobuf não suportado");
    }
    out.push({ number, wire, value });
  }
  return out;
}

const decoder = new TextDecoder("utf-8", { fatal: true });
function parseMessage(bytes, schema) {
  const record = {};
  for (const { number, wire, value } of fields(bytes)) {
    const entry = schema[number];
    if (!entry) continue;
    const [key, type] = entry;
    if (type === "string" && wire === 2) record[key] = decoder.decode(value);
    if (type === "uint64" && wire === 0) record[key] = value.toString();
  }
  for (const [key] of Object.values(schema)) {
    if (record[key] === undefined) throw new Error("Ponteiro protobuf incompleto: " + key);
  }
  return record;
}

const DJEN = {
  1: ["data", "string"], 2: ["membro_json", "string"],
  3: ["comunicacao_id", "uint64"], 4: ["hash", "string"]
};
const DATAJUD = {
  1: ["tribunal", "string"], 2: ["grau", "string"],
  3: ["documento_id", "string"], 4: ["item_ia", "string"],
  5: ["arquivo_zip", "string"], 6: ["membro", "string"],
  7: ["atualizado_em", "string"]
};

export function decodeProcessIndex(bytes) {
  const document = { publicacoes: [], datajud: [] };
  let version = null;
  for (const { number, wire, value } of fields(bytes)) {
    if (number === 1 && wire === 2) document.publicacoes.push(parseMessage(value, DJEN));
    if (number === 2 && wire === 2) document.datajud.push(parseMessage(value, DATAJUD));
    if (number === 15 && wire === 0) version = Number(value);
  }
  if (version !== 1) throw new Error("Versão do índice Protobuf desconhecida");
  return document;
}
