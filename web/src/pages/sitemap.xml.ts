import type { APIRoute } from 'astro';
import { TRIBUNAIS } from '../lib/tribunais';
import { loadContract } from '../lib/data';
import { topAdvogadosTribunals } from '../lib/advogadosCoverage';

export const GET: APIRoute = async ({ site }) => {
  const basePath = import.meta.env.BASE_URL.replace(/\/$/, '');
  const BASE_URL = new URL(basePath, site).toString().replace(/\/$/, '');
  const sitemapUrls: string[] = [];
  const now = new Date().toISOString();
  const advogadosTribunals = topAdvogadosTribunals(await loadContract('tribunal_coverage'));

  // Product hierarchy: primary jobs first, then continuity, advanced tools and docs.
  // /advogados and /comparador now preserve old URLs only as redirects to /stats,
  // so they are intentionally absent from indexing (#1138).
  const staticPages = [
    { url: '/', changefreq: 'daily', priority: '1.0' },
    { url: '/processo', changefreq: 'daily', priority: '0.9' },
    { url: '/publicacoes', changefreq: 'daily', priority: '0.9' },
    { url: '/minhas-consultas', changefreq: 'weekly', priority: '0.7' },
    { url: '/stats', changefreq: 'daily', priority: '0.6' },
    { url: '/explorador', changefreq: 'weekly', priority: '0.6' },
    { url: '/agentes', changefreq: 'weekly', priority: '0.6' },
    { url: '/sobre', changefreq: 'weekly', priority: '0.5' },
    { url: '/changelog', changefreq: 'weekly', priority: '0.4' },
  ];

  staticPages.forEach(page => {
    sitemapUrls.push(`
  <url>
    <loc>${BASE_URL}${page.url}</loc>
    <lastmod>${now}</lastmod>
    <changefreq>${page.changefreq}</changefreq>
    <priority>${page.priority}</priority>
  </url>
    `);
  });

  TRIBUNAIS.forEach(tribunal => {
    sitemapUrls.push(`
  <url>
    <loc>${BASE_URL}/publicacoes/${tribunal.toLowerCase()}</loc>
    <lastmod>${now}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.7</priority>
  </url>
    `);
  });

  advogadosTribunals.forEach((item) => {
    const slug = item.tribunal.toLowerCase();
    sitemapUrls.push(`
  <url>
    <loc>${BASE_URL}/advogados/${slug}</loc>
    <lastmod>${now}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.5</priority>
  </url>
    `);
  });

  const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${sitemapUrls.join('')}
</urlset>`;

  return new Response(sitemap.trim(), {
    headers: {
      'Content-Type': 'application/xml',
    },
  });
};
