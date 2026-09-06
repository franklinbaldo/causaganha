import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

const component = (name: string) =>
  readFileSync(join(process.cwd(), 'src/components', name), 'utf8');

const processo = component('ProcessoLookup.svelte');
const publicacoes = component('PublicationSearch.svelte');
const savedConsultations = component('SavedConsultations.svelte');
const styles = readFileSync(
  join(process.cwd(), 'src/styles/query-states.css'),
  'utf8',
);
const indexCss = readFileSync(join(process.cwd(), 'src/index.css'), 'utf8');

describe('shared query-state contract (#1136)', () => {
  it('keeps valid empty results distinct from unavailable sources in ProcessoLookup', () => {
    expect(processo).toContain("status === 'not_found'");
    expect(processo).toContain("status === 'source_unavailable'");
    expect(processo).toContain('não que o processo não existe');
    expect(processo).toContain('O erro não significa ausência do processo');
  });

  it('keeps empty DJEN results distinct from source failures', () => {
    expect(publicacoes).toContain("status === 'empty'");
    expect(publicacoes).toContain("status === 'error'");
    expect(publicacoes).toContain('Nenhum resultado nesta consulta');
    expect(publicacoes).toContain('falha de origem, não ausência de resultados');
  });

  it('loads one shared presentation layer for both primary query surfaces', () => {
    expect(indexCss).toContain("@import './styles/query-states.css';");
    expect(styles).toContain('.processo-lookup, .publication-search');
    expect(styles).toContain('.empty-state, .empty-search');
    expect(styles).toContain("[role='alert']");
    expect(styles).toContain("[aria-busy='true']");
  });

  it('does not collapse failures into the empty-state selector', () => {
    const emptyRule = styles.slice(
      styles.indexOf(':where(.processo-lookup, .publication-search) :where(.empty-state, .empty-search)'),
      styles.indexOf('/* A source failure'),
    );
    expect(emptyRule).not.toContain("[role='alert']");
  });

  it('marks SavedConsultations with the same semantic query-state vocabulary (#1136)', () => {
    expect(savedConsultations).toContain('class="empty-state"');
    expect(savedConsultations).toContain('role="alert"');
    expect(savedConsultations).toContain('aria-busy="true"');
  });

  it('extends the shared layout-stability contract to /minhas-consultas', () => {
    expect(styles).toContain(
      '.processo-lookup, .publication-search, .saved-consultations',
    );
  });

  it('still never collapses failures into the empty-state selector once extended', () => {
    const emptyRule = styles.slice(
      styles.indexOf(
        ':where(.processo-lookup, .publication-search, .saved-consultations) :where(.empty-state, .empty-search)',
      ),
      styles.indexOf('/* A source failure'),
    );
    expect(emptyRule).not.toContain("[role='alert']");
  });
});
