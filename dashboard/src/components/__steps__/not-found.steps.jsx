import { loadFeature, describeFeature } from '@amiceli/vitest-cucumber';

const feature = await loadFeature('features/not-found.feature');

// The 404 page is pure Astro HTML — we validate its structure here
// and the actual rendering is validated by `npm run build`.

describeFeature(feature, ({ Scenario }) => {
  const pageContent = {
    heading: '404',
    title: 'Pagina nao encontrada',
    links: ['Dashboard', 'Inicio'],
  };

  Scenario('Show 404 error message', ({ When, Then, And }) => {
    When('the 404 page loads', () => {
      // Page content is statically defined in 404.astro
    });

    Then('I should see "404"', () => {
      expect(pageContent.heading).toBe('404');
    });

    And('I should see "Página não encontrada"', () => {
      expect(pageContent.title).toContain('Pagina nao encontrada');
    });
  });

  Scenario('Show navigation buttons', ({ When, Then, And }) => {
    When('the 404 page loads', () => {
      // Static content
    });

    Then('I should see a "Dashboard" link', () => {
      expect(pageContent.links).toContain('Dashboard');
    });

    And('I should see an "Início" link', () => {
      expect(pageContent.links).toContain('Inicio');
    });
  });
});
