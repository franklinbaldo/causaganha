/**
 * Adapter between `/processo`'s dossier view models and the generated OKF
 * product core (#1105).
 *
 * Mirrors `causaganha_mcp/processo_contract.py`'s `serialize_shared_core` on
 * the Python/MCP side: `processoCnj.ts` builds its `*View` models by hand,
 * with nothing checking that the result still matches the same
 * `ProcessoConsultarSchema` (generated from `knowledge/contracts/`) that the
 * MCP side already validates against. This module closes that gap for the
 * Web runtime — domain data is first validated by the generated contract and
 * only then projected to the public product vocabulary the two surfaces
 * share.
 *
 * Like the Python adapter, this only covers the shared dossier core.
 * `documentos`/`documentos_truncados` parity is deliberately out of scope:
 * unlike MCP's inline bounded list, the Web dossier loads documents as a
 * separate paginated step (`carregarDocumentos`), so `serializeSharedCore`
 * always reports an empty, non-truncated document list here.
 */

import type {
  DatajudCapaView,
  DjenResumoView,
  Fonte,
  FonteCobertura,
  JurisDecisaoView,
  StjAcordaoView,
} from './processoCnj';
import { ProcessoConsultarSchema } from './processoConsultar.gen';

export interface SharedCoreInput {
  encontrado: boolean;
  nrProcesso: string;
  nrProcessoMascara: string;
  fontesPresentes: Fonte[];
  djen: DjenResumoView;
  juris: JurisDecisaoView;
  stj: StjAcordaoView;
  datajud: DatajudCapaView;
  coberturaDataset: FonteCobertura[];
  datasetGeradoEm: string | null;
  avisos: string[];
}

export interface DjenResumoCore {
  primeira_publicacao: string | null;
  ultima_publicacao: string | null;
  n_publicacoes: number | null;
  tribunais: string[];
}

export interface JurisDecisaoCore {
  n_documentos: number | null;
  tipos: string[];
  data_julgamento: string | null;
  orgao: string | null;
  relator: string | null;
  classe: string | null;
  url: string | null;
}

export interface StjAcordaoCore {
  id: string | null;
  classe: string | null;
  relator: string | null;
  tema: string | null;
  tese: string | null;
  ementa: string | null;
  data_decisao: string | null;
  data_publicacao: string | null;
}

export interface DatajudCapaCore {
  classe_oficial: string | null;
  assuntos: string | null;
  orgao_julgador: string | null;
  grau: string | null;
  data_ajuizamento: string | null;
  ultima_atualizacao: string | null;
}

export interface SharedCore {
  encontrado: boolean;
  cnj: string;
  cnj_formatado: string;
  fontes_presentes: string[];
  cobertura_dataset: FonteCobertura[];
  djen: DjenResumoCore | null;
  juris: JurisDecisaoCore | null;
  stj: StjAcordaoCore | null;
  datajud: DatajudCapaCore | null;
  documentos: never[];
  documentos_truncados: false;
  dataset_gerado_em: string | null;
  avisos: string[];
}

/**
 * Stable internal identity for a related OKF concept, satisfying the
 * generated contract's relational shape. Never exposed as a source
 * identifier by the public vocabulary — mirrors
 * `causaganha_mcp.processo_contract._concept_id`.
 */
function conceptId(cnj: string, source: string): string {
  return `${source}:${cnj}`;
}

function buildProjectionPayload(input: SharedCoreInput): Record<string, unknown> {
  const cnj = input.nrProcesso;
  const djenId = input.djen.present ? conceptId(cnj, 'djen') : null;
  const jurisId = input.juris.present ? conceptId(cnj, 'juris') : null;
  const stjId = input.stj.present ? conceptId(cnj, 'stj') : null;
  const datajudId = input.datajud.present ? conceptId(cnj, 'datajud') : null;

  return {
    type: 'Processo',
    nr_processo: cnj,
    nr_processo_mascara: input.nrProcessoMascara,
    encontrado: input.encontrado,
    fontes_presentes: input.fontesPresentes,
    djen_id: djenId,
    juris_id: jurisId,
    stj_id: stjId,
    datajud_id: datajudId,
    documentos_truncados: false,
    dataset_gerado_em: input.datasetGeradoEm,
    avisos: input.avisos,
    djen: input.djen.present
      ? {
          type: 'DjenResumo',
          id: djenId,
          primeira_publicacao: input.djen.primeiraPub,
          ultima_publicacao: input.djen.ultimaPub,
          n_publicacoes: input.djen.nPublicacoes,
          tribunais: input.djen.tribunais,
        }
      : null,
    juris: input.juris.present
      ? {
          type: 'JurisDecisao',
          id: jurisId,
          n_documentos: input.juris.nDocumentos,
          tipos: input.juris.tipos,
          data_julgamento: input.juris.dataJulgamento,
          orgao: input.juris.orgao,
          relator: input.juris.relator,
          classe: input.juris.classe,
          url: input.juris.url,
        }
      : null,
    stj: input.stj.present
      ? {
          type: 'StjAcordao',
          id: stjId,
          classe: input.stj.classe,
          relator: input.stj.relator,
          tema: input.stj.tema,
          tese: input.stj.tese,
          ementa: input.stj.ementa,
          data_decisao: input.stj.dataDecisao,
          data_publicacao: input.stj.dataPublicacao,
        }
      : null,
    datajud: input.datajud.present
      ? {
          type: 'DatajudCapa',
          id: datajudId,
          classe_oficial: input.datajud.classeOficial,
          assuntos: input.datajud.assuntos,
          orgao_julgador: input.datajud.orgaoJulgador,
          grau: input.datajud.grau,
          data_ajuizamento: input.datajud.dataAjuizamento,
          ultima_atualizacao: input.datajud.ultimaAtualizacao,
        }
      : null,
    cobertura_dataset: input.coberturaDataset.map((c) => ({
      type: 'FonteCobertura',
      id: conceptId(cnj, `cobertura:${c.fonte}`),
      processo_nr: cnj,
      fonte: c.fonte,
      status: c.status,
      registros: c.registros,
    })),
    documentos: [],
  };
}

/**
 * Validate the shared dossier core against the generated OKF contract and
 * return its public product shape.
 *
 * Surface-only fields such as loading state, share-URL params or pagination
 * cursors are deliberately absent — those stay local to `/processo`'s Svelte
 * component, never pushed into the shared domain contract. The public STJ
 * `id` stays the real source identifier (`input.stj.id`); the generated
 * relation uses a separate internal concept identity, so a missing source
 * identifier never becomes a fabricated public value.
 */
export function serializeSharedCore(input: SharedCoreInput): SharedCore {
  const core = ProcessoConsultarSchema.parse(buildProjectionPayload(input));

  return {
    encontrado: core.encontrado,
    cnj: core.nr_processo,
    cnj_formatado: core.nr_processo_mascara,
    fontes_presentes: core.fontes_presentes,
    cobertura_dataset: core.cobertura_dataset.map((c) => ({
      fonte: c.fonte,
      status: c.status,
      registros: Number(c.registros),
    })),
    djen: core.djen
      ? {
          primeira_publicacao: core.djen.primeira_publicacao,
          ultima_publicacao: core.djen.ultima_publicacao,
          n_publicacoes: core.djen.n_publicacoes === null ? null : Number(core.djen.n_publicacoes),
          tribunais: core.djen.tribunais,
        }
      : null,
    juris: core.juris
      ? {
          n_documentos: core.juris.n_documentos === null ? null : Number(core.juris.n_documentos),
          tipos: core.juris.tipos,
          data_julgamento: core.juris.data_julgamento,
          orgao: core.juris.orgao,
          relator: core.juris.relator,
          classe: core.juris.classe,
          url: core.juris.url,
        }
      : null,
    stj: core.stj
      ? {
          id: input.stj.id,
          classe: core.stj.classe,
          relator: core.stj.relator,
          tema: core.stj.tema,
          tese: core.stj.tese,
          ementa: core.stj.ementa,
          data_decisao: core.stj.data_decisao,
          data_publicacao: core.stj.data_publicacao,
        }
      : null,
    datajud: core.datajud
      ? {
          classe_oficial: core.datajud.classe_oficial,
          assuntos: core.datajud.assuntos,
          orgao_julgador: core.datajud.orgao_julgador,
          grau: core.datajud.grau,
          data_ajuizamento: core.datajud.data_ajuizamento,
          ultima_atualizacao: core.datajud.ultima_atualizacao,
        }
      : null,
    documentos: [],
    documentos_truncados: false,
    dataset_gerado_em: core.dataset_gerado_em,
    avisos: core.avisos,
  };
}
