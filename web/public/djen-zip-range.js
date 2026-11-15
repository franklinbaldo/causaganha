/** Read a single JSON member of an IA-hosted DJEN ZIP with bounded HTTP Ranges.
 *
 * Requires a deployed CORS proxy at proxyBase that forwards 206 responses,
 * and a browser with DecompressionStream('deflate-raw'). No ZIP is downloaded
 * in full. ZIP64/multidisk archives intentionally fail closed.
 */
// CORS + Range proxy for IA downloads (deployment/djen_proxy.go).
const DEFAULT_ARCHIVE_BASE = "https://djen-proxy-mhgmawcn3a-rj.a.run.app";
const CHUNK = 1024 * 1024;
const MAX_MEMBER_BYTES = 32 * 1024 * 1024;

async function rangeBytes(proxyBase, item, zip, start, length) {
  if (!Number.isSafeInteger(start) || start < 0 ||
      !Number.isSafeInteger(length) || length < 1) {
    throw new Error("Intervalo ZIP inválido");
  }
  const url = proxyBase.replace(/\/$/, "") + "/download/" +
    encodeURIComponent(item) + "/" + encodeURIComponent(zip);
  const pieces = [];
  let size = 0;
  while (size < length) {
    const chunkLength = Math.min(CHUNK, length - size);
    const left = start + size;
    const right = left + chunkLength - 1;
    const response = await fetch(url, { headers: { Range: "bytes=" + left + "-" + right } });
    if (response.status !== 206) {
      throw new Error("Servidor não respeitou HTTP Range: " + response.status);
    }
    const contentRange = response.headers.get("Content-Range") || "";
    if (!contentRange.startsWith("bytes " + left + "-" + right + "/")) {
      throw new Error("Content-Range incompatível");
    }
    const bytes = new Uint8Array(await response.arrayBuffer());
    if (bytes.length !== chunkLength) throw new Error("Intervalo ZIP incompleto");
    pieces.push(bytes);
    size += bytes.length;
  }
  const result = new Uint8Array(length);
  let offset = 0;
  for (const bytes of pieces) {
    result.set(bytes, offset);
    offset += bytes.length;
  }
  return result;
}

function findEOCD(bytes) {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  for (let i = bytes.length - 22; i >= 0; i--) {
    if (view.getUint32(i, true) !== 0x06054b50) continue;
    const comment = view.getUint16(i + 20, true);
    if (i + 22 + comment !== bytes.length) continue;
    const disk = view.getUint16(i + 4, true);
    const entries = view.getUint16(i + 10, true);
    const directoryBytes = view.getUint32(i + 12, true);
    const directoryOffset = view.getUint32(i + 16, true);
    if (disk !== 0 || entries === 0xffff ||
        directoryBytes === 0xffffffff || directoryOffset === 0xffffffff) {
      throw new Error("ZIP64 ou multidisco não suportado");
    }
    return { entries, directoryBytes, directoryOffset };
  }
  throw new Error("Diretório central ZIP não encontrado");
}

function locateMember(bytes, requested) {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const decoder = new TextDecoder("utf-8", { fatal: true });
  for (let offset = 0; offset + 46 <= bytes.length;) {
    if (view.getUint32(offset, true) !== 0x02014b50) {
      throw new Error("Diretório central ZIP inválido");
    }
    const flags = view.getUint16(offset + 8, true);
    const compression = view.getUint16(offset + 10, true);
    const compressed = view.getUint32(offset + 20, true);
    const uncompressed = view.getUint32(offset + 24, true);
    const nameLength = view.getUint16(offset + 28, true);
    const extraLength = view.getUint16(offset + 30, true);
    const commentLength = view.getUint16(offset + 32, true);
    const localOffset = view.getUint32(offset + 42, true);
    const end = offset + 46 + nameLength + extraLength + commentLength;
    if (end > bytes.length) throw new Error("Cabeçalho truncado");
    const name = decoder.decode(bytes.subarray(offset + 46, offset + 46 + nameLength));
    if (name === requested) {
      if (flags & 1 || ![0, 8].includes(compression)) {
        throw new Error("Membro ZIP criptografado ou compressão não suportada");
      }
      if (uncompressed > MAX_MEMBER_BYTES || compressed > MAX_MEMBER_BYTES) {
        throw new Error("Membro ZIP excede o orçamento de leitura");
      }
      return { compression, compressed, uncompressed, localOffset };
    }
    offset = end;
  }
  throw new Error("JSON não localizado no ZIP original");
}

async function unzipMember(compressedBytes, method, expectedSize) {
  if (method === 0) return compressedBytes;
  if (typeof DecompressionStream === "undefined") {
    throw new Error("Navegador sem suporte a descompressão DEFLATE");
  }
  const stream = new Blob([compressedBytes]).stream()
    .pipeThrough(new DecompressionStream("deflate-raw"));
  const reader = stream.getReader();
  const chunks = [];
  let total = 0;
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    total += value.length;
    if (total > MAX_MEMBER_BYTES) {
      await reader.cancel();
      throw new Error("JSON descompactado excede o limite");
    }
    chunks.push(value);
  }
  if (total !== expectedSize) throw new Error("Tamanho descompactado diferente do ZIP");
  const all = new Uint8Array(total);
  let at = 0;
  for (const bytes of chunks) {
    all.set(bytes, at);
    at += bytes.length;
  }
  return all;
}

async function tailBytes(proxyBase, item, zip, length) {
  // Suffix range: the ZIP tail *and* its total size (from Content-Range) in one
  // request, so no /metadata call is needed (djen-proxy only serves /download).
  const url = proxyBase.replace(/\/$/, "") + "/download/" +
    encodeURIComponent(item) + "/" + encodeURIComponent(zip);
  const response = await fetch(url, { headers: { Range: "bytes=-" + length } });
  if (response.status !== 206) {
    throw new Error("Servidor não respeitou HTTP Range: " + response.status);
  }
  const match = /^bytes (\d+)-(\d+)\/(\d+)$/.exec(response.headers.get("Content-Range") || "");
  if (!match) throw new Error("Content-Range incompatível");
  const [start, end, total] = match.slice(1).map(Number);
  const bytes = new Uint8Array(await response.arrayBuffer());
  if (end !== total - 1 || bytes.length !== end - start + 1) {
    throw new Error("Cauda ZIP incompleta");
  }
  return { bytes, total };
}

const ORIGINAL_DJEN = (item, zip, member) =>
  /^djen-[a-z0-9]+-20\d{2}$/.test(item) &&
  /^djen-20\d{2}-\d{2}-\d{2}-[A-Z0-9]+\.zip$/.test(zip) &&
  /^[A-Za-z0-9_.-]+\.json$/.test(member);
// Process (filing) years start well before 2000; the index item uses them.
const POINTER_INDEX = (item, zip, member) =>
  /^causaganha-(19|20)\d{2}-[0-9]-[0-9]{2}$/.test(item) &&
  /^[0-9]{4}\.zip$/.test(zip) &&
  /^[0-9]{9}\.pb$/.test(member);
const ORIGINAL_DATAJUD = (item, zip, member) =>
  /^datajud-[a-z0-9]+$/.test(item) &&
  /^[a-z0-9]+_20\d{2}-\d{2}-\d{2}(T\d{6}Z)?\.zip$/.test(zip) &&
  /^[0-9]{20}\.json(\.gz)?$/.test(member);

export async function readOriginalMember({ item, zip, member, proxyBase = DEFAULT_ARCHIVE_BASE, asText = false, asBytes = false }) {
  const baseUrl = (proxyBase || DEFAULT_ARCHIVE_BASE).replace(/\/$/, "");
  const allowed = ORIGINAL_DJEN(item, zip, member) || POINTER_INDEX(item, zip, member) ||
    ORIGINAL_DATAJUD(item, zip, member);
  if (!allowed || member.includes("..")) {
    throw new Error("Identificadores de arquivo inválidos");
  }
  const { bytes: tail, total: zipSize } = await tailBytes(baseUrl, item, zip, 65557);
  if (zipSize < 22) throw new Error("Tamanho ZIP inválido");
  const directory = findEOCD(tail);
  if (directory.directoryBytes > MAX_MEMBER_BYTES) throw new Error("Diretório ZIP excessivo");
  const central = await rangeBytes(baseUrl, item, zip,
    directory.directoryOffset, directory.directoryBytes);
  const found = locateMember(central, member);
  const header = await rangeBytes(baseUrl, item, zip, found.localOffset, 30);
  const h = new DataView(header.buffer, header.byteOffset, header.byteLength);
  if (h.getUint32(0, true) !== 0x04034b50) throw new Error("Cabeçalho local ZIP inválido");
  const start = found.localOffset + 30 + h.getUint16(26, true) + h.getUint16(28, true);
  const payload = await rangeBytes(baseUrl, item, zip, start, found.compressed);
  const json = await unzipMember(payload, found.compression, found.uncompressed);
  if (asBytes) return json;
  const text = new TextDecoder("utf-8", { fatal: true }).decode(json);
  return asText ? text : JSON.parse(text);
}
