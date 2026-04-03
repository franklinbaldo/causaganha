/**
 * Content constants for the homepage.
 * Imported by both index.astro and the BDD step file
 * so the test always validates against the real page content.
 */

export const HOW_IT_WORKS_CARDS = [
  { title: '1. Coleta Automatica', key: 'coleta' },
  { title: '2. Arquivo Permanente', key: 'arquivo' },
  { title: '3. Catalogo Indexado', key: 'catalogo' },
] as const;

export const AUDIENCE_CARDS = [
  { title: 'Pesquisadores', key: 'pesquisadores' },
  { title: 'LegalTechs', key: 'legaltechs' },
  { title: 'Jornalistas', key: 'jornalistas' },
] as const;

export function formatNumber(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1).replace(/\.0$/, '') + 'M';
  if (n >= 1_000) return (n / 1_000).toFixed(1).replace(/\.0$/, '') + 'K';
  return n.toLocaleString('pt-BR');
}
