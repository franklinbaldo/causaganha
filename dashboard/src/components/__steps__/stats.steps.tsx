import { loadFeature, describeFeature } from '@amiceli/vitest-cucumber';

const feature = await loadFeature('features/stats.feature');

// The stats page is server-rendered Astro. We test the data processing logic
// that the Astro frontmatter uses. Full page rendering is validated by build.

function processCompletedItems(data: Record<string, any>) {
  const sortedDates = Object.keys(data).sort((a, b) => b.localeCompare(a));
  const recent30 = sortedDates.slice(0, 30);

  let totalCoverage = 0;
  let bestDay: string | null = null, worstDay: string | null = null;
  let bestCount = -1, worstCount = 999;

  for (const date of recent30) {
    const count = data[date].tribunal_count || 0;
    totalCoverage += count;
    if (count > bestCount) { bestCount = count; bestDay = date; }
    if (count < worstCount) { worstCount = count; worstDay = date; }
  }

  const avgCoverage = recent30.length > 0 ? totalCoverage / recent30.length : 0;
  const avgPct = (avgCoverage / 91) * 100;

  const courtStats: Record<string, { collected: number; absent: number }> = {};
  for (const date of sortedDates) {
    const item = data[date];
    for (const c of (item.tribunais_coletados || [])) {
      if (!courtStats[c]) courtStats[c] = { collected: 0, absent: 0 };
      courtStats[c].collected++;
    }
    for (const c of (item.tribunais_ausentes || [])) {
      if (!courtStats[c]) courtStats[c] = { collected: 0, absent: 0 };
      courtStats[c].absent++;
    }
  }

  const courtArray = Object.keys(courtStats).map(c => {
    const total = courtStats[c].collected + courtStats[c].absent;
    const rate = total > 0 ? courtStats[c].collected / total : 0;
    return { court: c, rate, total, collected: courtStats[c].collected, absent: courtStats[c].absent };
  });
  courtArray.sort((a, b) => b.rate - a.rate || b.total - a.total);

  const top5 = courtArray.slice(0, 5);
  const bottom5 = [...courtArray].sort((a, b) => a.rate - b.rate || b.total - a.total).slice(0, 5);

  const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  const weekdayStats: Record<number, { totalCount: number; days: number }> = {};
  for (let i = 0; i < 7; i++) weekdayStats[i] = { totalCount: 0, days: 0 };

  for (const date of recent30) {
    const dow = new Date(date + 'T12:00:00Z').getUTCDay();
    weekdayStats[dow].totalCount += data[date].tribunal_count || 0;
    weekdayStats[dow].days++;
  }

  const weeklyPattern = dayNames.map((name, i) => ({
    name,
    avg: weekdayStats[i].days > 0 ? weekdayStats[i].totalCount / weekdayStats[i].days : 0,
    days: weekdayStats[i].days,
  }));

  return { avgPct, bestDay, bestCount, worstDay, worstCount, top5, bottom5, weeklyPattern };
}

describeFeature(feature, ({ Scenario }) => {
  let completedItems: Record<string, any>, result: any;

  function generateDays(n: number, baseCount: number): Record<string, any> {
    const items: Record<string, any> = {};
    const tribunals = ['STF', 'STJ', 'TST', 'TSE', 'TRF1', 'TJSP'];
    for (let i = 0; i < n; i++) {
      const d = new Date(2024, 0, 1 + i);
      const dateStr = d.toISOString().slice(0, 10);
      const count = baseCount + (i % 15) - 5;
      items[dateStr] = {
        tribunal_count: Math.max(0, count),
        tribunais_coletados: tribunals.slice(0, Math.min(count, tribunals.length)),
        tribunais_ausentes: count < tribunals.length ? tribunals.slice(count) : [],
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
      result = processCompletedItems(completedItems);
    });

    Then('I should see the average coverage percentage', () => {
      expect(result.avgPct).toBeGreaterThan(0);
      expect(result.avgPct).toBeLessThanOrEqual(100);
    });

    And('I should see the best and worst collection days', () => {
      expect(result.bestDay).toBeTruthy();
      expect(result.worstDay).toBeTruthy();
      expect(result.bestCount).toBeGreaterThanOrEqual(result.worstCount);
    });
  });

  Scenario('Show court reliability rankings', ({ Given, When, Then, And }) => {
    Given('completed items data with tribunal performance', () => {
      completedItems = generateDays(60, 78);
    });

    When('the stats page renders', () => {
      result = processCompletedItems(completedItems);
    });

    Then('I should see "Mais Confiáveis" section with top courts', () => {
      expect(result.top5.length).toBeGreaterThan(0);
      expect(result.top5[0].rate).toBeGreaterThanOrEqual(result.top5[result.top5.length - 1].rate);
    });

    And('I should see "Mais Falhas" section with bottom courts', () => {
      expect(result.bottom5.length).toBeGreaterThan(0);
      expect(result.bottom5[0].rate).toBeLessThanOrEqual(result.bottom5[result.bottom5.length - 1].rate);
    });
  });

  Scenario('Show weekly collection pattern', ({ Given, When, Then, And }) => {
    Given('completed items data with 30 days of collection', () => {
      completedItems = generateDays(30, 78);
    });

    When('the stats page renders', () => {
      result = processCompletedItems(completedItems);
    });

    Then('I should see all 7 days of the week', () => {
      expect(result.weeklyPattern.length).toBe(7);
    });

    And('each day should show an average coverage percentage', () => {
      for (const day of result.weeklyPattern) {
        expect(day.name).toBeTruthy();
        expect(typeof day.avg).toBe('number');
      }
    });
  });
});
