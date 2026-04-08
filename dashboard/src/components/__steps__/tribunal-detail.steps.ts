import './shared';
import { render, cleanup } from '@testing-library/svelte/pure';
import { loadFeature, describeFeature } from '@amiceli/vitest-cucumber';
import TribunalDetail from '../TribunalDetail.svelte';

const feature = await loadFeature('features/tribunal-detail.feature');

describeFeature(feature, ({ Scenario, BeforeEachScenario }) => {
  let props: any;

  BeforeEachScenario(() => {
    cleanup();
  });

  function makeProps(code: string) {
    return {
      tribunalCode: code,
      initialCoverage: {},
      initialEtas: {},
      initialTargetRange: { start: '2024-01-01', end: '2024-12-31' },
      initialStartDates: {},
      initialQualityScores: {},
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
});
