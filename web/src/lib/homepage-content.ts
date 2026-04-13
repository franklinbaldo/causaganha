/**
 * Content constants for the homepage.
 * Imported by both index.astro and the BDD step file
 * so the test always validates against the real page content.
 */

export const HOW_IT_WORKS_CARDS = [
  {
    title: 'Extração Ética',
    icon: '01.',
    description: 'Nossos crawlers respeitam as políticas de cada tribunal, coletando apenas dados públicos oficiais.',
    key: 'extracao',
  },
  {
    title: 'Normalização',
    icon: '02.',
    description: 'Limpeza e estruturação dos dados em um formato JSON padronizado para facilitar o consumo.',
    key: 'normalizacao',
  },
  {
    title: 'Acesso Livre',
    icon: '03.',
    description: 'Disponibilizamos tudo via API ou downloads em massa, sem custos ou barreiras.',
    key: 'acesso',
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
  {
    title: 'Pesquisadores',
    icon: '🎓',
    description: 'Acesse séries históricas completas de publicações judiciais para análises empíricas, estudos de direito e ciência de dados.',
    key: 'pesquisadores',
  },
  {
    title: 'LegalTechs',
    icon: '⚙️',
    description: 'Integre dados abertos do Judiciário em produtos jurídicos. API pública, Parquet e DuckDB WASM prontos para uso.',
    key: 'legaltechs',
  },
  {
    title: 'Jornalistas',
    icon: '📰',
    description: 'Investigue decisões judiciais, acompanhe processos de interesse público e consulte advogados envolvidos em casos relevantes.',
    key: 'jornalistas',
  },
] as const;

export function formatNumber(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1).replace(/\.0$/, '') + 'M';
  if (n >= 1_000) return (n / 1_000).toFixed(1).replace(/\.0$/, '') + 'K';
  return n.toLocaleString('pt-BR');
}
