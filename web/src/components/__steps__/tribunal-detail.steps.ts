import { render } from './shared';
import { cleanup } from '@testing-library/svelte/pure';
import { loadFeature, describeFeature } from '@amiceli/vitest-cucumber';
import TribunalDetail from '../TribunalDetail.svelte';

const feature = await loadFeature('features/tribunal-detail.feature');

// tribunalStartDate/coverage are relative to "today" (expectedDays counts
// from initialStartDate to the current date), so scenarios build dates
// relative to now instead of hardcoding a fixed calendar window.
function isoDaysAgo(n: number): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - n);
  return d.toISOString().split('T')[0];
}

describeFeature(feature, ({ Scenario, BeforeEachScenario }) => {
  let props: any;

  BeforeEachScenario(() => {
    cleanup();
  });

  function makeProps(code: string) {
    return {
      tribunalCode: code,
      initialUploadedDates: [] as string[],
      initialAbsentDates: [] as string[],
      initialStartDate: null as string | null,
    };
  }

  Scenario('Show tribunal name and selector', ({ Given, When, Then, And }) => {
    Given('tribunal code is "STF"', () => {
      props = makeProps('STF');
    });

    When('the tribunal detail page loads', () => {
      render(TribunalDetail, props);
    });

    Then('I should see a tribunal selector', () => {
      const select = document.querySelector('select');
      expect(select).toBeTruthy();
    });

    And('"STF" should be selected', () => {
      const select = document.querySelector('select') as HTMLSelectElement;
      expect(select.value).toBe('STF');
    });
  });

  Scenario('Render tribunal content after mount', ({ Given, When, Then }) => {
    Given('tribunal code is "STJ"', () => {
      props = makeProps('STJ');
    });

    When('the component mounts before hash is parsed', () => {
      render(TribunalDetail, props);
    });

    Then('I should see the tribunal name in the detail view', () => {
      const content = document.body.textContent;
      expect(content).toContain('STJ');
    });
  });

  Scenario('Tribunal selector contains all tribunals', ({ Given, When, Then, And }) => {
    Given('tribunal code is "STF"', () => {
      props = makeProps('STF');
    });

    When('the tribunal detail page loads', () => {
      render(TribunalDetail, props);
    });

    Then('the selector should contain "STJ" as an option', () => {
      const options = document.querySelectorAll('select option');
      const values = Array.from(options).map(o => (o as HTMLOptionElement).value);
      expect(values).toContain('STJ');
    });

    And('the selector should contain "TRT1" as an option', () => {
      const options = document.querySelectorAll('select option');
      const values = Array.from(options).map(o => (o as HTMLOptionElement).value);
      expect(values).toContain('TRT1');
    });
  });

  Scenario('Highlight tribunal coverage gap state', ({ Given, When, Then, And }) => {
    Given('tribunal "STF" has 12 missing days and 4 absent days', () => {
      props = makeProps('STF');
      // expectedDays = 18 (17 days ago .. today); 2 uploaded + 4 absent
      // leaves 18 - 2 - 4 = 12 missing days.
      props.initialStartDate = isoDaysAgo(17);
      props.initialUploadedDates = [isoDaysAgo(17), isoDaysAgo(16)];
      props.initialAbsentDates = [isoDaysAgo(15), isoDaysAgo(14), isoDaysAgo(13), isoDaysAgo(12)];
    });

    When('the tribunal detail page loads', () => {
      render(TribunalDetail, props);
    });

    Then('I should see a coverage gap attention card', () => {
      expect(document.body.textContent).toContain('Lacuna de cobertura do tribunal');
      expect(document.body.textContent).toContain('STF tem 12 dias sem publicação coletada');
    });

    And('I should see explanatory next action text', () => {
      expect(document.body.textContent).toContain('Próxima ação: revisar o calendário');
      expect(document.body.textContent).toContain('Possível causa: backfill pendente');
    });
  });

  Scenario('Highlight tribunal anomaly state', ({ Given, When, Then, And }) => {
    Given('tribunal "STJ" has low completion coverage', () => {
      props = makeProps('STJ');
      // expectedDays = 10 (9 days ago .. today); 1 uploaded day → 10% completion.
      props.initialStartDate = isoDaysAgo(9);
      props.initialUploadedDates = [isoDaysAgo(9)];
    });

    When('the tribunal detail page loads', () => {
      render(TribunalDetail, props);
    });

    Then('I should see an anomaly attention card', () => {
      expect(document.body.textContent).toContain('Destaque de anomalia');
    });

    And('I should see the anomaly impact text', () => {
      expect(document.body.textContent).toContain('Impacto: o tempo para concluir o histórico pode aumentar.');
      expect(document.body.textContent).toContain('Próxima ação: comparar velocidade');
    });
  });

});
