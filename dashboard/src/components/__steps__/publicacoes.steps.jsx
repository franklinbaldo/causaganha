import './shared.js';
import { render, screen, cleanup } from '@testing-library/preact/pure';
import { loadFeature, describeFeature } from '@amiceli/vitest-cucumber';
import { TribunalView } from '../TribunalView';

const feature = await loadFeature('features/publicacoes.feature');

describeFeature(feature, ({ Scenario, BeforeEachScenario }) => {
  let props;

  BeforeEachScenario(() => {
    cleanup();
  });

  function resetProps() {
    props = {
      initialCoverage: {},
      initialEtas: {},
      initialStartDates: {},
      initialQualityScores: {},
      initialPipeline: null,
      initialProgressByYear: {},
      initialVolume: {},
      initialVelocityMetrics: {},
      initialIaSnapshot: { summary: {}, items: {}, by_year: {} },
    };
  }

  Scenario('Show archive progress banner', ({ Given, When, Then, And }) => {
    resetProps();

    Given('the IA snapshot has 15000 total ZIPs', () => {
      props.initialIaSnapshot.summary.total_zips = 15000;
    });

    And('85 tribunals have data', () => {
      props.initialIaSnapshot.summary.tribunals_with_data = 85;
      props.initialIaSnapshot.summary.tribunals_total = 96;
    });

    When('the publications overview loads', () => {
      render(<TribunalView {...props} />);
    });

    Then('I should see "Progresso do Arquivo"', () => {
      expect(screen.getByText('Progresso do Arquivo')).toBeTruthy();
    });

    And('I should see the ZIP count in the banner', () => {
      // toLocaleString() without locale returns "15,000" in Node.js
      // Appears in both banner text and stats grid
      expect(screen.getAllByText(/15,000/).length).toBeGreaterThan(0);
    });

    And('I should see "85" as tribunals with data', () => {
      expect(screen.getByText('85')).toBeTruthy();
    });
  });

  Scenario('Show tribunal cards in the grid', ({ Given, When, Then, And }) => {
    resetProps();

    Given('coverage data for tribunals STF and STJ', () => {
      props.initialIaSnapshot.items = {
        'backup-djen-2024-01-01-STF': { tribunal: 'STF', zip_count: 10, latest_date: '2024-01-01' },
        'backup-djen-2024-01-01-STJ': { tribunal: 'STJ', zip_count: 5, latest_date: '2024-01-01' },
      };
    });

    When('the publications overview loads', () => {
      render(<TribunalView {...props} />);
    });

    Then('I should see a card for "STF"', () => {
      // STF is always in TRIBUNAL_GROUPS, so it always renders
      expect(screen.getAllByText('STF').length).toBeGreaterThan(0);
    });

    And('I should see a card for "STJ"', () => {
      expect(screen.getAllByText('STJ').length).toBeGreaterThan(0);
    });
  });

  Scenario('Show group headings for tribunal branches', ({ When, Then, And }) => {
    resetProps();

    When('the publications overview loads with default data', () => {
      render(<TribunalView {...props} />);
    });

    Then('I should see "Tribunais Superiores"', () => {
      expect(screen.getByText('Tribunais Superiores')).toBeTruthy();
    });

    And('I should see "Justica Federal"', () => {
      expect(screen.getByText('Justica Federal')).toBeTruthy();
    });

    And('I should see "Justica Estadual"', () => {
      expect(screen.getByText('Justica Estadual')).toBeTruthy();
    });
  });

  Scenario('Show ZIP counts per tribunal', ({ Given, When, Then }) => {
    resetProps();

    Given('STF has 150 ZIPs in the snapshot', () => {
      props.initialIaSnapshot.items = {
        'backup-djen-2024-STF': { tribunal: 'STF', zip_count: 150, latest_date: '2024-06-01' },
      };
    });

    When('the publications overview loads', () => {
      render(<TribunalView {...props} />);
    });

    Then('I should see "150" next to STF', () => {
      expect(screen.getByText('150')).toBeTruthy();
    });
  });
});
