import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import type { SiteStatus } from './contracts';
import { buildSourceCoverage } from './sourceCoverage';

const siteStatus: SiteStatus = {
  generated_at: '2026-09-06T02:00:00Z',
  sources: {
    djen: {
      zips_archived: 1200,
      pairs_total: 1500,
      tribunals_with_data: 80,
      tribunals_total: 90,
      coverage_pct: 80,
      earliest_tracked_date: '2026-01-01',
      earliest_upload_date: '2026-01-02',
      latest_upload_date: '2026-09-05',
      absent_confirmed: 100,
      pending_real: 10,
      pending_real_max_age_hours: 4,
      errors_transient: 20,
      never_checked: 170,
      last_attempt_at: '2026-09-06T01:30:00Z',
      last_success_at: '2026-09-06T01:00:00Z',
    },
  },
};

describe('buildSourceCoverage', () => {
  it('deriva cobertura e frescor dos contratos públicos', () => {
    const sources = buildSourceCoverage({
      siteStatus,
      datajud: {
        total_processos: 500,
        total_registros: 800,
        total_tribunais: 12,
        ultima_atualizacao: '2026-09-05',
      },
      juris: {
        total_documentos: 200,
        total_tipos: 8,
        total_orgaos: 15,
        data_mais_recente: '2026-09-04',
      },
      stj: { total: 90, total_temas: 20, ultima_decisao: '2026-09-03' },
      now: Date.parse('2026-09-06T02:00:00Z'),
    });

    expect(sources.map((source) => source.id)).toEqual(['djen', 'datajud', 'tjro_juris', 'stj']);
    expect(sources[0].coverage).toContain('cadernos preservados');
    expect(sources[0].coverage).toContain('80% de cobertura');
    expect(sources[0].freshness).toBe('Atualizado');
    expect(sources[1].coverage).toContain('500 processos');
    expect(sources[2].coverage).toContain('200 documentos');
    expect(sources[3].coverage).toContain('90 registros');
  });

  it('expõe contrato ausente como não publicado, não como contagem zero', () => {
    const sources = buildSourceCoverage({
      siteStatus,
      datajud: null,
      juris: null,
      stj: null,
      now: Date.parse('2026-09-06T02:00:00Z'),
    });

    for (const source of sources.slice(1)) {
      expect(source.coverage).toBe('Cobertura não publicada neste build.');
      expect(source.coverage).not.toMatch(/\b0\b/);
      expect(source.freshness).toBe('Atualização não publicada.');
    }
  });

  it('/sobre consome a projeção compartilhada em vez de manter catálogo próprio', () => {
    const page = readFileSync(new URL('../../pages/sobre.astro', import.meta.url), 'utf8');
    expect(page).toContain('buildSourceCoverage');
    expect(page).not.toMatch(/const\s+sources\s*=\s*\[/);
    expect(page).not.toContain("['Arquivo', 'DJEN'");
  });
});
