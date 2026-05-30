import { render } from './shared';
import { screen, cleanup, waitFor, fireEvent } from '@testing-library/svelte/pure';
import { loadFeature, describeFeature } from '@amiceli/vitest-cucumber';
import { expect, vi } from 'vitest';
import PublicationSearchRaw from '../PublicationSearch.svelte';
import { clearDjenSearchCache } from '../../lib/djen';

// Astro's Svelte integration wraps components with PropsWithClientDirectives
// which confuses testing-library's types. Cast to any for the tests.
const PublicationSearch = PublicationSearchRaw as unknown as Parameters<typeof render>[0];

const feature = await loadFeature('features/publicacoes-search.feature');

function samplePublication(id: number) {
  return {
    id,
    numeroComunicacao: id,
    siglaTribunal: 'TJSP',
    texto: `Exemplo de publicação ${id}`,
    data_disponibilizacao: '2026-04-01',
    tipoDocumento: 'Intimação',
    nomeOrgao: 'Vara X',
    destinatarios: [],
    destinatarioadvogados: [],
  };
}

function mockFetchOnce(body: unknown, init: { status?: number; headers?: Record<string, string> } = {}) {
  const fetchMock = vi.fn().mockImplementation(
    async () =>
      new Response(JSON.stringify(body), {
        status: init.status ?? 200,
        headers: init.headers,
      }),
  );
  global.fetch = fetchMock as unknown as typeof fetch;
  return fetchMock;
}

function fetchCallUrl(call: unknown[]): URL {
  const [input] = call;
  if (input instanceof Request) return new URL(input.url);
  return new URL(String(input));
}

function latestFetchUrl(fetchMock: ReturnType<typeof vi.fn>): URL {
  const calls = fetchMock.mock.calls;
  return fetchCallUrl(calls[calls.length - 1] as unknown[]);
}

async function typeAndSubmit(input: HTMLInputElement, value: string) {
  await fireEvent.input(input, { target: { value } });
  await fireEvent.keyDown(input, { key: 'Enter' });
}

describeFeature(feature, ({ Scenario, BeforeEachScenario, AfterEachScenario }) => {
  BeforeEachScenario(() => {
    cleanup();
    clearDjenSearchCache();
    vi.restoreAllMocks();
    // Reset URL between scenarios
    if (typeof window !== 'undefined') {
      window.history.replaceState({}, '', '/');
    }
  });

  AfterEachScenario(() => {
    clearDjenSearchCache();
  });

  Scenario('Idle state shows instructions', ({ When, Then }) => {
    When('the publication search loads with no URL params', () => {
      render(PublicationSearch);
    });

    Then('I should see instructions about OAB, processo or texto livre', () => {
      expect(
        screen.getByText(/Comece digitando um número de OAB, um processo CNJ ou um termo livre/i),
      ).toBeTruthy();
    });
  });

  Scenario('User searches by OAB and sees results', ({ Given, When, Then, And }) => {
    let fetchMock: ReturnType<typeof vi.fn>;

    Given('the DJEN API returns 2 publications for the next request', () => {
      fetchMock = mockFetchOnce(
        { items: [samplePublication(1), samplePublication(2)], count: 2 },
        { headers: { 'x-ratelimit-limit': '30', 'x-ratelimit-remaining': '29' } },
      );
    });

    When('I enter "OAB/SP 123456" and press Enter', async () => {
      render(PublicationSearch);
      const input = screen.getByLabelText('Buscar publicações') as HTMLInputElement;
      await typeAndSubmit(input, 'OAB/SP 123456');
    });

    Then('I should see 2 result cards', async () => {
      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalled();
        expect(screen.getByText(/2 resultado/)).toBeTruthy();
      });
    });

    And('I should see "OAB SP/123456 detectada" as the hint', () => {
      expect(screen.getByText(/OAB SP\/123456 detectada/)).toBeTruthy();
    });
  });

  Scenario('User pastes a CNJ process number', ({ Given, When, Then, And }) => {
    let fetchMock: ReturnType<typeof vi.fn>;

    Given('the DJEN API returns 1 publication for the next request', () => {
      fetchMock = mockFetchOnce(
        { items: [samplePublication(7)], count: 1 },
        { headers: { 'x-ratelimit-limit': '30', 'x-ratelimit-remaining': '28' } },
      );
    });

    When('I enter "1234567-89.2024.8.26.0100" and press Enter', async () => {
      render(PublicationSearch);
      const input = screen.getByLabelText('Buscar publicações') as HTMLInputElement;
      await typeAndSubmit(input, '1234567-89.2024.8.26.0100');
    });

    Then('I should see the hint "Número de processo CNJ detectado"', () => {
      expect(screen.getByText(/Número de processo CNJ detectado/)).toBeTruthy();
    });

    And('I should see 1 result card', async () => {
      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalled();
        expect(screen.getByText(/1 resultado/)).toBeTruthy();
      });
    });
  });

  Scenario('User hits the rate limit', ({ Given, When, Then }) => {
    Given('the DJEN API responds with HTTP 429 and retry-after 60', () => {
      mockFetchOnce(
        { message: 'Too Many Requests' },
        { status: 429, headers: { 'retry-after': '60' } },
      );
    });

    When('I enter "contrato" with tribunal "TJSP" and press Enter', async () => {
      render(PublicationSearch);
      const input = screen.getByLabelText('Buscar publicações') as HTMLInputElement;
      // Expand filters and pick tribunal
      await fireEvent.click(screen.getByRole('button', { name: /Filtros avançados/ }));
      const tribunalSelect = screen.getByRole('combobox') as HTMLSelectElement;
      await fireEvent.change(tribunalSelect, { target: { value: 'TJSP' } });
      await typeAndSubmit(input, 'contrato');
    });

    Then('I should see a rate-limit banner with a countdown', async () => {
      await waitFor(() => {
        expect(screen.getByText(/Limite de requisições atingido/i)).toBeTruthy();
      });
    });
  });

  Scenario('Search criteria changes reset pagination', ({ Given, When, Then }) => {
    let fetchMock: ReturnType<typeof vi.fn>;

    Given('the DJEN API returns 30 publications out of 60 for each request', () => {
      fetchMock = mockFetchOnce(
        { items: Array.from({ length: 30 }, (_, i) => samplePublication(i + 1)), count: 60 },
        { headers: { 'x-ratelimit-limit': '30', 'x-ratelimit-remaining': '29' } },
      );
    });

    When(
      'I search for "contrato", go to page 2, and replace the search with "mandado de segurança"',
      async () => {
        render(PublicationSearch);
        const input = screen.getByLabelText('Buscar publicações') as HTMLInputElement;

        await typeAndSubmit(input, 'contrato');
        await waitFor(() => {
          expect(fetchMock).toHaveBeenCalled();
          expect(screen.getByText(/Página 1 de 2/)).toBeTruthy();
        });

        await fireEvent.click(screen.getByRole('button', { name: /Próxima/ }));
        await waitFor(() => {
          expect(latestFetchUrl(fetchMock).searchParams.get('pagina')).toBe('2');
          expect(screen.getByText(/Página 2 de 2/)).toBeTruthy();
        });

        await typeAndSubmit(input, 'mandado de segurança');
      },
    );

    Then('the last DJEN query should request page 1 for "mandado de segurança"', async () => {
      await waitFor(() => {
        const lastUrl = latestFetchUrl(fetchMock);
        expect(lastUrl.searchParams.get('texto')).toBe('mandado de segurança');
        expect(lastUrl.searchParams.get('pagina')).toBe('1');
      });
    });
  });


  Scenario('Active filters are shown and can be removed outside advanced filters', ({ When, Then, And }) => {
    When('I configure advanced filters and close the filters panel', async () => {
      render(PublicationSearch);

      await fireEvent.click(screen.getByRole('button', { name: /Filtros avançados/ }));
      await fireEvent.change(screen.getByLabelText('Tribunal'), { target: { value: 'TJSP' } });
      await fireEvent.input(screen.getByLabelText('Data início'), { target: { value: '2026-05-01' } });
      await fireEvent.input(screen.getByLabelText('Data fim'), { target: { value: '2026-05-30' } });
      await fireEvent.click(screen.getByText('Mais filtros'));
      await fireEvent.input(screen.getByLabelText('OAB — número'), { target: { value: '123456' } });
      await fireEvent.input(screen.getByLabelText('OAB — UF'), { target: { value: 'SP' } });
      await fireEvent.input(screen.getByLabelText('Nome do advogado'), { target: { value: 'Maria Silva' } });
      await fireEvent.input(screen.getByLabelText('Nome da parte'), { target: { value: 'Empresa XYZ' } });
      await fireEvent.click(screen.getByRole('radio', { name: 'Edital' }));
      await fireEvent.click(screen.getByRole('radio', { name: '100' }));
      await fireEvent.click(screen.getByRole('button', { name: /Ocultar filtros/ }));
    });

    Then(
      'I should see active chips for tribunal, period, OAB, UF, advogado, parte, meio and items per page',
      () => {
        expect(screen.getByRole('button', { name: /Remover filtro Tribunal: TJSP/ })).toBeTruthy();
        expect(screen.getByRole('button', { name: /Remover filtro Período: 01\/05\/2026 a 30\/05\/2026/ })).toBeTruthy();
        expect(screen.getByRole('button', { name: /Remover filtro OAB: 123456/ })).toBeTruthy();
        expect(screen.getByRole('button', { name: /Remover filtro UF: SP/ })).toBeTruthy();
        expect(screen.getByRole('button', { name: /Remover filtro Advogado: Maria Silva/ })).toBeTruthy();
        expect(screen.getByRole('button', { name: /Remover filtro Parte: Empresa XYZ/ })).toBeTruthy();
        expect(screen.getByRole('button', { name: /Remover filtro Meio: Edital/ })).toBeTruthy();
        expect(screen.getByRole('button', { name: /Remover filtro Itens por página: 100/ })).toBeTruthy();
      },
    );

    When('I remove the tribunal active filter chip', async () => {
      await fireEvent.click(screen.getByRole('button', { name: /Remover filtro Tribunal: TJSP/ }));
    });

    Then('the filters panel should remain closed', () => {
      expect(screen.queryByLabelText('Tribunal')).toBeNull();
      expect(screen.getByRole('button', { name: /Filtros avançados/ })).toBeTruthy();
    });

    And('the tribunal active filter chip should be removed', () => {
      expect(screen.queryByRole('button', { name: /Remover filtro Tribunal: TJSP/ })).toBeNull();
    });
  });

  Scenario('Clearing all filters resets pagination and page size defaults', ({ Given, When, Then }) => {
    let fetchMock: ReturnType<typeof vi.fn>;

    Given('the DJEN API returns 30 publications out of 60 for each request', () => {
      fetchMock = mockFetchOnce(
        { items: Array.from({ length: 30 }, (_, i) => samplePublication(i + 1)), count: 60 },
        { headers: { 'x-ratelimit-limit': '30', 'x-ratelimit-remaining': '29' } },
      );
    });

    When(
      'I search for "contrato", go to page 2, set 100 items per page, and clear all filters',
      async () => {
        render(PublicationSearch);
        const input = screen.getByLabelText('Buscar publicações') as HTMLInputElement;

        await typeAndSubmit(input, 'contrato');
        await waitFor(() => {
          expect(fetchMock).toHaveBeenCalled();
          expect(screen.getByText(/Página 1 de 2/)).toBeTruthy();
        });

        await fireEvent.click(screen.getByRole('button', { name: /Próxima/ }));
        await waitFor(() => {
          expect(latestFetchUrl(fetchMock).searchParams.get('pagina')).toBe('2');
        });

        await fireEvent.click(screen.getByRole('button', { name: /Filtros avançados/ }));
        await fireEvent.click(screen.getByText('Mais filtros'));
        await fireEvent.click(screen.getByRole('radio', { name: '100' }));
        await waitFor(() => {
          const lastUrl = latestFetchUrl(fetchMock);
          expect(lastUrl.searchParams.get('pagina')).toBe('1');
          expect(lastUrl.searchParams.get('itensPorPagina')).toBe('100');
        });

        await fireEvent.click(screen.getByRole('button', { name: /Limpar tudo/ }));
      },
    );

    Then(
      'active filters should be empty and the URL should request page 1 with 30 items per page',
      async () => {
        expect(screen.getByText(/Nenhum filtro ativo/)).toBeTruthy();
        await waitFor(() => {
          const currentUrl = new URL(window.location.href);
          expect(currentUrl.searchParams.get('pagina')).toBe('1');
          expect(currentUrl.searchParams.get('itensPorPagina')).toBe('30');
        });
      },
    );
  });

  Scenario('User uses Ctrl+K to focus search input', ({ When, Then }) => {
    When('I press Ctrl+K', () => {
      render(PublicationSearch);
      fireEvent.keyDown(window, { key: 'k', ctrlKey: true });
    });

    Then('the search input should be focused', () => {
      const input = screen.getByLabelText('Buscar publicações') as HTMLInputElement;
      expect(document.activeElement).toBe(input);
    });
  });

  Scenario('User presses Escape to clear input', ({ When, Then, And }) => {
    When('I type "Some search text" in the search input', async () => {
      render(PublicationSearch);
      const input = screen.getByLabelText('Buscar publicações') as HTMLInputElement;
      await fireEvent.input(input, { target: { value: 'Some search text' } });
    });

    And('I press Escape', async () => {
      const input = screen.getByLabelText('Buscar publicações') as HTMLInputElement;
      await fireEvent.keyDown(input, { key: 'Escape' });
    });

    Then('the search input should be empty', () => {
      const input = screen.getByLabelText('Buscar publicações') as HTMLInputElement;
      expect(input.value).toBe('');
    });
  });

  Scenario('Input is auto-focused on load', ({ When, Then }) => {
    When('the publication search loads with no URL params', () => {
      render(PublicationSearch);
    });

    Then('the search input should be focused', () => {
      const input = screen.getByLabelText('Buscar publicações') as HTMLInputElement;
      expect(document.activeElement).toBe(input);
    });
  });
});
