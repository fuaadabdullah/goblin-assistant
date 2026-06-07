import type { MetadataRoute } from 'next';

function cleanSiteUrl(value: string | undefined): string {
  const v = (value || '').trim();
  if (!v) return 'https://goblin-assistant.vercel.app';
  return v.replace(/\/$/, '');
}

export default function sitemap(): MetadataRoute.Sitemap {
  const siteUrl = cleanSiteUrl(process.env.NEXT_PUBLIC_SITE_URL);
  const now = new Date();

  // Public-only pages.
  return [
    { url: `${siteUrl}/`, lastModified: now },
    { url: `${siteUrl}/help`, lastModified: now },
  ];
}
