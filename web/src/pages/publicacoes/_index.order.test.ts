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
  it('renders the search action before the coverage/gaps explanation', () => {
    const searchIndex = indexOfOrThrow('<PublicationSearch');
    const coverageIndex = indexOfOrThrow('Cobertura e lacunas por tribunal');

    expect(searchIndex).toBeLessThan(coverageIndex);
  });

  it('keeps the search action immediately after the page header, with no attention-card in between', () => {
    const headerIndex = indexOfOrThrow('class="page-head"');
    const searchIndex = indexOfOrThrow('<PublicationSearch');
    const attentionCardIndex = pageSource.indexOf('attention-card');

    expect(headerIndex).toBeLessThan(searchIndex);
    expect(attentionCardIndex === -1 || attentionCardIndex > searchIndex).toBe(true);
  });

  it('still distinguishes official absence, pending backfill, and transient failure', () => {
    expect(pageSource).toContain('ausência oficial do diário');
    expect(pageSource).toContain('backfill pendente');
    expect(pageSource).toContain('falha temporária de coleta');
  });
});
