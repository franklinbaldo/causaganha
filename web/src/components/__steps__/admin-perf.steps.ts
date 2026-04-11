import './shared';
import { render, screen, cleanup } from '@testing-library/svelte/pure';
import { loadFeature, describeFeature } from '@amiceli/vitest-cucumber';
import { vi } from 'vitest';

// Mock Observable Plot (uses DOM APIs not available in jsdom)
vi.mock('@observablehq/plot', () => ({
  plot: () => document.createElement('div'),
  line: () => ({}),
  dot: () => ({}),
  barY: () => ({}),
}));

// Mock sub-components that rely on fetch/WebSocket
vi.mock('../LiveStatusWidget.svelte', () => import('./stubs/LiveStatusWidgetStub.svelte'));
vi.mock('../PipelineRunHistory.svelte', () => import('./stubs/PipelineRunHistoryStub.svelte'));

import PerfDashboard from '../PerfDashboard.svelte';

const feature = await loadFeature('features/admin-perf.feature');

describeFeature(feature, ({ Scenario, BeforeEachScenario }) => {
  let perfMetrics: any, qualityScores: any;

  BeforeEachScenario(() => {
    cleanup();
  });

  function resetData() {
    perfMetrics = {
      causaganha_upload_success_rate: 0,
      causaganha_backlog_pending_days: 0,
      causaganha_active_tribunals: 0,
      causaganha_collect_latency_ms: [],
      slowest_tribunals: [],
    };
    qualityScores = {};
  }

  Scenario('Show upload success rate', ({ Given, When, Then }) => {
    resetData();

    Given('perf metrics with 98.5 percent upload success rate', () => {
      perfMetrics.causaganha_upload_success_rate = 98.5;
    });

    When('the perf dashboard loads', () => {
      render(PerfDashboard, { perfMetrics, qualityScores });
    });

    Then('I should see "98.5%" as the upload success rate', () => {
      expect(screen.getByText('98.5%')).toBeTruthy();
    });
  });

  Scenario('Show active tribunals count', ({ Given, When, Then }) => {
    resetData();

    Given('perf metrics with 91 active tribunals', () => {
      perfMetrics.causaganha_active_tribunals = 91;
    });

    When('the perf dashboard loads', () => {
      render(PerfDashboard, { perfMetrics, qualityScores });
    });

    Then('I should see "91" as active tribunals', () => {
      expect(screen.getByText('91')).toBeTruthy();
    });
  });

  Scenario('Show backlog pending days', ({ Given, When, Then }) => {
    resetData();

    Given('perf metrics with 45 backlog pending days', () => {
      perfMetrics.causaganha_backlog_pending_days = 45;
    });

    When('the perf dashboard loads', () => {
      render(PerfDashboard, { perfMetrics, qualityScores });
    });

    Then('I should see "45" as pending backlog days', () => {
      expect(screen.getByText('45')).toBeTruthy();
    });
  });

  Scenario('Show quality grade distribution', ({ Given, When, Then }) => {
    resetData();

    Given('quality scores with grades A:10 B:30 C:40 D:10 F:1', () => {
      const grades: Record<string, number> = { A: 10, B: 30, C: 40, D: 10, F: 1 };
      let i = 0;
      for (const [grade, count] of Object.entries(grades)) {
        for (let j = 0; j < count; j++) {
          qualityScores[`TRIBUNAL_${i++}`] = { grade };
        }
      }
    });

    When('the perf dashboard loads', () => {
      render(PerfDashboard, { perfMetrics, qualityScores });
    });

    Then('I should see grade labels for non-zero grades', () => {
      expect(screen.getByText('Grade Distribution')).toBeTruthy();
    });
  });

  Scenario('Show slowest tribunals', ({ Given, When, Then, And }) => {
    resetData();

    Given('perf metrics with slowest tribunals "TRT1" and "TRT2"', () => {
      perfMetrics.slowest_tribunals = [
        { tribunal: 'TRT1', velocity_14d: 2.5 },
        { tribunal: 'TRT2', velocity_14d: 3.1 },
      ];
    });

    When('the perf dashboard loads', () => {
      render(PerfDashboard, { perfMetrics, qualityScores });
    });

    Then('I should see "TRT1" in the slowest tribunals list', () => {
      expect(screen.getByText(/TRT1/)).toBeTruthy();
    });

    And('I should see "TRT2" in the slowest tribunals list', () => {
      expect(screen.getByText(/TRT2/)).toBeTruthy();
    });
  });
});
