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

    And('I should see "Página não encontrada"', () => {
      expect(templateContent).toContain('Página não encontrada');
    });
  });

  Scenario('Show navigation buttons', ({ When, Then, And }) => {
    When('the 404 page loads', () => {
      // Template already loaded above
    });

    Then('I should see a "Buscar publicações" link', () => {
      expect(templateContent).toMatch(/<a\s[^>]*>[\s\S]*?Buscar publicações[\s\S]*?<\/a>/);
    });

    And('I should see an "Início" link', () => {
      expect(templateContent).toMatch(/<a\s[^>]*>[\s\S]*?Início[\s\S]*?<\/a>/);
    });
  });

  Scenario('Content does not duplicate the page heading', ({ When, Then }) => {
    When('the 404 page loads', () => {
      // Template already loaded above
    });

    // PageHeader.astro already renders the page's one <h1> (the visible
    // "Página não encontrada" title). This page's own content previously
    // added a second, aria-hidden <h1>404</h1> purely for decoration —
    // two <h1> elements on one page, even with one hidden from AT, is an
    // invalid heading structure (see AUDIT.md #14, archived to
    // docs/history/). The decorative "404" glyph must use a non-heading
    // element instead.
    Then('the page content should not render its own level-1 heading', () => {
      expect(templateContent).not.toMatch(/<h1\b/);
    });
  });
});
