import DOMPurify from "dompurify";
import { z } from "zod";

const optionalString = z.preprocess((value) => {
  if (value === null || value === undefined) {
    return undefined;
  }

  return typeof value === "string" ? value : String(value);
}, z.string().optional());

const optionalNumber = z.preprocess((value) => {
  if (value === null || value === undefined || value === "") {
    return undefined;
  }

  if (typeof value === "number") {
    return Number.isFinite(value) ? value : undefined;
  }

  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : undefined;
  }

  return undefined;
}, z.number().optional());

const optionalBoolean = z.preprocess((value) => {
  if (value === null || value === undefined) {
    return undefined;
  }

  if (typeof value === "boolean") {
    return value;
  }

  if (typeof value === "string") {
    if (value.toLowerCase() === "true") {
      return true;
    }

    if (value.toLowerCase() === "false") {
      return false;
    }
  }

  return undefined;
}, z.boolean().optional());

function normalizeDateString(value: unknown): string | undefined {
  if (value === null || value === undefined || value === "") {
    return undefined;
  }

  const raw = typeof value === "string" ? value.trim() : String(value).trim();

  if (!raw) {
    return undefined;
  }

  const isoDateMatch = raw.match(/^(\d{4}-\d{2}-\d{2})/);
  if (isoDateMatch) {
    return isoDateMatch[1];
  }

  const brDateMatch = raw.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (brDateMatch) {
    const [, day, month, year] = brDateMatch;
    return `${year}-${month}-${day}`;
  }

  const dashedBrDateMatch = raw.match(/^(\d{2})-(\d{2})-(\d{4})$/);
  if (dashedBrDateMatch) {
    const [, day, month, year] = dashedBrDateMatch;
    return `${year}-${month}-${day}`;
  }

  return raw;
}

function normalizeLabel(value: unknown): string {
  return (typeof value === "string" ? value : String(value))
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

const optionalDateString = z.preprocess(
  normalizeDateString,
  z
    .string()
    .refine((value) => /^\d{4}-\d{2}-\d{2}$/.test(value), "Expected date in YYYY-MM-DD format")
    .optional(),
);

function normalizeMeio(value: unknown): "D" | "E" | undefined {
  if (value === null || value === undefined || value === "") {
    return undefined;
  }

  const raw = normalizeLabel(value);

  if (!raw) {
    return undefined;
  }

  if (
    raw === "d" ||
    raw === "diario" ||
    raw === "diario eletronico" ||
    raw === "eletronico" ||
    raw === "eletronico nacional"
  ) {
    return "D";
  }

  if (raw === "e" || raw === "edital" || raw === "edital eletronico") {
    return "E";
  }

  return undefined;
}

function normalizePolo(value: unknown): "A" | "P" | "T" | "D" | undefined {
  if (value === null || value === undefined || value === "") {
    return undefined;
  }

  const raw = normalizeLabel(value);

  if (!raw) {
    return undefined;
  }

  if (raw === "a" || raw === "ativo" || raw === "ativa" || raw === "autor" || raw === "autora") {
    return "A";
  }

  if (raw === "p" || raw === "passivo" || raw === "passiva" || raw === "reu" || raw === "re") {
    return "P";
  }

  if (raw === "t" || raw === "terceiro" || raw === "terceira") {
    return "T";
  }

  if (raw === "d" || raw === "destinatario") {
    return "D";
  }

  return undefined;
}

function looksLikeHtml(value: string): boolean {
  return /<\/?[a-z][\s\S]*>/i.test(value);
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function sanitizeHtml(value: string): string {
  if (typeof window === "undefined") {
    return escapeHtml(value);
  }
  return DOMPurify.sanitize(value, {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ["script", "style"],
    FORBID_ATTR: ["style"],
  });
}

function normalizeExternalUrl(value: unknown): string | undefined {
  if (value === null || value === undefined || value === "") {
    return undefined;
  }

  const raw = typeof value === "string" ? value.trim() : String(value).trim();
  if (!raw) {
    return undefined;
  }

  try {
    const url = new URL(raw);
    if (url.protocol === "http:" || url.protocol === "https:") {
      return url.toString();
    }
  } catch {
    return undefined;
  }

  return undefined;
}

export const DjenTextoRenderSchema = z.union([
  z.object({
    kind: z.literal("html"),
    content: z.string(),
  }),
  z.object({
    kind: z.literal("text"),
    content: z.string(),
  }),
]);

export const DjenMeioSchema = z.enum(["D", "E"]);
export const DjenPoloSchema = z.enum(["A", "P", "T", "D"]);
export const DjenTipoComunicacaoCodigoSchema = z.enum(["C", "I", "E", "P", "L", "A"]);

export const DjenLoginRequestSchema = z.object({
  login: z.string(),
  senha: z.string(),
});

export const DjenLoginResponseSchema = z.object({
  user: z
    .object({
      id: z.number().int().optional(),
      nome: optionalString,
      email: optionalString,
      cpf: optionalString,
    })
    .optional(),
  access_token: optionalString,
});

export const DjenAdvogadoSchema = z
  .object({
    id: optionalNumber,
    nome: optionalString,
    numero_oab: optionalString,
    uf_oab: optionalString,
    tipo_inscricao: optionalString,
    email: optionalString,
  })
  .passthrough();

export const DjenDestinatarioSchema = z
  .object({
    nome: optionalString,
    polo: optionalString,
    comunicacao_id: optionalNumber,
    cpf_cnpj: optionalString,
  })
  .passthrough()
  .transform((value) => ({
    ...value,
    polo: normalizePolo(value.polo),
  }));

export const DjenDestinatarioAdvogadoSchema = z
  .object({
    id: optionalNumber,
    comunicacao_id: optionalNumber,
    advogado_id: optionalNumber,
    created_at: optionalString,
    updated_at: optionalString,
    advogado: DjenAdvogadoSchema.optional(),
  })
  .passthrough();

const DjenPublicationSourceSchema = z
  .object({
    id: optionalNumber,
    data_disponibilizacao: optionalDateString,
    datadisponibilizacao: optionalDateString,
    dataDisponibilizacao: optionalDateString,
    siglaTribunal: optionalString,
    sigla_tribunal: optionalString,
    tipoComunicacao: optionalString,
    tipo_comunicacao: optionalString,
    nomeOrgao: optionalString,
    nome_orgao: optionalString,
    orgao: optionalString,
    idOrgao: optionalNumber,
    id_orgao: optionalNumber,
    texto: optionalString,
    numero_processo: optionalString,
    numeroProcesso: optionalString,
    meio: optionalString,
    link: optionalString,
    tipoDocumento: optionalString,
    tipo_documento: optionalString,
    nomeClasse: optionalString,
    nome_classe: optionalString,
    codigoClasse: optionalString,
    codigo_classe: optionalString,
    numeroComunicacao: optionalNumber,
    numero_comunicacao: optionalNumber,
    ativo: optionalBoolean,
    hash: optionalString,
    status: optionalString,
    motivo_cancelamento: optionalString,
    data_cancelamento: optionalString,
    meiocompleto: optionalString,
    numeroprocessocommascara: optionalString,
    destinatarios: z.array(DjenDestinatarioSchema).optional(),
    destinatarioadvogados: z.array(DjenDestinatarioAdvogadoSchema).optional(),
  })
  .passthrough();

export const DjenPublicationSchema = DjenPublicationSourceSchema.transform((value) => ({
  ...value,
  data_disponibilizacao:
    value.data_disponibilizacao ?? value.datadisponibilizacao ?? value.dataDisponibilizacao,
  siglaTribunal: value.siglaTribunal ?? value.sigla_tribunal,
  tipoComunicacao: value.tipoComunicacao ?? value.tipo_comunicacao,
  nomeOrgao: value.nomeOrgao ?? value.nome_orgao ?? value.orgao,
  idOrgao: value.idOrgao ?? value.id_orgao,
  numero_processo: value.numero_processo ?? value.numeroProcesso,
  meio: normalizeMeio(value.meio),
  link: normalizeExternalUrl(value.link),
  tipoDocumento: value.tipoDocumento ?? value.tipo_documento,
  nomeClasse: value.nomeClasse ?? value.nome_classe,
  codigoClasse: value.codigoClasse ?? value.codigo_classe,
  numeroComunicacao: value.numeroComunicacao ?? value.numero_comunicacao,
  textoRender: value.texto
    ? looksLikeHtml(value.texto)
      ? { kind: "html" as const, content: sanitizeHtml(value.texto) }
      : { kind: "text" as const, content: value.texto }
    : undefined,
}));

export type DjenPublication = z.infer<typeof DjenPublicationSchema>;
export type DjenDestinatario = z.infer<typeof DjenDestinatarioSchema>;
export type DjenDestinatarioAdvogado = z.infer<typeof DjenDestinatarioAdvogadoSchema>;
export type DjenAdvogado = z.infer<typeof DjenAdvogadoSchema>;

export const DjenPublicationCollectionSchema = z
  .union([
    z.array(DjenPublicationSchema),
    z.object({ items: z.array(DjenPublicationSchema) }).passthrough(),
  ])
  .transform((value) => (Array.isArray(value) ? value : value.items));

export const DjenComunicacaoQuerySchema = z
  .object({
    numeroOab: optionalString,
    ufOab: optionalString,
    nomeAdvogado: optionalString,
    nomeParte: optionalString,
    numeroProcesso: optionalString,
    dataDisponibilizacaoInicio: optionalDateString,
    dataDisponibilizacaoFim: optionalDateString,
    siglaTribunal: optionalString,
    numeroComunicacao: optionalNumber,
    pagina: optionalNumber,
    itensPorPagina: optionalNumber,
    orgaoId: optionalNumber,
    meio: DjenMeioSchema.optional(),
  })
  .passthrough();

export const DjenComunicacaoListResponseSchema = z.object({
  status: optionalString,
  message: optionalString,
  count: optionalNumber,
  items: z.array(DjenPublicationSchema).default([]),
});

export const DjenCreateComunicacaoRequestSchema = z
  .object({
    codigo_classe: z.string(),
    numero_processo: z.string(),
    sigla_tribunal: z.string(),
    meio: DjenMeioSchema,
    link: optionalString,
    texto: optionalString,
    tipo_documento: z.string(),
    orgao: z.string(),
    data_disponibilizacao: optionalDateString,
    tipo_comunicacao: DjenTipoComunicacaoCodigoSchema,
    destinatarios: z.array(
      z
        .object({
          nome: optionalString,
          cpf_cnpj: optionalString,
          polo: DjenPoloSchema.optional(),
        })
        .passthrough(),
    ),
    advogados: z
      .array(
        z
          .object({
            nome: optionalString,
            numero_oab: optionalString,
            uf_oab: optionalString,
          })
          .passthrough(),
      )
      .optional(),
  })
  .passthrough();

export const DjenCreateComunicacaoResponseItemSchema = z
  .object({
    tribunal_id: optionalNumber,
    classe_id: optionalNumber,
    tipo_documento_id: optionalNumber,
    orgao_id: optionalNumber,
    tipo_id: optionalNumber,
    id: optionalNumber,
    data_publicacao: optionalDateString,
    texto: optionalString,
    numero_processo: optionalString,
    meio: DjenMeioSchema.optional(),
    link: optionalString,
    numero_comunicacao: optionalNumber,
    ativo: optionalBoolean,
    hash: optionalString,
    meiocompleto: optionalString,
    numeroprocessocommascara: optionalString,
    destinatarios: z.array(DjenDestinatarioSchema).optional(),
    destinatarioadvogados: z.array(DjenDestinatarioAdvogadoSchema).optional(),
  })
  .passthrough();

export const DjenCreateComunicacaoResponseSchema = z.object({
  status: optionalString,
  message: optionalString,
  items: z.array(DjenCreateComunicacaoResponseItemSchema).default([]),
});

export const DjenDeleteComunicacaoParamsSchema = z.object({
  id: z.string(),
});

export const DjenDeleteComunicacaoRequestSchema = z.object({
  motivo_cancelamento: z.string(),
});

export const DjenDeleteComunicacaoResponseSchema = z.object({
  status: optionalString,
  message: optionalString,
});

export const DjenCertidaoParamsSchema = z.object({
  hash: z.string(),
});

export const DjenTribunalSchema = z
  .object({
    id: optionalNumber,
    nome: optionalString,
    sigla: optionalString,
    jurisdicao: optionalString,
    endereco: optionalString,
    telefone: optionalString,
  })
  .passthrough();

export const DjenTribunalListSchema = z.array(DjenTribunalSchema);

export const DjenErrorResponseSchema = z.object({
  status: optionalString,
  message: optionalString,
});

export const DjenCadernoParamsSchema = z.object({
  sigla_tribunal: z.string(),
  data: optionalDateString,
  meio: DjenMeioSchema,
});

export const DjenCadernoSchema = z.object({
  tribunal: optionalString,
  sigla_tribunal: optionalString,
  meio: DjenMeioSchema.optional(),
  status: optionalString,
  versao: optionalString,
  data: optionalDateString,
  total_comunicacoes: optionalNumber,
  numero_paginas: optionalNumber,
  hash: optionalString,
  url: optionalString,
});

export function parseDjenPublication(input: unknown): DjenPublication {
  return DjenPublicationSchema.parse(input);
}

export function parseDjenPublicationCollection(input: unknown): DjenPublication[] {
  return DjenPublicationCollectionSchema.parse(input);
}

export function parseDjenPublicationCollectionSafely(input: unknown): DjenPublication[] {
  const collectionResult = z
    .union([
      z.array(z.unknown()),
      z.object({ items: z.array(z.unknown()) }).passthrough(),
    ])
    .safeParse(input);

  if (!collectionResult.success) {
    return [];
  }

  const items = Array.isArray(collectionResult.data)
    ? collectionResult.data
    : collectionResult.data.items;

  const publications: DjenPublication[] = [];

  for (const item of items) {
    const parsed = DjenPublicationSchema.safeParse(item);
    if (parsed.success) {
      publications.push(parsed.data);
    }
  }

  return publications;
}
