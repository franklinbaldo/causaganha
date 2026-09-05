import { render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import ProcessoEvidenceMatrix from './ProcessoEvidenceMatrix.svelte';
import { evidenceMatrixRows } from '../lib/processoCnj';

describe('ProcessoEvidenceMatrix (#1130 evidence-summary strip)', () => {
  it('renders one row per source with a visible textual status label, not color-only', () => {
    const rows = evidenceMatrixRows(['djen'], [], []);
    const component = render(ProcessoEvidenceMatrix, { props: { rows } });

    expect(component.getByText('DJEN')).toBeTruthy();
    expect(component.getByText('Presente')).toBeTruthy();
    expect(component.getByText('JURIS (TJRO)')).toBeTruthy();
    expect(component.getAllByText('Sem registro').length).toBeGreaterThan(0);
  });

  it('distinguishes indisponível from ausente with its own visible label', () => {
    const rows = evidenceMatrixRows([], ["Fonte 'stj' indisponível para este processo: 404"], []);
    const component = render(ProcessoEvidenceMatrix, { props: { rows } });

    expect(component.getByText('Indisponível')).toBeTruthy();
  });

  it('shows the product papel (Arquivo/Estado/Teor) alongside each source', () => {
    const rows = evidenceMatrixRows([], [], []);
    const component = render(ProcessoEvidenceMatrix, { props: { rows } });

    expect(component.getByText('Arquivo')).toBeTruthy();
    expect(component.getByText('Estado')).toBeTruthy();
    expect(component.getAllByText('Teor').length).toBe(2);
  });

  it('links each row to its source detail section in the dossier', () => {
    const rows = evidenceMatrixRows(['djen'], [], []);
    const component = render(ProcessoEvidenceMatrix, { props: { rows } });

    const djenLink = component.getByText('DJEN').closest('a');
    expect(djenLink?.getAttribute('href')).toBe('#djen-title');
    const datajudLink = component.getByText('DataJud').closest('a');
    expect(datajudLink?.getAttribute('href')).toBe('#datajud-title');
    const jurisLink = component.getByText('JURIS (TJRO)').closest('a');
    expect(jurisLink?.getAttribute('href')).toBe('#documentos-title');
    const stjLink = component.getByText('STJ').closest('a');
    expect(stjLink?.getAttribute('href')).toBe('#documentos-title');
  });
});
