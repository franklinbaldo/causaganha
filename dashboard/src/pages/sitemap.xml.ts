import type { APIRoute } from 'astro';
import { TRIBUNAIS } from '../lib/tribunais';

const BASE_URL = 'https://franklinbaldo.github.io/causaganha';

export const GET: APIRoute = () => {
  const sitemapUrls = [];
  const now = new Date().toISOString();

  // Static pages
  const staticPages = [
    { url: '/', changefreq: 'daily', priority: '1.0' },
    { url: '/publicacoes', changefreq: 'daily', priority: '0.9' },
    { url: '/stats', changefreq: 'daily', priority: '0.8' },
    { url: '/sobre', changefreq: 'weekly', priority: '0.8' },
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
