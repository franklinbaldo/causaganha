import { describe, expect, it } from 'vitest';
import {
  ALL_FONTES,
  buildCnjSearchParams,
  buildProcessoDocumentosSql,
  buildProcessoUnificadoSql,
  classifyCnjInput,
  completude,
  formatCnj,
  isDocumentosVazio,
  isValidCnj,
  mapDocumentoRow,
  mapProcessoRow,
  normalizeCnj,
  paginate,
  readCnjParam,
  stripCnjMask,
  toIsoDate,
} from './processoCnj';

describe('stripCnjMask / isValidCnj / normalizeCnj', () => {
  it('strips a fully masked CNJ down to 20 digits', () => {
    expect(stripCnjMask('0000001-02.2024.8.22.0001')).toBe('00000010220248220001');
  });

  it('accepts an already-unmasked 20-digit CNJ', () => {
    expect(normalizeCnj('00000010220248220001')).toBe('00000010220248220001');
  });

  it('accepts a masked CNJ and returns the digits', () => {
    expect(normalizeCnj('0000001-02.2024.8.22.0001')).toBe('00000010220248220001');
  });

  it('tolerates surrounding whitespace and stray characters', () => {
    expect(normalizeCnj('  0000001-02.2024.8.22.0001  ')).toBe('00000010220248220001');
  });

  it('rejects too few digits', () => {
    expect(normalizeCnj('123')).toBe('');
    expect(isValidCnj('123')).toBe(false);
  });

  it('rejects too many digits', () => {
    expect(normalizeCnj('123456789012345678901')).toBe('');
  });

  it('rejects empty input', () => {
    expect(normalizeCnj('')).toBe('');
  });
});

describe('formatCnj', () => {
  it('masks a valid 20-digit CNJ', () => {
    expect(formatCnj('00000010220248220001')).toBe('0000001-02.2024.8.22.0001');
  });

  it('returns the input unchanged when not exactly 20 digits', () => {
    expect(formatCnj('123')).toBe('123');
  });
});

describe('classifyCnjInput', () => {
  it('classifies empty/whitespace-only input as empty', () => {
    expect(classifyCnjInput('')).toBe('empty');
    expect(classifyCnjInput('   ')).toBe('empty');
  });

  it('classifies a wrong-length or non-numeric input as invalid', () => {
    expect(classifyCnjInput('123')).toBe('invalid');
    expect(classifyCnjInput('abcde')).toBe('invalid');
  });

  it('classifies a valid masked or unmasked CNJ as valid', () => {
    expect(classifyCnjInput('00000010220248220001')).toBe('valid');
    expect(classifyCnjInput('0000001-02.2024.8.22.0001')).toBe('valid');
  });
});

describe('readCnjParam / buildCnjSearchParams', () => {
  it('reads ?cnj= from a query string', () => {
    expect(readCnjParam('?cnj=0000001-02.2024.8.22.0001')).toBe('0000001-02.2024.8.22.0001');
  });

  it('returns null when cnj is absent or blank', () => {
    expect(readCnjParam('')).toBeNull();
    expect(readCnjParam('?other=1')).toBeNull();
    expect(readCnjParam('?cnj=')).toBeNull();
  });

  it('writes a masked ?cnj= for a valid CNJ, preserving other params', () => {
    const qs = buildCnjSearchParams('?foo=bar', '00000010220248220001');
    const params = new URLSearchParams(qs);
    expect(params.get('cnj')).toBe('0000001-02.2024.8.22.0001');
    expect(params.get('foo')).toBe('bar');
  });

  it('removes ?cnj= instead of writing an incoherent value for invalid digits', () => {
    const qs = buildCnjSearchParams('?cnj=0000001-02.2024.8.22.0001&foo=bar', '123');
    const params = new URLSearchParams(qs);
    expect(params.has('cnj')).toBe(false);
    expect(params.get('foo')).toBe('bar');
  });

  it('round-trips through readCnjParam once written', () => {
    const qs = buildCnjSearchParams('', '00000010220248220001');
    expect(readCnjParam(qs)).toBe('0000001-02.2024.8.22.0001');
  });
});

describe('SQL builders never use SELECT * and filter by parameter', () => {
  it('processos_unificados query lists explicit columns and filters nr_processo via placeholder', () => {
    const sql = buildProcessoUnificadoSql();
    expect(sql).not.toMatch(/select\s+\*/i);
    expect(sql).toContain('WHERE nr_processo = ?');
    expect(sql).toContain('nr_processo_mascara');
    expect(sql).toContain("read_parquet('https://archive.org/download/causaganha-dashboard/processos_unificados.parquet')");
  });

  it('processo_documentos query lists explicit columns, filters by parameter and paginates', () => {
    const sql = buildProcessoDocumentosSql();
    expect(sql).not.toMatch(/select\s+\*/i);
    expect(sql).toContain('WHERE nr_processo = ?');
    expect(sql).toContain('LIMIT ? OFFSET ?');
    expect(sql).toContain('ORDER BY data DESC NULLS LAST');
  });
});

describe('paginate', () => {
  it('reports hasMore=true and trims the extra row when pageSize+1 rows come back', () => {
    const rows = [1, 2, 3];
    const { items, hasMore } = paginate(rows, 2);
    expect(items).toEqual([1, 2]);
    expect(hasMore).toBe(true);
  });

  it('reports hasMore=false when exactly pageSize rows come back', () => {
    const rows = [1, 2];
    const { items, hasMore } = paginate(rows, 2);
    expect(items).toEqual([1, 2]);
    expect(hasMore).toBe(false);
  });

  it('reports hasMore=false for an empty page', () => {
    const { items, hasMore } = paginate([], 20);
    expect(items).toEqual([]);
    expect(hasMore).toBe(false);
  });
});

describe('toIsoDate', () => {
  it('normalizes a Date instance', () => {
    expect(toIsoDate(new Date(Date.UTC(2024, 2, 5)))).toBe('2024-03-05');
  });

  it('normalizes an ISO string', () => {
    expect(toIsoDate('2024-03-05T00:00:00Z')).toBe('2024-03-05');
  });

  it('returns null for null/undefined/invalid input', () => {
    expect(toIsoDate(null)).toBeNull();
    expect(toIsoDate(undefined)).toBeNull();
    expect(toIsoDate('not-a-date')).toBeNull();
  });
});

const CNJ_ALL = '00000010220248220001';

function baseRawProcesso(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    nr_processo: CNJ_ALL,
    nr_processo_mascara: '0000001-02.2024.8.22.0001',
    n_fontes: 4,
    fontes: ['djen', 'juris', 'stj', 'datajud'],
    djen_primeira_pub: '2024-03-01',
    djen_ultima_pub: '2024-03-05',
    djen_n_publicacoes: 2,
    djen_tribunais: ['TJRO'],
    juris_n_documentos: 2,
    juris_tipos: ['ACÓRDÃO', 'SENTENÇA'],
    juris_data_julgamento: '2024-02-28',
    juris_orgao: '2a Camara',
    juris_relator: 'Des. A',
    juris_classe: 'Apelação',
    juris_url: 'https://juris/1',
    stj_id: 'stj-1',
    stj_classe: 'REsp',
    stj_relator: 'MIN X',
    stj_tema: 'tema',
    stj_tese: 'tese',
    stj_ementa: 'ementa',
    stj_data_decisao: '2024-05-01',
    stj_data_publicacao: '2024-05-10',
    classe_oficial: 'Apelacao Civel',
    assuntos: 'Contratos',
    orgao_julgador: '2a Camara',
    grau: 'G2',
    data_ajuizamento: '2024-01-10',
    ultima_atualizacao: '2024-06-01',
    tem_datajud: true,
    updated_at: '2026-07-12T18:00:00Z',
    ...overrides,
  };
}

describe('mapProcessoRow — multi-fonte row', () => {
  it('marks every source present and surfaces every field with the right provenance', () => {
    const row = mapProcessoRow(baseRawProcesso());
    expect(row.nrProcesso).toBe(CNJ_ALL);
    expect(row.nrProcessoMascara).toBe('0000001-02.2024.8.22.0001');
    expect(row.nFontes).toBe(4);
    expect(row.fontes).toEqual(['djen', 'juris', 'stj', 'datajud']);

    expect(row.djen).toMatchObject({ present: true, nPublicacoes: 2, primeiraPub: '2024-03-01', ultimaPub: '2024-03-05' });
    expect(row.djen.tribunais).toEqual(['TJRO']);

    expect(row.juris).toMatchObject({ present: true, nDocumentos: 2, orgao: '2a Camara', relator: 'Des. A' });
    expect(row.juris.tipos).toEqual(['ACÓRDÃO', 'SENTENÇA']);

    expect(row.stj).toMatchObject({ present: true, id: 'stj-1', classe: 'REsp' });

    expect(row.datajud).toMatchObject({ present: true, classeOficial: 'Apelacao Civel', assuntos: 'Contratos' });
  });
});

describe('mapProcessoRow — DataJud absent (tem_datajud=false)', () => {
  it('marks datajud not present and nulls its fields even if fontes lists it (defensive)', () => {
    const row = mapProcessoRow(
      baseRawProcesso({
        fontes: ['djen', 'juris', 'stj'],
        tem_datajud: false,
        classe_oficial: null,
        assuntos: null,
        orgao_julgador: null,
        grau: null,
        data_ajuizamento: null,
        ultima_atualizacao: null,
      }),
    );
    expect(row.datajud.present).toBe(false);
    expect(row.datajud.classeOficial).toBeNull();
  });
});

describe('mapProcessoRow — single-source (DJEN only)', () => {
  it('marks juris/stj/datajud absent and leaves their fields null, without fabricating zeros', () => {
    const row = mapProcessoRow(
      baseRawProcesso({
        fontes: ['djen'],
        n_fontes: 1,
        juris_n_documentos: null,
        juris_tipos: null,
        juris_data_julgamento: null,
        juris_orgao: null,
        juris_relator: null,
        juris_classe: null,
        juris_url: null,
        stj_id: null,
        stj_classe: null,
        stj_relator: null,
        stj_tema: null,
        stj_tese: null,
        stj_ementa: null,
        stj_data_decisao: null,
        stj_data_publicacao: null,
        tem_datajud: false,
        classe_oficial: null,
        assuntos: null,
        orgao_julgador: null,
        grau: null,
        data_ajuizamento: null,
        ultima_atualizacao: null,
      }),
    );
    expect(row.djen.present).toBe(true);
    expect(row.juris.present).toBe(false);
    expect(row.juris.nDocumentos).toBeNull();
    expect(row.stj.present).toBe(false);
    expect(row.datajud.present).toBe(false);
  });
});

describe('mapDocumentoRow', () => {
  it('maps a JURIS document row', () => {
    const doc = mapDocumentoRow({
      nr_processo: CNJ_ALL,
      fonte: 'juris',
      id_documento: '1',
      tipo: 'ACÓRDÃO',
      data: '2024-01-15',
      url: 'https://juris/1',
      resumo: 'texto um',
    });
    expect(doc).toEqual({
      fonte: 'juris',
      idDocumento: '1',
      tipo: 'ACÓRDÃO',
      data: '2024-01-15',
      url: 'https://juris/1',
      resumo: 'texto um',
    });
  });

  it('maps an STJ document row with an empty url as null', () => {
    const doc = mapDocumentoRow({
      nr_processo: CNJ_ALL,
      fonte: 'stj',
      id_documento: 'stj-1',
      tipo: 'REsp',
      data: '2024-05-01',
      url: '',
      resumo: 'ementa',
    });
    expect(doc.url).toBeNull();
    expect(doc.fonte).toBe('stj');
  });
});

describe('completude', () => {
  it('reports all 4 sources present at 100%', () => {
    const c = completude(['djen', 'juris', 'stj', 'datajud']);
    expect(c.presentes).toEqual(ALL_FONTES);
    expect(c.ausentes).toEqual([]);
    expect(c.pct).toBe(100);
  });

  it('reports a single source at 25%, listing the other three as absent', () => {
    const c = completude(['djen']);
    expect(c.presentes).toEqual(['djen']);
    expect(c.ausentes).toEqual(['juris', 'stj', 'datajud']);
    expect(c.pct).toBe(25);
  });

  it('reports zero sources at 0%', () => {
    const c = completude([]);
    expect(c.pct).toBe(0);
    expect(c.ausentes).toEqual(ALL_FONTES);
  });
});

describe('isDocumentosVazio', () => {
  it('is true only on the first page with zero items (processo found, no documents)', () => {
    expect(isDocumentosVazio([], 0)).toBe(true);
  });

  it('is false when items exist', () => {
    expect(isDocumentosVazio([{ id: 1 }], 0)).toBe(false);
  });

  it('is false on a later page even if that page is empty (already proven non-empty overall)', () => {
    expect(isDocumentosVazio([], 20)).toBe(false);
  });
});
