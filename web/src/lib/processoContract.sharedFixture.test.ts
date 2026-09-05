import { describe, expect, it } from 'vitest';
import fixture from '../../../tests/fixtures/processo_consultar_shared_core.json';
import { serializeSharedCore } from './processoContract';
import type { SharedCoreInput } from './processoContract';
import type { Fonte } from './processoCnj';

const raw = fixture.domain_input;

function webInput(): SharedCoreInput {
  return {
    encontrado: raw.encontrado,
    nrProcesso: raw.nr_processo,
    nrProcessoMascara: raw.nr_processo_mascara,
    fontesPresentes: raw.fontes_presentes as Fonte[],
    coberturaDataset: raw.cobertura_dataset,
    djen: {
      present: true,
      primeiraPub: raw.djen.primeira_publicacao,
      ultimaPub: raw.djen.ultima_publicacao,
      nPublicacoes: raw.djen.n_publicacoes,
      tribunais: raw.djen.tribunais,
    },
    juris: {
      present: false,
      nDocumentos: null,
      tipos: [],
      dataJulgamento: null,
      orgao: null,
      relator: null,
      classe: null,
      url: null,
    },
    stj: {
      present: true,
      id: raw.stj.id,
      classe: raw.stj.classe,
      relator: raw.stj.relator,
      tema: raw.stj.tema,
      tese: raw.stj.tese,
      ementa: raw.stj.ementa,
      dataDecisao: raw.stj.data_decisao,
      dataPublicacao: raw.stj.data_publicacao,
    },
    datajud: {
      present: false,
      classeOficial: null,
      assuntos: null,
      orgaoJulgador: null,
      grau: null,
      dataAjuizamento: null,
      ultimaAtualizacao: null,
    },
    datasetGeradoEm: raw.dataset_gerado_em,
    avisos: raw.avisos,
  };
}

describe('shared ProcessoConsultar fixture', () => {
  it('produces the same shared product core as the MCP serializer', () => {
    const payload = serializeSharedCore(webInput());
    const comparable = Object.fromEntries(
      Object.keys(fixture.expected_shared).map((key) => [key, payload[key as keyof typeof payload]]),
    );

    expect(comparable).toEqual(fixture.expected_shared);
    expect(payload.documentos).toEqual([]);
    expect(payload.documentos_truncados).toBe(false);
  });
});
