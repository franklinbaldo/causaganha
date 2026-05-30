import { readFileSync } from 'node:fs';
import { loadFeature, describeFeature } from '@amiceli/vitest-cucumber';

const feature = await loadFeature('features/data-source-indicator.feature');

describeFeature(feature, ({ Scenario }) => {
  let generatedAt = '';
  let indicator: HTMLElement;

  async function flushPromises() {
    await Promise.resolve();
    await Promise.resolve();
  }

  async function renderIndicator() {
    document.body.innerHTML = '<small id="datasource-indicator" class="datasource" role="status">Connecting...</small>';
    indicator = document.getElementById('datasource-indicator')!;

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue({ generated_at: generatedAt }),
      }),
    );

    const component = readFileSync('src/components/DataSourceIndicator.astro', 'utf8');
    const script = component.match(/<script>([\s\S]*?)<\/script>/)?.[1];
    if (!script) {
      throw new Error('DataSourceIndicator script not found');
    }

    const executableScript = script.replace(/indicator!/g, 'indicator');
    Function(executableScript)();
    await flushPromises();
  }

  Scenario('Escape HTML characters from generated_at payload', ({ Given, When, Then, And }) => {
    Given('the Internet Archive metadata has generated_at with HTML characters', () => {
      generatedAt = '<em>2026-05-30Z</em>';
    });

    When('the data source indicator probes the metadata', async () => {
      await renderIndicator();
    });

    Then('the generated_at HTML should be displayed as text', () => {
      expect(indicator.textContent).toContain('Live via Internet Archive (<em>2026-05-30Z<)');
      expect(indicator.querySelector('em')).toBeNull();
    });

    And('the live pulse should be rendered as a span', () => {
      const pulse = indicator.querySelector('span.cg-pulse');
      expect(pulse).toBeInstanceOf(HTMLSpanElement);
    });
  });
});
