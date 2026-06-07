import { z } from "zod";

export const CONSOLIDATED_SCHEMA_VERSION = "3";

export const comunicacoesSchema = z.object({
  id: z.string(),
  original_id: z.string(),
  tribunal: z.string(),
  numero_processo: z.string(),
  numero_processo_mascara: z.string(),
  data_disponibilizacao: z.string(), // ISO Date
  tipo_comunicacao: z.string(),
  nome_orgao: z.string(),
  meio: z.string(),
  link: z.string(),
  tipo_documento: z.string(),
  nome_classe: z.string(),
  codigo_classe: z.string(),
  numero_comunicacao: z.string(),
  hash: z.string(),
  processed_at: z.string(), // ISO Timestamp
  texto_id: z.string(),
  p_ano: z.number().int(),
  p_mes: z.number().int(),
  p_item_ia: z.string(),
});

export const advogadosSchema = z.object({
  id: z.string(),
  original_id: z.string(),
  tribunal: z.string(),
  nome: z.string(),
  numero_oab: z.string(),
  uf_oab: z.string(),
  p_ano: z.number().int(),
  p_mes: z.number().int(),
  p_item_ia: z.string(),
});

export const advogadoNomesSchema = z.object({
  advogado_id: z.string(),
  nome: z.string(),
  tribunal: z.string(),
  first_seen: z.string(), // ISO Date
});

export const destinatariosSchema = z.object({
  comunicacao_id: z.string(),
  tribunal: z.string(),
  nome: z.string(),
  polo: z.string(),
  parte_id: z.string(),
  p_ano: z.number().int(),
  p_mes: z.number().int(),
  p_item_ia: z.string(),
});

export const comunicacaoAdvogadosSchema = z.object({
  comunicacao_id: z.string(),
  tribunal: z.string(),
  advogado_id: z.string(),
});

export const textosSchema = z.object({
  id: z.string(),
  texto: z.string(),
});

export const representacoesSchema = z.object({
  comunicacao_id: z.string(),
  tribunal: z.string(),
  advogado_id: z.string(),
  parte_id: z.string(),
  polo: z.string(),
  p_ano: z.number().int(),
  p_mes: z.number().int(),
  p_item_ia: z.string(),
});

export const processosSchema = z.object({
  numero_processo: z.string(),
  tribunal: z.string(),
  data: z.string(), // ISO Date
  comunicacao_id: z.string(),
  p_ano: z.number().int(),
  p_mes: z.number().int(),
  p_item_ia: z.string(),
});

export const partesSchema = z.object({
  id: z.string(),
  nome_normalizado: z.string(),
  nome_original: z.string(),
});

export const consolidatedSchemas = {
  comunicacoes: comunicacoesSchema,
  advogados: advogadosSchema,
  advogado_nomes: advogadoNomesSchema,
  destinatarios: destinatariosSchema,
  comunicacao_advogados: comunicacaoAdvogadosSchema,
  textos: textosSchema,
  representacoes: representacoesSchema,
  processos: processosSchema,
  partes: partesSchema,
};
