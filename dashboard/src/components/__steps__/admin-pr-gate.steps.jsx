import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/preact/pure';
import { loadFeature, describeFeature } from '@amiceli/vitest-cucumber';
import { vi } from 'vitest';
import { PRGateExplainer } from '../PRGateExplainer';

const feature = await loadFeature('features/admin-pr-gate.feature');

describeFeature(feature, ({ Scenario, BeforeEachScenario }) => {
  let fetchMock;

  BeforeEachScenario(() => {
    cleanup();
  });

  function setupFetchMock(responses) {
    fetchMock = vi.fn((url) => {
      for (const [pattern, response] of Object.entries(responses)) {
        if (url.includes(pattern)) {
          return Promise.resolve(response);
        }
      }
      return Promise.resolve({ ok: false, status: 404 });
    });
    globalThis.fetch = fetchMock;
  }

  Scenario('Show PR lookup form', ({ When, Then, And }) => {
    When('the PR gate page loads', () => {
      render(<PRGateExplainer />);
    });

    Then('I should see a PR number input field', () => {
      const input = document.querySelector('input[type="number"]');
      expect(input).toBeTruthy();
    });

    And('I should see a submit button', () => {
      expect(screen.getByText('Check PR')).toBeTruthy();
    });
  });

  Scenario('Show loading state during fetch', ({ Given, When, Then }) => {
    Given('the PR gate page is loaded', () => {
      globalThis.fetch = vi.fn(() => new Promise(() => {}));
      render(<PRGateExplainer />);
    });

    When('I submit PR number "42"', () => {
      const input = document.querySelector('input[type="number"]');
      fireEvent.input(input, { target: { value: '42' } });
      fireEvent.submit(input.closest('form'));
    });

    Then('I should see a loading indicator', () => {
      expect(screen.getByText('Checking...')).toBeTruthy();
    });
  });

  Scenario('Show error on invalid PR', ({ Given, When, Then, And }) => {
    Given('the PR gate page is loaded', () => {
      render(<PRGateExplainer />);
    });

    And('the GitHub API returns an error', () => {
      globalThis.fetch = vi.fn(() =>
        Promise.resolve({ ok: false, status: 404 })
      );
    });

    When('I submit PR number "99999"', async () => {
      const input = document.querySelector('input[type="number"]');
      fireEvent.input(input, { target: { value: '99999' } });
      fireEvent.submit(input.closest('form'));
      await waitFor(() => {
        const errorEl = document.querySelector('[class*="danger"]');
        if (!errorEl) throw new Error('waiting for error');
      });
    });

    Then('I should see an error message', () => {
      expect(screen.getByText(/Failed to fetch PR details/)).toBeTruthy();
    });
  });

  Scenario('Show merged PR status', ({ Given, When, Then, And }) => {
    Given('the PR gate page is loaded', () => {
      render(<PRGateExplainer />);
    });

    And('PR 42 is already merged', () => {
      setupFetchMock({
        '/pulls/42': {
          ok: true,
          json: () => Promise.resolve({
            number: 42,
            title: 'Fix collection bug',
            state: 'closed',
            merged: true,
            head: { sha: 'abc123' },
          }),
        },
        '/reviews': {
          ok: true,
          json: () => Promise.resolve([]),
        },
        '/check-runs': {
          ok: true,
          json: () => Promise.resolve({ check_runs: [] }),
        },
      });
    });

    When('I submit PR number "42"', async () => {
      const input = document.querySelector('input[type="number"]');
      fireEvent.input(input, { target: { value: '42' } });
      fireEvent.submit(input.closest('form'));
      await waitFor(() => screen.getByText('Merged'));
    });

    Then('I should see "Merged" status', () => {
      expect(screen.getByText('Merged')).toBeTruthy();
    });
  });
});
