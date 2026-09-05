import { loadFeature, describeFeature } from '@amiceli/vitest-cucumber';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const feature = await loadFeature('features/not-found.feature');
const templatePath = resolve(import.meta.dirname, '../../../src/pages/404.astro');
const templateContent = readFileSync(templatePath, 'utf-8');

describeFeature(feature, ({ Scenario }) => {
  Scenario('Show 404 error message', ({ When, Then, And }) => {
    When('the 404 page loads', () => {});

    Then('I should see "404"', () => {
      expect(templateContent).toContain('>404</p>');
    });

    And('I should see "Página não encontrada"', () => {
      expect(templateContent).toContain('Página não encontrada');
    });
  });

  Scenario('Show navigation buttons', ({ When, Then, And }) => {
    When('the 404 page loads', () => {});

    Then('I should see a "Buscar publicações" link', () => {
      expect(templateContent).toMatch(/<a\s[^>]*>[\s\S]*?Buscar publicações[\s\S]*?<\/a>/);
    });

    And('I should see an "Início" link', () => {
      expect(templateContent).toMatch(/<a\s[^>]*>[\s\S]*?Início[\s\S]*?<\/a>/);
    });
  });

  Scenario('Content does not duplicate the page heading', ({ When, Then }) => {
    When('the 404 page loads', () => {});

    Then('the page content should not render its own level-1 heading', () => {
      const headings = templateContent.match(/<h1\b/g) ?? [];
      expect(headings).toHaveLength(1);
      expect(templateContent).toMatch(/<p[^>]*aria-hidden="true"[^>]*>404<\/p>/);
    });
  });
});
