import { describe, expect, it } from 'vitest';
import { serializeSharedCore } from './processoContract';
import type { SharedCoreInput } from './processoContract';

// Mirrors tests/causaganha_mcp/test_processo_contract_adapter.py's shape and
// intent (#1105 slice 2): the Web normalizer must validate the same shared
// dossier core through the generated OKF contract (`ProcessoConsultarSchema`)
// before exposing it in the public vocabulary, exactly like
// `causaganha_mcp.processo_contract.serialize_shared_core` does for the MCP
// side — same field names, same "absent source is null, not a fabricated
// object" rule, same "internal OKF id/type metadata never leaks" rule.

const CNJ = '00000010220248220001';
const CNJ_MASCARA = '0000001-02.2024.8.22.0001';

function baseInput(overrides: Partial<SharedCoreInput> = {}): SharedCoreInput {
  return {
    encontrado: true,
    nrProcesso: CNJ,
    nrProcessoMascara: CNJ_MASCARA,
    fontesPresentes: [],
    djen: { present: false, primeiraPub: null, ultimaPub: null, nPublicacoes: null, tribunais: [] },
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
      present: false,
      id: null,
      classe: null,
      relator: null,
      tema: null,
      tese: null,
      ementa: null,
      dataDecisao: null,
      dataPublicacao: null,
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
    coberturaDataset: [],
    datasetGeradoEm: null,
    avisos: [],
    ...overrides,
  };
}

describe('serializeSharedCore', () => {
  it('validates the shared core then exposes it in the public vocabulary', () => {
    const input = baseInput({
      fontesPresentes: ['djen', 'juris', 'stj'],
      djen: {
        present: true,
        primeiraPub: '2024-03-01',
        ultimaPub: '2024-03-05',
        nPublicacoes: 2,
        tribunais: ['TJRO'],
      },
      juris: {
        present: true,
        nDocumentos: 1,
        tipos: ['ACÓRDÃO'],
        dataJulgamento: null,
        orgao: null,
        relator: null,
        classe: null,
        url: null,
      },
      stj: {
        present: true,
        id: 'source-stj-1',
        classe: 'REsp',
        relator: null,
        tema: null,
        tese: null,
        ementa: null,
        dataDecisao: null,
        dataPublicacao: null,
      },
      coberturaDataset: [{ fonte: 'djen', status: 'loaded_remote', registros: 10 }],
      avisos: ['freshness desconhecida'],
    });

    const core = serializeSharedCore(input);

    expect(core.cnj).toBe(CNJ);
    expect(core.cnj_formatado).toBe(CNJ_MASCARA);
    expect(core).not.toHaveProperty('nr_processo');
    expect(core).not.toHaveProperty('type');
    expect(core).not.toHaveProperty('djen_id');
    expect(core.stj?.id).toBe('source-stj-1');
    expect(core.juris?.relator).toBeNull();
    expect(core.dataset_gerado_em).toBeNull();
    expect(core.avisos).toEqual(['freshness desconhecida']);
  });

  it('reports every absent source as null, never a fabricated object', () => {
    const core = serializeSharedCore(baseInput());

    expect(core.encontrado).toBe(true);
    expect(core.djen).toBeNull();
    expect(core.juris).toBeNull();
    expect(core.stj).toBeNull();
    expect(core.datajud).toBeNull();
    expect(core.fontes_presentes).toEqual([]);
  });

  it('mirrors coverage entries with the same field names DuckDB already produces', () => {
    const input = baseInput({
      coberturaDataset: [
        { fonte: 'djen', status: 'loaded_remote', registros: 5539302 },
        { fonte: 'stj', status: 'unavailable', registros: 0 },
      ],
    });

    const core = serializeSharedCore(input);

    expect(core.cobertura_dataset).toEqual([
      { fonte: 'djen', status: 'loaded_remote', registros: 5539302 },
      { fonte: 'stj', status: 'unavailable', registros: 0 },
    ]);
  });

  it('never inlines documents — the Web dossier loads them as a separate paginated step', () => {
    const core = serializeSharedCore(baseInput());

    expect(core.documentos).toEqual([]);
    expect(core.documentos_truncados).toBe(false);
  });
});
