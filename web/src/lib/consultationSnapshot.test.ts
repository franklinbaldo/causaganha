import { describe, expect, it } from 'vitest';
import {
  buildConsultationSnapshot,
  compareConsultationSnapshots,
  type ConsultationSnapshot,
} from './consultationSnapshot';
import { formatFonteIndisponivelAviso } from './processoCnj';
import type { ProcessoResultado } from './processoCnj';

const AUSENTE_DJEN = { present: false, primeiraPub: null, ultimaPub: null, nPublicacoes: null, tribunais: [] };
const AUSENTE_JURIS = {
  present: false,
  nDocumentos: null,
  tipos: [],
  dataJulgamento: null,
  orgao: null,
  relator: null,
  classe: null,
  url: null,
};
const AUSENTE_STJ = {
  present: false,
  id: null,
  classe: null,
  relator: null,
  tema: null,
  tese: null,
  ementa: null,
  dataDecisao: null,
  dataPublicacao: null,
};
const AUSENTE_DATAJUD = {
  present: false,
  classeOficial: null,
  assuntos: null,
  orgaoJulgador: null,
  grau: null,
  dataAjuizamento: null,
  ultimaAtualizacao: null,
};

function baseResultado(overrides: Partial<ProcessoResultado> = {}): ProcessoResultado {
  return {
    encontrado: true,
    nrProcesso: '00000010220248220001',
    nrProcessoMascara: '0000001-02.2024.8.22.0001',
    fontes: ['djen'],
    djen: { present: true, primeiraPub: '2026-01-01', ultimaPub: '2026-01-10', nPublicacoes: 3, tribunais: ['TJRO'] },
    juris: AUSENTE_JURIS,
    stj: AUSENTE_STJ,
    datajud: AUSENTE_DATAJUD,
    jurisUrls: [],
    stjUrls: [],
    cobertura: [],
    datasetGeradoEm: '2026-09-01T00:00:00Z',
    avisos: [],
    nucleoCompartilhado: {} as ProcessoResultado['nucleoCompartilhado'],
    ...overrides,
  };
}

describe('buildConsultationSnapshot', () => {
  it('captures comparable fields only for sources that actually loaded', () => {
    const snapshot = buildConsultationSnapshot(baseResultado(), '2026-09-01T12:00:00Z');
    expect(snapshot).toEqual<ConsultationSnapshot>({
      version: 1,
      capturedAt: '2026-09-01T12:00:00Z',
      encontrado: true,
      datasetGeradoEm: '2026-09-01T00:00:00Z',
      fontesPresentes: ['djen'],
      fontesIndisponiveis: [],
      djen: { nPublicacoes: 3, ultimaPub: '2026-01-10' },
      juris: null,
      stj: null,
      datajud: null,
    });
  });

  it('never treats a source flagged indisponível in avisos as comparable, even if present looks true', () => {
    const resultado = baseResultado({
      fontes: ['djen', 'stj'],
      stj: { ...AUSENTE_STJ, present: true, id: 'stale-cached-value' },
      avisos: [formatFonteIndisponivelAviso('stj', 'timeout')],
    });
    const snapshot = buildConsultationSnapshot(resultado, '2026-09-01T12:00:00Z');
    expect(snapshot.stj).toBeNull();
    expect(snapshot.fontesIndisponiveis).toEqual(['stj']);
    expect(snapshot.fontesPresentes).toEqual(['djen', 'stj']);
  });
});

describe('compareConsultationSnapshots', () => {
  const capturedAtPrev = '2026-09-01T12:00:00Z';
  const capturedAtNow = '2026-09-02T12:00:00Z';

  it('reports sem_historico when there is no previous snapshot', () => {
    const current = buildConsultationSnapshot(baseResultado(), capturedAtNow);
    const comparison = compareConsultationSnapshots(null, current);
    expect(comparison.status).toBe('sem_historico');
    expect(comparison.changedFields).toEqual([]);
  });

  it('reports sem_mudanca when the comparable fields are identical', () => {
    const previous = buildConsultationSnapshot(baseResultado(), capturedAtPrev);
    const current = buildConsultationSnapshot(baseResultado(), capturedAtNow);
    const comparison = compareConsultationSnapshots(previous, current);
    expect(comparison.status).toBe('sem_mudanca');
    expect(comparison.changedFields).toEqual([]);
  });

  it('reports mudou when a comparable field actually changed', () => {
    const previous = buildConsultationSnapshot(baseResultado(), capturedAtPrev);
    const current = buildConsultationSnapshot(
      baseResultado({
        djen: { present: true, primeiraPub: '2026-01-01', ultimaPub: '2026-02-15', nPublicacoes: 5, tribunais: ['TJRO'] },
      }),
      capturedAtNow,
    );
    const comparison = compareConsultationSnapshots(previous, current);
    expect(comparison.status).toBe('mudou');
    expect(comparison.changedFields).toEqual(expect.arrayContaining(['djen.nPublicacoes', 'djen.ultimaPub']));
  });

  it('reports mudou when a new fonte appears in the índice, even with no other field changes', () => {
    const previous = buildConsultationSnapshot(baseResultado(), capturedAtPrev);
    const current = buildConsultationSnapshot(
      baseResultado({
        fontes: ['djen', 'datajud'],
        datajud: { ...AUSENTE_DATAJUD, present: true, grau: 'G1', ultimaAtualizacao: '2026-02-01T00:00:00Z' },
      }),
      capturedAtNow,
    );
    const comparison = compareConsultationSnapshots(previous, current);
    expect(comparison.status).toBe('mudou');
    expect(comparison.changedFields).toContain('fontesPresentes');
  });

  it('never infers change from a source that is merely unavailable right now (indisponibilidade != remoção)', () => {
    const previous = buildConsultationSnapshot(
      baseResultado({
        fontes: ['djen', 'stj'],
        stj: { ...AUSENTE_STJ, present: true, id: 'stj-1', dataDecisao: '2026-01-05' },
      }),
      capturedAtPrev,
    );
    const current = buildConsultationSnapshot(
      baseResultado({
        fontes: ['djen', 'stj'],
        stj: { ...AUSENTE_STJ, present: true, id: 'stj-1', dataDecisao: '2026-01-05' },
        avisos: [formatFonteIndisponivelAviso('stj', 'network error')],
      }),
      capturedAtNow,
    );
    const comparison = compareConsultationSnapshots(previous, current);
    expect(comparison.status).not.toBe('mudou');
    expect(comparison.changedFields).not.toContain('stj.id');
    expect(comparison.changedFields).not.toContain('stj.dataDecisao');
    expect(comparison.unstableFontes).toEqual(['stj']);
  });

  it('reports nao_comparavel when every source that had a previous baseline is unavailable now and nothing new appeared', () => {
    const previous = buildConsultationSnapshot(
      baseResultado({
        fontes: ['stj'],
        djen: AUSENTE_DJEN,
        stj: { ...AUSENTE_STJ, present: true, id: 'stj-1', dataDecisao: '2026-01-05' },
      }),
      capturedAtPrev,
    );
    const current = buildConsultationSnapshot(
      baseResultado({
        fontes: ['stj'],
        djen: AUSENTE_DJEN,
        stj: { ...AUSENTE_STJ, present: true, id: 'stj-1', dataDecisao: '2026-01-05' },
        avisos: [formatFonteIndisponivelAviso('stj', 'network error')],
      }),
      capturedAtNow,
    );
    const comparison = compareConsultationSnapshots(previous, current);
    expect(comparison.status).toBe('nao_comparavel');
    expect(comparison.changedFields).toEqual([]);
  });
});
