import { loadFeature, describeFeature } from '@amiceli/vitest-cucumber';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const feature = await loadFeature('features/not-found.feature');

// The 404 page is pure Astro HTML — we read the actual template and validate
// that the expected text and links are present in the real source file.
const templatePath = resolve(import.meta.dirname, '../../../src/pages/404.astro');
const templateContent = readFileSync(templatePath, 'utf-8');

describeFeature(feature, ({ Scenario }) => {
  Scenario('Show 404 error message', ({ When, Then, And }) => {
    When('the 404 page loads', () => {
      // Template already loaded above
    });

    Then('I should see "404"', () => {
      expect(templateContent).toContain('>404</');
    });

    And('I should see "Pagina nao encontrada"', () => {
      expect(templateContent).toContain('Pagina nao encontrada');
    });
  });

  Scenario('Show navigation buttons', ({ When, Then, And }) => {
    When('the 404 page loads', () => {
      // Template already loaded above
    });

    Then('I should see a "Dashboard" link', () => {
      // Verify there's an <a> tag containing "Dashboard"
      expect(templateContent).toMatch(/<a\s[^>]*>[\s\S]*?Dashboard[\s\S]*?<\/a>/);
    });

    And('I should see an "Inicio" link', () => {
      // Verify there's an <a> tag containing "Inicio"
      expect(templateContent).toMatch(/<a\s[^>]*>[\s\S]*?Inicio[\s\S]*?<\/a>/);
    });
  });
});
