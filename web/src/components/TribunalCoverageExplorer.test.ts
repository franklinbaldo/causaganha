import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it } from 'vitest';
import TribunalCoverageExplorer from './TribunalCoverageExplorer.svelte';
import type { TribunalCalendarRow } from '../lib/tribunalCoverageDrilldown';

const ROWS: TribunalCalendarRow[] = [
  { tribunal: 'TJRO', date: '2026-01-01', status: 'uploaded' },
  { tribunal: 'TJRO', date: '2026-01-02', status: 'uploaded' },
  { tribunal: 'TJRO', date: '2026-01-03', status: 'absent' },
  { tribunal: 'TJSP', date: '2026-06-01', status: 'absent' },
];

const TRIBUNALS = ['TJRO', 'TJSP'];

beforeEach(() => {
  window.history.replaceState(null, '', '/stats');
});

describe('TribunalCoverageExplorer', () => {
  it('shows the uploaded/absent breakdown for the default tribunal and period', async () => {
    render(TribunalCoverageExplorer, {
      calendarRows: ROWS,
      tribunals: TRIBUNALS,
      publicBase: '/',
      initialTribunal: 'TJRO',
      initialStart: '2026-01-01',
      initialEnd: '2026-01-03',
    });

    await waitFor(() => {
      expect(screen.getByText(/2 dias preservados/i)).toBeInTheDocument();
      expect(screen.getByText(/1 dia com ausência confirmada/i)).toBeInTheDocument();
    });
  });

  it('shows a not-enough-evidence message instead of 0% when the period has no observed day', async () => {
    render(TribunalCoverageExplorer, {
      calendarRows: ROWS,
      tribunals: TRIBUNALS,
      publicBase: '/',
      initialTribunal: 'TJSP',
      initialStart: '2026-01-01',
      initialEnd: '2026-01-02',
    });

    await waitFor(() => {
      expect(screen.getByText(/sem evidência suficiente neste período/i)).toBeInTheDocument();
    });
  });

  it('recomputes the summary when the tribunal selection changes', async () => {
    render(TribunalCoverageExplorer, {
      calendarRows: ROWS,
      tribunals: TRIBUNALS,
      publicBase: '/',
      initialTribunal: 'TJRO',
      initialStart: '2026-01-01',
      initialEnd: '2026-01-03',
    });

    const select = screen.getByLabelText(/tribunal/i) as HTMLSelectElement;
    await fireEvent.change(select, { target: { value: 'TJSP' } });

    await waitFor(() => {
      expect(screen.getByText(/sem evidência suficiente neste período/i)).toBeInTheDocument();
    });
  });

  it('reflects the current selection in the URL querystring', async () => {
    render(TribunalCoverageExplorer, {
      calendarRows: ROWS,
      tribunals: TRIBUNALS,
      publicBase: '/',
      initialTribunal: 'TJRO',
      initialStart: '2026-01-01',
      initialEnd: '2026-01-03',
    });

    const select = screen.getByLabelText(/tribunal/i) as HTMLSelectElement;
    await fireEvent.change(select, { target: { value: 'TJSP' } });

    await waitFor(() => {
      const params = new URLSearchParams(window.location.search);
      expect(params.get('tribunal')).toBe('TJSP');
    });
  });

  it('links to the full per-tribunal calendar page', () => {
    render(TribunalCoverageExplorer, {
      calendarRows: ROWS,
      tribunals: TRIBUNALS,
      publicBase: '/',
      initialTribunal: 'TJRO',
      initialStart: '2026-01-01',
      initialEnd: '2026-01-03',
    });

    const link = screen.getByRole('link', { name: /ver calendário completo/i }) as HTMLAnchorElement;
    expect(link.getAttribute('href')).toBe('/publicacoes/tjro');
  });
});
