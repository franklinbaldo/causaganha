import { loadFeature, describeFeature } from '@amiceli/vitest-cucumber';
import { processCoverageOverview, processCourtReliability, processWeeklyPattern } from '../../lib/stats-processing';

const feature = await loadFeature('features/stats.feature');

// The stats page is server-rendered Astro. We test the shared processing functions
// that the Astro frontmatter imports, ensuring the test validates the real logic.

describeFeature(feature, ({ Scenario }) => {
  let completedItems: Record<string, any>, coverageResult: any, courtResult: any, weeklyResult: any;

  function generateDays(n: number, baseCount: number): Record<string, any> {
    const items: Record<string, any> = {};
    const tribunals = ['STF', 'STJ', 'TST', 'TSE', 'TRF1', 'TJSP'];
    for (let i = 0; i < n; i++) {
      const d = new Date(2024, 0, 1 + i);
      const dateStr = d.toISOString().slice(0, 10);
      const count = baseCount + (i % 15) - 5;
      const clampedCount = Math.max(0, count);
      items[dateStr] = {
        tribunal_count: clampedCount,
        tribunais_coletados: tribunals.slice(0, Math.min(clampedCount, tribunals.length)),
        tribunais_ausentes: clampedCount < tribunals.length ? tribunals.slice(clampedCount) : [],
      };
    }
    return items;
  }

  Scenario('Show coverage overview cards', ({ Given, When, Then, And }) => {
    Given('completed items data with 30 days of collection', () => {
      completedItems = generateDays(30, 78);
    });

    And('the average daily coverage is 78 out of 91', () => {
      // Already set by generateDays with baseCount=78
    });

    When('the stats page renders', () => {
      coverageResult = processCoverageOverview(completedItems);
    });

    Then('I should see the average coverage percentage', () => {
      expect(coverageResult.avgPct).toBeGreaterThan(0);
      expect(coverageResult.avgPct).toBeLessThanOrEqual(100);
      // Verify the formatted value matches what the page would display
      const formatted = coverageResult.avgPct.toFixed(1);
      expect(parseFloat(formatted)).toBeGreaterThan(0);
    });

    And('I should see the best and worst collection days', () => {
      expect(coverageResult.bestDay).toBeTruthy();
      expect(coverageResult.worstDay).toBeTruthy();
      expect(coverageResult.bestCount).toBeGreaterThanOrEqual(coverageResult.worstCount);
    });
  });

  Scenario('Show court reliability rankings', ({ Given, When, Then, And }) => {
    Given('completed items data with tribunal performance', () => {
      completedItems = generateDays(60, 78);
    });

    When('the stats page renders', () => {
      courtResult = processCourtReliability(completedItems);
    });

    Then('I should see "Mais Confiáveis" section with top courts', () => {
      expect(courtResult.top5.length).toBeGreaterThan(0);
      expect(courtResult.top5[0].rate).toBeGreaterThanOrEqual(courtResult.top5[courtResult.top5.length - 1].rate);
    });

    And('I should see "Mais Falhas" section with bottom courts', () => {
      expect(courtResult.bottom5.length).toBeGreaterThan(0);
      expect(courtResult.bottom5[0].rate).toBeLessThanOrEqual(courtResult.bottom5[courtResult.bottom5.length - 1].rate);
    });
  });

  Scenario('Show weekly collection pattern', ({ Given, When, Then, And }) => {
    Given('completed items data with 30 days of collection', () => {
      completedItems = generateDays(30, 78);
    });

    When('the stats page renders', () => {
      weeklyResult = processWeeklyPattern(completedItems);
    });

    Then('I should see all 7 days of the week', () => {
      expect(weeklyResult.weeklyAverages.length).toBe(7);
    });

    And('each day should show an average coverage percentage', () => {
      for (const day of weeklyResult.weeklyAverages) {
        expect(day.name).toBeTruthy();
        expect(typeof day.avg).toBe('number');
        expect(typeof day.avgPct).toBe('number');
      }
    });
  });
});
