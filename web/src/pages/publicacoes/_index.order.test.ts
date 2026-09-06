import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

const pageSource = readFileSync(
  join(process.cwd(), 'src/pages/publicacoes/index.astro'),
  'utf8',
);

function indexOfOrThrow(marker: string): number {
  const index = pageSource.indexOf(marker);
  if (index === -1) throw new Error(`marker not found in publicacoes/index.astro: ${marker}`);
  return index;
}

describe('/publicacoes page hierarchy (#1139)', () => {
  it('renders the search action before the coverage explanation', () => {
    const searchIndex = indexOfOrThrow('<PublicationSearch');
    const coverageIndex = indexOfOrThrow('Cobertura não é uma promessa de completude.');

    expect(searchIndex).toBeLessThan(coverageIndex);
  });

  it('keeps the page hero before search and explanatory alerts after search', () => {
    const heroIndex = indexOfOrThrow('Encontre a publicação.');
    const searchIndex = indexOfOrThrow('<PublicationSearch');
    const coverageAlertIndex = indexOfOrThrow("alert({ tone: 'info' })");

    expect(heroIndex).toBeLessThan(searchIndex);
    expect(searchIndex).toBeLessThan(coverageAlertIndex);
  });

  it('still distinguishes official absence, pending backfill, and transient failure', () => {
    expect(pageSource).toContain('ausência oficial do diário');
    expect(pageSource).toContain('backfill pendente');
    expect(pageSource).toContain('falha temporária de coleta');
  });
});