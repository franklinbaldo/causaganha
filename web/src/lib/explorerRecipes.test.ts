import { describe, expect, it } from 'vitest';

import { buildExplorerRecipes, normalizeCnj, recipeIsAvailable } from './explorerRecipes';

const path = (fileName: string) => `https://archive.org/download/djen-tjro-2026/${fileName}`;

describe('explorerRecipes', () => {
  it('offers a compact catalog with period, CNJ and provenance recipes', () => {
    const recipes = buildExplorerRecipes(path, {
      startDate: '2026-01-01',
      endDate: '2026-01-31',
      cnj: '0001234-56.2026.8.22.0001',
    });

    expect(recipes.length).toBeGreaterThanOrEqual(5);
    expect(recipes.map((recipe) => recipe.key)).toEqual(
      expect.arrayContaining(['por-periodo', 'por-cnj', 'por-data-orgao', 'proveniencia']),
    );
    expect(recipes.every((recipe) => recipe.sql.includes('djen-tjro-2026'))).toBe(true);
  });

  it('renders period filters as typed DATE literals only after valid dates are supplied', () => {
    const ready = buildExplorerRecipes(path, {
      startDate: '2026-02-01',
      endDate: '2026-02-28',
    }).find((recipe) => recipe.key === 'por-periodo');
    const invalid = buildExplorerRecipes(path, {
      startDate: "2026-02-01' OR 1=1 --",
      endDate: '2026-02-28',
    }).find((recipe) => recipe.key === 'por-periodo');

    expect(ready?.missingInput).toBeNull();
    expect(ready?.sql).toContain("DATE '2026-02-01'");
    expect(ready?.sql).toContain("DATE '2026-02-28'");
    expect(invalid?.missingInput).toBe('period');
    expect(invalid?.sql).not.toContain('OR 1=1');
  });

  it('normalizes CNJ input to exactly 20 digits before interpolation', () => {
    expect(normalizeCnj('0001234-56.2026.8.22.0001')).toBe('00012345620268220001');
    expect(normalizeCnj("0001234' OR 1=1 --")).toBeNull();

    const recipe = buildExplorerRecipes(path, {
      cnj: '0001234-56.2026.8.22.0001',
    }).find((item) => item.key === 'por-cnj');
    expect(recipe?.sql).toContain("= '00012345620268220001'");
  });

  it('declares file dependencies so unavailable recipes can be disabled without guessing', () => {
    const recipes = buildExplorerRecipes(path);
    const activeLawyers = recipes.find((recipe) => recipe.key === 'advogados-ativos');
    const schema = recipes.find((recipe) => recipe.key === 'schema');

    expect(activeLawyers).toBeDefined();
    expect(recipeIsAvailable(activeLawyers!, ['advogados.parquet'])).toBe(false);
    expect(recipeIsAvailable(activeLawyers!, ['advogados.parquet', 'comunicacao_advogados.parquet'])).toBe(true);
    expect(recipeIsAvailable(schema!, ['comunicacoes.parquet'])).toBe(true);
  });

  it('keeps the remote parquet path explicit in every executable recipe', () => {
    const recipes = buildExplorerRecipes(path, {
      startDate: '2026-01-01',
      endDate: '2026-12-31',
      cnj: '00012345620268220001',
    });

    for (const recipe of recipes) {
      expect(recipe.sql).toContain('read_parquet');
      expect(recipe.sql).toContain('https://archive.org/download/djen-tjro-2026/');
    }
  });
});
