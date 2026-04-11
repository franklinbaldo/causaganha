import type { APIRoute } from 'astro';
import { TRIBUNAIS } from '../lib/tribunais';
import { readJson } from '../lib/readJson';

const BASE_URL = 'https://franklinbaldo.github.io/causaganha';

export const GET: APIRoute = () => {
  const sitemapUrls: string[] = [];
  const now = new Date().toISOString();
  const backfill = readJson<any>('cache/backfill.json');

  // Static pages
  const staticPages = [
    { url: '/', changefreq: 'daily', priority: '1.0' },
    { url: '/publicacoes', changefreq: 'daily', priority: '0.9' },
    { url: '/advogados', changefreq: 'daily', priority: '0.8' },
    { url: '/comparador', changefreq: 'daily', priority: '0.8' },
    { url: '/stats', changefreq: 'daily', priority: '0.8' },
    { url: '/consultas', changefreq: 'weekly', priority: '0.7' },
    { url: '/dicionario', changefreq: 'weekly', priority: '0.7' },
    { url: '/changelog', changefreq: 'weekly', priority: '0.6' },
    { url: '/sobre', changefreq: 'weekly', priority: '0.8' },
    { url: '/admin/quality', changefreq: 'daily', priority: '0.5' },
    { url: '/admin/backfill', changefreq: 'daily', priority: '0.5' },
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

  // Dynamic tribunal pages
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

  ((backfill?.tribunal_stats ?? []) as any[]).slice(0, 12).forEach((item) => {
    const slug = String(item.tribunal ?? '').toLowerCase();
    if (!slug) return;
    sitemapUrls.push(`
  <url>
    <loc>${BASE_URL}/advogados/${slug}</loc>
    <lastmod>${now}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.6</priority>
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
