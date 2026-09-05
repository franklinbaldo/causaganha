import { describe, expect, it } from 'vitest';
import { ProcessoConsultarSchema } from './processoConsultar.gen';

// Mirrors the fixtures in tests/causaganha_mcp/test_okf_domain_models.py so the
// generated Zod schema (Web) and the generated Pydantic model (MCP) are proven
// against the same ProcessoConsultar shapes, not just against each other's
// existence (#1105).

function fonteCobertura(fonte: string, status: string, registros: number) {
  return {
    type: 'FonteCobertura',
    id: `cobertura-${fonte}`,
    processo_nr: '01316736220028220001',
    fonte,
    status,
    registros,
  };
}

describe('ProcessoConsultarSchema (generated from knowledge/)', () => {
  it('validates a CNJ present in all four sources, with documents', () => {
    const fixture = {
      type: 'Processo',
      nr_processo: '01316736220028220001',
      nr_processo_mascara: '0131673-62.2002.8.22.0001',
      encontrado: true,
      fontes_presentes: ['djen', 'juris', 'stj', 'datajud'],
      djen_id: 'djen-1',
      juris_id: 'juris-1',
      stj_id: 'stj-1',
      datajud_id: 'datajud-1',
      documentos_truncados: false,
      dataset_gerado_em: '2026-09-03T15:54:21+00:00',
      avisos: [],
      djen: {
        type: 'DjenResumo',
        id: 'djen-1',
        primeira_publicacao: '2002-05-01',
        ultima_publicacao: '2010-03-12',
        n_publicacoes: 7,
        tribunais: ['TJRO'],
      },
      juris: {
        type: 'JurisDecisao',
        id: 'juris-1',
        n_documentos: 2,
        tipos: ['acordao'],
        data_julgamento: '2009-11-04',
        orgao: '1ª Câmara Cível',
        relator: 'Des. Fulano',
        classe: 'Apelação',
        url: 'https://tjro.jus.br/juris/juris-1',
      },
      stj: {
        type: 'StjAcordao',
        id: 'stj-1',
        classe: 'REsp',
        relator: 'Min. Sicrana',
        tema: '123',
        tese: 'Tese de exemplo.',
        ementa: 'Ementa de exemplo.',
        data_decisao: '2011-02-01',
        data_publicacao: '2011-02-15',
      },
      datajud: {
        type: 'DatajudCapa',
        id: 'datajud-1',
        classe_oficial: 'Apelação Cível',
        assuntos: 'Indenização por Dano Moral',
        orgao_julgador: '1ª Câmara Cível',
        grau: 'G2',
        data_ajuizamento: '2002-04-20',
        ultima_atualizacao: '2011-03-01T00:00:00+00:00',
      },
      cobertura_dataset: [
        fonteCobertura('djen', 'loaded_remote', 5539302),
        fonteCobertura('juris', 'loaded_remote', 1221386),
        fonteCobertura('stj', 'loaded_remote', 0),
        fonteCobertura('datajud', 'loaded_remote', 27),
      ],
      documentos: [
        {
          type: 'DocumentoProcesso',
          fonte: 'juris',
          id_documento: 'juris-1',
          processo_nr: '01316736220028220001',
          tipo: 'acordao',
          data: '2009-11-04',
          url: 'https://tjro.jus.br/juris/juris-1',
          resumo: 'Resumo truncado da decisão.',
        },
      ],
    };

    const parsed = ProcessoConsultarSchema.parse(fixture);
    expect(parsed.nr_processo).toBe('01316736220028220001');
    expect(parsed.djen?.tribunais).toEqual(['TJRO']);
    expect(parsed.cobertura_dataset).toHaveLength(4);
  });

  it('distinguishes a source genuinely absent (null) from an empty list', () => {
    const fixture = {
      type: 'Processo',
      nr_processo: '01316736220028220001',
      nr_processo_mascara: '0131673-62.2002.8.22.0001',
      encontrado: true,
      fontes_presentes: ['djen', 'juris'],
      djen_id: 'djen-1',
      juris_id: 'juris-1',
      stj_id: '',
      datajud_id: '',
      documentos_truncados: false,
      dataset_gerado_em: '2026-09-03T15:54:21+00:00',
      avisos: [],
      djen: {
        type: 'DjenResumo',
        id: 'djen-1',
        primeira_publicacao: '2002-05-01',
        ultima_publicacao: '2010-03-12',
        n_publicacoes: 7,
        tribunais: ['TJRO'],
      },
      juris: {
        type: 'JurisDecisao',
        id: 'juris-1',
        n_documentos: 2,
        tipos: ['acordao'],
        data_julgamento: '2009-11-04',
        orgao: '1ª Câmara Cível',
        relator: 'Des. Fulano',
        classe: 'Apelação',
        url: 'https://tjro.jus.br/juris/juris-1',
      },
      stj: null,
      datajud: null,
      cobertura_dataset: [
        fonteCobertura('djen', 'loaded_remote', 5539302),
        fonteCobertura('juris', 'loaded_remote', 1221386),
        fonteCobertura('stj', 'loaded_remote_zero_cnj_join', 0),
        fonteCobertura('datajud', 'unavailable', 0),
      ],
      documentos: [],
    };

    const parsed = ProcessoConsultarSchema.parse(fixture);
    expect(parsed.stj).toBeNull();
    expect(parsed.datajud).toBeNull();
    expect(parsed.documentos).toEqual([]);
  });

  it('allows unknown fields within a present source', () => {
    // Mirrors test_processo_consultar_projection_allows_unknown_fields_within_a_present_source
    // in tests/causaganha_mcp/test_okf_domain_models.py (#1105): a source can be present yet
    // only partially known — processoCnj.ts's real DuckDB rows have the same optionality.
    const fixture = {
      type: 'Processo',
      nr_processo: '01316736220028220001',
      nr_processo_mascara: '0131673-62.2002.8.22.0001',
      encontrado: true,
      fontes_presentes: ['djen', 'juris', 'stj', 'datajud'],
      djen_id: 'djen-1',
      juris_id: 'juris-1',
      stj_id: 'stj-1',
      datajud_id: 'datajud-1',
      documentos_truncados: false,
      dataset_gerado_em: '2026-09-03T15:54:21+00:00',
      avisos: [],
      djen: {
        type: 'DjenResumo',
        id: 'djen-1',
        primeira_publicacao: null,
        ultima_publicacao: null,
        n_publicacoes: null,
        tribunais: ['TJRO'],
      },
      juris: {
        type: 'JurisDecisao',
        id: 'juris-1',
        n_documentos: null,
        tipos: ['acordao'],
        data_julgamento: null,
        orgao: null,
        relator: null,
        classe: null,
        url: null,
      },
      stj: {
        type: 'StjAcordao',
        id: 'stj-1',
        classe: 'REsp',
        relator: null,
        tema: null,
        tese: null,
        ementa: null,
        data_decisao: null,
        data_publicacao: null,
      },
      datajud: {
        type: 'DatajudCapa',
        id: 'datajud-1',
        classe_oficial: null,
        assuntos: null,
        orgao_julgador: null,
        grau: null,
        data_ajuizamento: null,
        ultima_atualizacao: null,
      },
      cobertura_dataset: [
        fonteCobertura('djen', 'loaded_remote', 5539302),
        fonteCobertura('juris', 'loaded_remote', 1221386),
        fonteCobertura('stj', 'loaded_remote', 1),
        fonteCobertura('datajud', 'loaded_remote', 1),
      ],
      documentos: [
        {
          type: 'DocumentoProcesso',
          fonte: 'juris',
          id_documento: 'juris-1',
          processo_nr: '01316736220028220001',
          tipo: null,
          data: null,
          url: null,
          resumo: null,
        },
      ],
    };

    const parsed = ProcessoConsultarSchema.parse(fixture);
    expect(parsed.djen?.primeira_publicacao).toBeNull();
    expect(parsed.juris?.orgao).toBeNull();
    expect(parsed.juris?.relator).toBeNull();
    expect(parsed.stj?.tema).toBeNull();
    expect(parsed.datajud?.classe_oficial).toBeNull();
    expect(parsed.documentos[0]?.tipo).toBeNull();
  });

  it('requires nr_processo — an incomplete payload fails loudly', () => {
    const fixture = {
      type: 'Processo',
      nr_processo_mascara: '0131673-62.2002.8.22.0001',
      encontrado: false,
      fontes_presentes: [],
      djen_id: '',
      juris_id: '',
      stj_id: '',
      datajud_id: '',
      documentos_truncados: false,
      dataset_gerado_em: '2026-09-03T15:54:21+00:00',
      avisos: [],
      djen: null,
      juris: null,
      stj: null,
      datajud: null,
      cobertura_dataset: [],
      documentos: [],
    };

    expect(() => ProcessoConsultarSchema.parse(fixture)).toThrow(/nr_processo/);
  });
});
