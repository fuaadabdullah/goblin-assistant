import type { GetServerSideProps } from 'next';

function cleanSiteUrl(value: string | undefined): string {
  const v = (value || '').trim();
  if (!v) return 'https://goblin-assistant.vercel.app';
  return v.replace(/\/$/, '');
}

function buildUrlset(urls: Array<{ loc: string; lastmod?: string }>): string {
  const lines = urls
    .map(u => {
      const lastmod = u.lastmod ? `<lastmod>${u.lastmod}</lastmod>` : '';
      return `<url><loc>${u.loc}</loc>${lastmod}</url>`;
    })
    .join('');
  return `<?xml version="1.0" encoding="UTF-8"?>` +
    `<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${lines}</urlset>`;
}

export const getServerSideProps: GetServerSideProps = async ({ res }) => {
  const siteUrl = cleanSiteUrl(process.env.NEXT_PUBLIC_SITE_URL);
  const now = new Date().toISOString();

  // Public-only pages.
  const urls = [
    { loc: `${siteUrl}/`, lastmod: now },
    { loc: `${siteUrl}/help`, lastmod: now },
  ];

  const xml = buildUrlset(urls);

  res.setHeader('Content-Type', 'application/xml; charset=utf-8');
  res.setHeader('Cache-Control', 'public, max-age=600, stale-while-revalidate=86400');
  res.write(xml);
  res.end();

  return { props: {} };
};

export default function SitemapXml() {
  return null;
}

