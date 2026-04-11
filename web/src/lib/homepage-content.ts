/**
 * Content constants for the homepage.
 * Imported by both index.astro and the BDD step file
 * so the test always validates against the real page content.
 */

export const HOW_IT_WORKS_CARDS = [
  {
    title: 'Coleta Automática',
    icon: '⚡',
    description: 'A cada 20 minutos, o GitHub Actions coleta publicações do DJEN de todos os tribunais brasileiros via proxy dedicado.',
    key: 'coleta',
  },
  {
    title: 'Arquivo Permanente',
    icon: '🗄️',
    description: 'Cada ZIP é enviado ao Internet Archive, garantindo acesso público permanente e preservação histórica dos dados.',
    key: 'arquivo',
  },
  {
    title: 'Catálogo Indexado',
    icon: '🔍',
    description: 'Um catálogo em Parquet é gerado automaticamente, permitindo consultas rápidas via DuckDB direto no navegador.',
    key: 'catalogo',
  },
] as const;

export const QUICK_ACCESS_CARDS = [
  {
    title: 'Publicações',
    icon: '📋',
    description: 'Busque publicações judiciais por OAB, número de processo, nome da parte ou texto livre. Dados ao vivo do DJEN.',
    cta: 'Buscar publicações',
    href: 'publicacoes',
    key: 'publicacoes',
  },
  {
    title: 'Advogados / OAB',
    icon: '⚖️',
    description: 'Explore a cobertura por tribunal e consulte dados de advogados extraídos das publicações arquivadas.',
    cta: 'Ver advogados',
    href: 'advogados',
    key: 'advogados',
  },
  {
    title: 'Explorador SQL',
    icon: '💾',
    description: 'Consulte os dados diretamente no navegador usando DuckDB WASM. Sem servidor, sem cadastro, sem limites.',
    cta: 'Abrir explorador',
    href: 'explorador',
    key: 'explorador',
  },
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
