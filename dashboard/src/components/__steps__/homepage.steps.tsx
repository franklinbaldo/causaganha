import { loadFeature, describeFeature } from '@amiceli/vitest-cucumber';
import { formatNumber, HOW_IT_WORKS_CARDS, AUDIENCE_CARDS } from '../../lib/homepage-content';

const feature = await loadFeature('features/homepage.feature');

// The homepage is a server-rendered Astro page that reads JSON at build time.
// We test the data processing logic and content constants used by the page template.
// Full page rendering is validated by `npm run build` in CI.

describeFeature(feature, ({ Scenario }) => {
  let snapshot: any, pipeline: any, rendered: any;

  function resetData() {
    snapshot = { total_zips: 0, tribunals_with_data: 0, total_size_gb: 0, tribunals_total: 96 };
    pipeline = { progress_pct: 0 };
    rendered = {};
  }

  function renderData() {
    rendered = {
      totalZips: formatNumber(snapshot.total_zips),
      tribunalsWithData: snapshot.tribunals_with_data.toString(),
      totalGB: snapshot.total_size_gb.toString(),
      progressPct: pipeline.progress_pct + '%',
    };
  }

  Scenario('Display pipeline stats cards', ({ Given, When, Then, And }) => {
    resetData();

    Given('the snapshot has 15000 total ZIPs', () => {
      snapshot.total_zips = 15000;
    });

    And('the snapshot has 85 tribunals with data', () => {
      snapshot.tribunals_with_data = 85;
    });

    And('the snapshot has 120 GB archived', () => {
      snapshot.total_size_gb = 120;
    });

    When('the homepage loads', () => {
      renderData();
    });

    Then('I should see "15K" in the stats section', () => {
      expect(rendered.totalZips).toBe('15K');
    });

    And('I should see "85" in the tribunals card', () => {
      expect(rendered.tribunalsWithData).toBe('85');
    });

    And('I should see "120" in the volume card', () => {
      expect(rendered.totalGB).toBe('120');
    });
  });

  Scenario('Show live pipeline card with backfill progress', ({ Given, When, Then }) => {
    resetData();

    Given('the pipeline has 75 percent backfill progress', () => {
      pipeline.progress_pct = 75;
    });

    When('the homepage loads', () => {
      renderData();
    });

    Then('I should see "75%" in the pipeline card', () => {
      expect(rendered.progressPct).toBe('75%');
    });
  });

  Scenario('Display all how-it-works cards', ({ When, Then, And }) => {
    resetData();

    When('the homepage loads', () => {
      // Use the real content constants imported from the shared module
      rendered.sections = HOW_IT_WORKS_CARDS.map(c => c.title);
    });

    Then('I should see "Coleta Automatica"', () => {
      expect(rendered.sections).toContain('1. Coleta Automatica');
    });

    And('I should see "Arquivo Permanente"', () => {
      expect(rendered.sections).toContain('2. Arquivo Permanente');
    });

    And('I should see "Catalogo Indexado"', () => {
      expect(rendered.sections).toContain('3. Catalogo Indexado');
    });
  });

  Scenario('Display all audience cards', ({ When, Then, And }) => {
    resetData();

    When('the homepage loads', () => {
      // Use the real content constants imported from the shared module
      rendered.audiences = AUDIENCE_CARDS.map(c => c.title);
    });

    Then('I should see "Pesquisadores"', () => {
      expect(rendered.audiences).toContain('Pesquisadores');
    });

    And('I should see "LegalTechs"', () => {
      expect(rendered.audiences).toContain('LegalTechs');
    });

    And('I should see "Jornalistas"', () => {
      expect(rendered.audiences).toContain('Jornalistas');
    });
  });
});
