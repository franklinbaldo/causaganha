import type { APIRoute } from 'astro';

export const GET: APIRoute = ({ site }) => {
  const sitemapUrl = new URL(`${import.meta.env.BASE_URL.replace(/\/$/, '')}/sitemap.xml`, site).toString();
  const robotsTxt = `User-agent: *\nAllow: /\nSitemap: ${sitemapUrl}\n`;
  return new Response(robotsTxt, {
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
    },
  });
};
