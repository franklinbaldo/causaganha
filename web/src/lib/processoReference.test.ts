import { describe, expect, it } from 'vitest';
import { buildDocumentoReferenceText, buildProcessoReferenceText } from './processoReference';

const CAUSAGANHA_URL = 'https://causaganha.example/causaganha/processo?numeroProcesso=00000010220248220001';
const ORIGEM_URL = 'https://archive.org/download/causaganha-dashboard/indice_processual.parquet';

describe('buildProcessoReferenceText', () => {
  it('composes source, identification, origin, freshness and the CausaGanha URL as secondary context', () => {
    const text = buildProcessoReferenceText({
      nrProcessoMascara: '0000001-02.2024.8.22.0001',
      fontesPresentes: ['DJEN', 'DataJud'],
      datasetGeradoEm: '2026-08-20T10:00:00Z',
      origemUrl: ORIGEM_URL,
      causaganhaUrl: CAUSAGANHA_URL,
    });

    expect(text).toContain('0000001-02.2024.8.22.0001');
    expect(text).toContain('DJEN, DataJud');
    expect(text).toContain('2026-08-20T10:00:00Z');
    expect(text).toContain(ORIGEM_URL);
    expect(text).toContain(CAUSAGANHA_URL);
    // The preserved/authoritative origin must stay distinguishable from the
    // CausaGanha page URL — never merge them into one generic "link" line.
    expect(text.indexOf(ORIGEM_URL)).toBeLessThan(text.indexOf(CAUSAGANHA_URL));
  });

  it('never fabricates a freshness placeholder when the dataset timestamp is unknown', () => {
    const text = buildProcessoReferenceText({
      nrProcessoMascara: '0000001-02.2024.8.22.0001',
      fontesPresentes: ['DJEN'],
      datasetGeradoEm: null,
      origemUrl: ORIGEM_URL,
      causaganhaUrl: CAUSAGANHA_URL,
    });

    expect(text).not.toMatch(/desconhecido|unknown|n\/a/i);
    expect(text).not.toContain('Dataset gerado em');
  });

  it('says explicitly when no source has a record, instead of an empty list', () => {
    const text = buildProcessoReferenceText({
      nrProcessoMascara: '0000001-02.2024.8.22.0001',
      fontesPresentes: [],
      datasetGeradoEm: null,
      origemUrl: ORIGEM_URL,
      causaganhaUrl: CAUSAGANHA_URL,
    });

    expect(text).toContain('nenhuma fonte');
  });

  it('is a stable, plain-text, human-and-machine-readable block (no markdown/HTML)', () => {
    const text = buildProcessoReferenceText({
      nrProcessoMascara: '0000001-02.2024.8.22.0001',
      fontesPresentes: ['DJEN'],
      datasetGeradoEm: '2026-08-20T10:00:00Z',
      origemUrl: ORIGEM_URL,
      causaganhaUrl: CAUSAGANHA_URL,
    });

    // Underscores are legitimate inside URLs/identifiers (e.g. indice_processual);
    // only markdown emphasis/heading/HTML markers are disallowed here.
    expect(text).not.toMatch(/\*\*|##|<[a-z]/i);
  });
});

describe('buildDocumentoReferenceText', () => {
  it('composes a document-level reference around its own public origin URL', () => {
    const text = buildDocumentoReferenceText({
      fonteLabel: 'JURIS (TJRO)',
      nrProcessoMascara: '0000001-02.2024.8.22.0001',
      tipo: 'Acórdão',
      data: '2024-01-01',
      url: 'https://tjro.jus.br/juris/acordao/123',
      causaganhaUrl: CAUSAGANHA_URL,
    });

    expect(text).toContain('Acórdão');
    expect(text).toContain('JURIS (TJRO)');
    expect(text).toContain('0000001-02.2024.8.22.0001');
    expect(text).toContain('2024-01-01');
    expect(text).toContain('https://tjro.jus.br/juris/acordao/123');
    expect(text).toContain(CAUSAGANHA_URL);
    expect(text.indexOf('https://tjro.jus.br/juris/acordao/123')).toBeLessThan(text.indexOf(CAUSAGANHA_URL));
  });

  it('never fabricates a date when the document has none', () => {
    const text = buildDocumentoReferenceText({
      fonteLabel: 'STJ',
      nrProcessoMascara: '0000001-02.2024.8.22.0001',
      tipo: null,
      data: null,
      url: 'https://stj.jus.br/processo/456',
      causaganhaUrl: CAUSAGANHA_URL,
    });

    expect(text).not.toMatch(/desconhecid[ao]|unknown|n\/a/i);
    expect(text).not.toMatch(/Data:/);
    // No document type on record — must not invent one, only use a neutral noun.
    expect(text).toContain('documento');
  });
});
