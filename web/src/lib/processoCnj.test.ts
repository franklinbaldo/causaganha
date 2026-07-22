import { describe, expect, it, vi } from 'vitest';
import {
  ALL_FONTES,
  buildCnjSearchParams,
  buildDatajudSql,
  buildDjenSql,
  buildDocumentosSql,
  buildHeroSearchRedirect,
  buildIndiceSql,
  buildJurisSql,
  buildStjSql,
  buscarProcesso,
  carregarDocumentos,
  classifyCnjInput,
  fetchCobertura,
  fontesPresenca,
  fonteUrls,
  formatCnj,
  isDocumentosVazio,
  isValidCnj,
  mapDatajudRow,
  mapDjenRow,
  mapDocumentoRow,
  mapJurisRow,
  mapStjRow,
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

describe('buildHeroSearchRedirect', () => {
  it('redirects an unmasked 20-digit CNJ to /processo with a masked ?cnj=', () => {
    expect(buildHeroSearchRedirect('00000010220248220001', '/processo')).toBe(
      '/processo?cnj=0000001-02.2024.8.22.0001',
    );
  });

  it('redirects a masked CNJ to /processo with the same masked ?cnj=', () => {
    expect(buildHeroSearchRedirect('0000001-02.2024.8.22.0001', '/processo')).toBe(
      '/processo?cnj=0000001-02.2024.8.22.0001',
    );
  });

  it('returns null for free text, leaving the caller to submit to /publicacoes', () => {
    expect(buildHeroSearchRedirect('mandado de segurança', '/processo')).toBeNull();
  });

  it('returns null for OAB-shaped input', () => {
    expect(buildHeroSearchRedirect('OAB/SP 245.812', '/processo')).toBeNull();
  });

  it('returns null for malformed CNJ-like text (wrong digit count)', () => {
    expect(buildHeroSearchRedirect('0000001-02.2024.8.22', '/processo')).toBeNull();
  });

  it('returns null for empty input', () => {
    expect(buildHeroSearchRedirect('', '/processo')).toBeNull();
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
  it('indice query filters numero_processo via placeholder and reads indice_processual.parquet', () => {
    const sql = buildIndiceSql();
    expect(sql).not.toMatch(/select\s+\*/i);
    expect(sql).toContain('WHERE numero_processo = ?');
    expect(sql).toContain(
      "read_parquet('https://archive.org/download/causaganha-dashboard/indice_processual.parquet')",
    );
  });

  it('djen query unions the discovered URLs and filters by placeholder', () => {
    const sql = buildDjenSql(['https://a/comunicacoes.parquet', "https://b/comunicacoes.parquet"]);
    expect(sql).not.toMatch(/select\s+\*/i);
    expect(sql).toContain("read_parquet(['https://a/comunicacoes.parquet', 'https://b/comunicacoes.parquet']");
    expect(sql).toContain('= ?');
  });

  it('juris query cross-joins agg and principal over the discovered URLs', () => {
    const sql = buildJurisSql(['https://a/tjro-juris-2024.parquet']);
    expect(sql).toContain('FROM agg, principal');
    expect(sql).toContain("read_parquet(['https://a/tjro-juris-2024.parquet']");
  });

  it('stj query filters by placeholder over the discovered URLs', () => {
    const sql = buildStjSql(['https://a/stj-acordaos.parquet']);
    expect(sql).toContain('regexp_replace("numeroProcesso"');
  });

  it('datajud query filters by placeholder over the discovered URLs', () => {
    const sql = buildDatajudSql(['https://a/datajud-capa-tjro.parquet']);
    expect(sql).toContain('WHERE numero_processo = ?');
  });

  it('documentos query unions only the branches with URLs present, and paginates', () => {
    const { sql, nParams } = buildDocumentosSql(['https://a/juris.parquet'], []);
    expect(sql).not.toMatch(/union all.*union all/is);
    expect(sql).toContain('LIMIT ? OFFSET ?');
    expect(nParams).toBe(1);

    const both = buildDocumentosSql(['https://a/juris.parquet'], ['https://a/stj.parquet']);
    expect(both.sql).toMatch(/union all/i);
    expect(both.nParams).toBe(2);

    const none = buildDocumentosSql([], []);
    expect(none.nParams).toBe(0);
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

describe('mapDjenRow', () => {
  it('marks present with n_publicacoes > 0', () => {
    const view = mapDjenRow({
      n_publicacoes: 2,
      primeira_publicacao: '2024-03-01',
      ultima_publicacao: '2024-03-05',
      tribunais: ['TJRO'],
    });
    expect(view).toMatchObject({ present: true, nPublicacoes: 2, primeiraPub: '2024-03-01', ultimaPub: '2024-03-05' });
    expect(view.tribunais).toEqual(['TJRO']);
  });

  it('marks absent for a null row or n_publicacoes=0, without fabricating zeros', () => {
    expect(mapDjenRow(null)).toMatchObject({ present: false, nPublicacoes: null });
    expect(mapDjenRow({ n_publicacoes: 0, tribunais: [] })).toMatchObject({ present: false });
  });
});

describe('mapJurisRow', () => {
  it('marks present when a row comes back', () => {
    const view = mapJurisRow({
      n_documentos: 2,
      tipos: ['ACÓRDÃO', 'SENTENÇA'],
      data_julgamento: '2024-02-28',
      orgao: '2a Camara',
      relator: 'Des. A',
      classe: 'Apelação',
      url: 'https://juris/1',
    });
    expect(view).toMatchObject({ present: true, nDocumentos: 2, orgao: '2a Camara', relator: 'Des. A' });
    expect(view.tipos).toEqual(['ACÓRDÃO', 'SENTENÇA']);
  });

  it('marks absent for a null row (no cross-join match)', () => {
    expect(mapJurisRow(null)).toMatchObject({ present: false, nDocumentos: null });
  });
});

describe('mapStjRow', () => {
  it('marks present with n > 0', () => {
    const view = mapStjRow({
      n: 1,
      id: 'stj-1',
      classe: 'REsp',
      relator: 'MIN X',
      tema: 'tema',
      tese: 'tese',
      ementa: 'ementa',
      data_decisao: '2024-05-01',
      data_publicacao: '2024-05-10',
    });
    expect(view).toMatchObject({ present: true, id: 'stj-1', classe: 'REsp' });
  });

  it('marks absent for a null row or n=0', () => {
    expect(mapStjRow(null)).toMatchObject({ present: false, id: null });
    expect(mapStjRow({ n: 0 })).toMatchObject({ present: false });
  });
});

describe('mapDatajudRow', () => {
  it('marks present with n > 0', () => {
    const view = mapDatajudRow({
      n: 1,
      classe_oficial: 'Apelacao Civel',
      assuntos: 'Contratos',
      orgao_julgador: '2a Camara',
      grau: 'G2',
      data_ajuizamento: '2024-01-10',
      ultima_atualizacao: '2024-06-01',
    });
    expect(view).toMatchObject({ present: true, classeOficial: 'Apelacao Civel', assuntos: 'Contratos' });
  });

  it('marks absent for a null row or n=0', () => {
    expect(mapDatajudRow(null)).toMatchObject({ present: false, classeOficial: null });
    expect(mapDatajudRow({ n: 0 })).toMatchObject({ present: false });
  });
});

describe('mapDocumentoRow', () => {
  it('maps a JURIS document row', () => {
    const doc = mapDocumentoRow({
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

describe('fontesPresenca', () => {
  it('groups all 4 sources as present, none absent', () => {
    const c = fontesPresenca(['djen', 'juris', 'stj', 'datajud']);
    expect(c.presentes).toEqual(ALL_FONTES);
    expect(c.ausentes).toEqual([]);
  });

  it('groups a single present source, listing the other three as without a record — no percentage', () => {
    const c = fontesPresenca(['djen']);
    expect(c.presentes).toEqual(['djen']);
    expect(c.ausentes).toEqual(['juris', 'stj', 'datajud']);
    expect(c).not.toHaveProperty('pct');
  });

  it('groups zero present sources, all four without a record', () => {
    const c = fontesPresenca([]);
    expect(c.presentes).toEqual([]);
    expect(c.ausentes).toEqual(ALL_FONTES);
  });
});

describe('fonteUrls', () => {
  it('dedupes and sorts URLs for the requested fonte', () => {
    const rows = [
      { fonte: 'djen', url: 'https://b' },
      { fonte: 'djen', url: 'https://a' },
      { fonte: 'djen', url: 'https://a' },
      { fonte: 'juris', url: 'https://c' },
    ];
    expect(fonteUrls(rows, 'djen')).toEqual(['https://a', 'https://b']);
    expect(fonteUrls(rows, 'stj')).toEqual([]);
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

describe('fetchCobertura', () => {
  it('returns cobertura + datasetGeradoEm on a healthy report', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        generated_at: '2026-07-12T18:00:00Z',
        sources: { djen: { status: 'loaded_remote', rows: 10 }, stj: { status: 'unavailable', rows: 0 } },
      }),
    });
    vi.stubGlobal('fetch', fetchMock);
    try {
      const result = await fetchCobertura('https://example/report.json');
      expect(result?.datasetGeradoEm).toBe('2026-07-12T18:00:00Z');
      expect(result?.cobertura).toEqual([
        { fonte: 'djen', status: 'loaded_remote', registros: 10 },
        { fonte: 'stj', status: 'unavailable', registros: 0 },
      ]);
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it('returns null on a non-ok response, without throwing', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false }));
    try {
      expect(await fetchCobertura('https://example/report.json')).toBeNull();
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it('returns null when fetch itself rejects, without throwing', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network down')));
    try {
      expect(await fetchCobertura('https://example/report.json')).toBeNull();
    } finally {
      vi.unstubAllGlobals();
    }
  });
});

const CNJ_ALL = '00000010220248220001';

/** Fake DuckDB-WASM connection: routes each prepare()d SQL to a canned row set by matching a SQL substring. */
function fakeConn(bySqlSubstring: Array<[string, Record<string, unknown>[]]>) {
  const calls: Array<{ sql: string; params: unknown[] }> = [];
  return {
    calls,
    prepare: async (sql: string) => ({
      query: async (...params: unknown[]) => {
        calls.push({ sql, params });
        const match = bySqlSubstring.find(([needle]) => sql.includes(needle));
        const rows = match ? match[1] : [];
        return { toArray: () => rows.map((row) => ({ toJSON: () => row })) };
      },
      close: async () => {},
    }),
  };
}

describe('buscarProcesso', () => {
  it('returns encontrado=false when the index has no rows for the CNJ, still surfacing cobertura', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => ({ generated_at: 'X', sources: {} }) }),
    );
    try {
      const conn = fakeConn([]);
      const result = await buscarProcesso(conn as any, CNJ_ALL);
      expect(result.encontrado).toBe(false);
      expect(result.nrProcessoMascara).toBe('0000001-02.2024.8.22.0001');
      expect(result.datasetGeradoEm).toBe('X');
      expect(result.avisos).toEqual([]);
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it('assembles the dossie from per-fonte queries when the index has rows, and warns when the report is unavailable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false }));
    try {
      const conn = fakeConn([
        [
          'FROM read_parquet(\'https://archive.org/download/causaganha-dashboard/indice_processual.parquet\')',
          [
            { fonte: 'djen', arquivo_ia_url: 'https://ia/djen-2024.parquet' },
            { fonte: 'datajud', arquivo_ia_url: 'https://ia/datajud-capa-tjro.parquet' },
          ],
        ],
        ['COUNT(*)::INTEGER AS n_publicacoes', [{ n_publicacoes: 1, primeira_publicacao: '2024-01-01', ultima_publicacao: '2024-01-01', tribunais: ['TJRO'] }]],
        ['FROM agg, principal', []],
        [
          'FROM read_parquet([\'https://ia/datajud-capa-tjro.parquet\'])',
          [{ n: 1, classe_oficial: 'Apelacao', assuntos: 'X', orgao_julgador: 'Y', grau: 'G1', data_ajuizamento: '2024-01-01', ultima_atualizacao: '2024-02-01' }],
        ],
      ]);
      const result = await buscarProcesso(conn as any, CNJ_ALL);
      expect(result.encontrado).toBe(true);
      expect(result.fontes).toEqual(['datajud', 'djen']);
      expect(result.djen.present).toBe(true);
      expect(result.juris.present).toBe(false);
      expect(result.stj.present).toBe(false);
      expect(result.datajud).toMatchObject({ present: true, classeOficial: 'Apelacao' });
      expect(result.jurisUrls).toEqual([]);
      expect(result.avisos).toEqual([
        'Relatório de cobertura (indice_processual.report.json) indisponível; sem detalhamento de ' +
          'quais fontes estavam carregadas na geração do dataset.',
      ]);
    } finally {
      vi.unstubAllGlobals();
    }
  });
});

/** Like fakeConn, but any query whose SQL contains `failSubstring` throws instead of resolving. */
function fakeConnWithFailure(
  failSubstring: string,
  bySqlSubstring: Array<[string, Record<string, unknown>[]]>,
) {
  const calls: Array<{ sql: string; params: unknown[] }> = [];
  return {
    calls,
    prepare: async (sql: string) => ({
      query: async (...params: unknown[]) => {
        calls.push({ sql, params });
        if (sql.includes(failSubstring)) {
          throw new Error('IO Error: could not open causaganha-dashboard/indice_processual.parquet');
        }
        const match = bySqlSubstring.find(([needle]) => sql.includes(needle));
        const rows = match ? match[1] : [];
        return { toArray: () => rows.map((row) => ({ toJSON: () => row })) };
      },
      close: async () => {},
    }),
  };
}

describe('buscarProcesso — rollout fallback (indice_processual.parquet unreachable)', () => {
  const INDICE_SUBSTRING = "FROM read_parquet('https://archive.org/download/causaganha-dashboard/indice_processual.parquet')";
  const LEGADO_UNIFICADO_SUBSTRING =
    "FROM read_parquet('https://archive.org/download/causaganha-dashboard/processos_unificados.parquet')";

  it('falls back to processos_unificados.parquet and marks the result legado', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false }));
    try {
      const conn = fakeConnWithFailure(INDICE_SUBSTRING, [
        [
          LEGADO_UNIFICADO_SUBSTRING,
          [
            {
              nr_processo: CNJ_ALL,
              nr_processo_mascara: '0000001-02.2024.8.22.0001',
              n_fontes: 2,
              fontes: ['djen', 'juris'],
              djen_primeira_pub: '2024-03-01',
              djen_ultima_pub: '2024-03-05',
              djen_n_publicacoes: 2,
              djen_tribunais: ['TJRO'],
              juris_n_documentos: 1,
              juris_tipos: ['ACÓRDÃO'],
              juris_data_julgamento: '2024-02-28',
              juris_orgao: '2a Camara',
              juris_relator: 'Des. A',
              juris_classe: 'Apelação',
              juris_url: 'https://juris/1',
              tem_datajud: false,
              updated_at: '2026-01-01T00:00:00Z',
            },
          ],
        ],
      ]);
      const result = await buscarProcesso(conn as any, CNJ_ALL);

      expect(result.legado).toBe(true);
      expect(result.encontrado).toBe(true);
      expect(result.nrProcesso).toBe(CNJ_ALL);
      expect(result.fontes).toEqual(['djen', 'juris']);
      expect(result.djen).toMatchObject({ present: true, nPublicacoes: 2 });
      expect(result.juris).toMatchObject({ present: true, orgao: '2a Camara' });
      expect(result.jurisUrls).toEqual([]);
      expect(result.stjUrls).toEqual([]);
      expect(result.cobertura).toEqual([]);
      expect(result.datasetGeradoEm).toBe('2026-01-01T00:00:00.000Z');
      expect(result.avisos.some((a) => a.includes('indice_processual.parquet'))).toBe(true);
      expect(result.avisos.some((a) => a.includes('processos_unificados.parquet'))).toBe(true);
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it('falls back and reports not found when the legacy parquet has no row either', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false }));
    try {
      const conn = fakeConnWithFailure(INDICE_SUBSTRING, []);
      const result = await buscarProcesso(conn as any, CNJ_ALL);

      expect(result.legado).toBe(true);
      expect(result.encontrado).toBe(false);
      expect(result.fontes).toEqual([]);
    } finally {
      vi.unstubAllGlobals();
    }
  });
});

describe('carregarDocumentos', () => {
  it('skips the query entirely when neither juris nor stj has a URL', async () => {
    const conn = fakeConn([]);
    const result = await carregarDocumentos(conn as any, [], [], CNJ_ALL, 0, 20);
    expect(result).toEqual({ items: [], hasMore: false });
    expect(conn.calls).toHaveLength(0);
  });

  it('queries and paginates over the discovered URLs', async () => {
    const conn = fakeConn([
      [
        "'juris' AS fonte",
        [
          { fonte: 'juris', id_documento: '1', tipo: 'ACÓRDÃO', data: '2024-01-15', url: 'https://juris/1', resumo: 'r1' },
        ],
      ],
    ]);
    const result = await carregarDocumentos(conn as any, ['https://ia/juris.parquet'], [], CNJ_ALL, 0, 20);
    expect(result.items).toEqual([
      { fonte: 'juris', idDocumento: '1', tipo: 'ACÓRDÃO', data: '2024-01-15', url: 'https://juris/1', resumo: 'r1' },
    ]);
    expect(result.hasMore).toBe(false);
    expect(conn.calls[0].params).toEqual([CNJ_ALL, 21, 0]);
  });

  it('queries processo_documentos.parquet directly when legado=true, ignoring jurisUrls/stjUrls', async () => {
    const conn = fakeConn([
      [
        "FROM read_parquet('https://archive.org/download/causaganha-dashboard/processo_documentos.parquet')",
        [
          { fonte: 'juris', id_documento: '1', tipo: 'ACÓRDÃO', data: '2024-01-15', url: 'https://juris/1', resumo: 'r1' },
        ],
      ],
    ]);
    const result = await carregarDocumentos(conn as any, [], [], CNJ_ALL, 0, 20, true);
    expect(result.items).toEqual([
      { fonte: 'juris', idDocumento: '1', tipo: 'ACÓRDÃO', data: '2024-01-15', url: 'https://juris/1', resumo: 'r1' },
    ]);
    expect(conn.calls[0].params).toEqual([CNJ_ALL, 21, 0]);
  });
});
