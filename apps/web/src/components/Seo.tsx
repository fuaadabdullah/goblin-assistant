import Head from 'next/head';
import { useRouter } from 'next/router';

interface SeoProps {
  title: string;
  description?: string;
  canonical?: string;
  robots?: string; // e.g. "index,follow" or "noindex,nofollow"
  ogImagePath?: string; // absolute or site-relative
}

const DEFAULT_DESCRIPTION =
  'Goblin Assistant – AI Gateway & Orchestration Platform. Multi-LLM routing, cost optimization, reliability, observability, security. Companies plug in once and never worry about LLM outages, costs, or vendor lock-in again.';

function cleanSiteUrl(value: string | undefined): string {
  const v = (value || '').trim();
  if (!v) return 'https://goblin-assistant.vercel.app';
  return v.replace(/\/$/, '');
}

function toAbsoluteUrl(siteUrl: string, maybePath: string): string {
  if (/^https?:\/\//i.test(maybePath)) return maybePath;
  const path = maybePath.startsWith('/') ? maybePath : `/${maybePath}`;
  return `${siteUrl}${path}`;
}

export default function Seo({
  title,
  description,
  canonical,
  robots = 'index,follow',
  ogImagePath = '/goblin-logo.png',
}: SeoProps) {
  const router = useRouter();
  const siteUrl = cleanSiteUrl(process.env.NEXT_PUBLIC_SITE_URL);
  const desc = description || DEFAULT_DESCRIPTION;

  const canonicalUrl =
    canonical ||
    toAbsoluteUrl(siteUrl, (router.asPath || '/').split('#')[0].split('?')[0] || '/');

  const ogImageUrl = toAbsoluteUrl(siteUrl, ogImagePath);

  const fullTitle = title.includes('Goblin Assistant') ? title : `${title} | Goblin Assistant`;

  return (
    <Head>
      <title>{fullTitle}</title>
      <meta name="description" content={desc} />
      <link rel="canonical" href={canonicalUrl} />

      <meta name="robots" content={robots} />

      <meta property="og:site_name" content="Goblin Assistant" />
      <meta property="og:title" content={fullTitle} />
      <meta property="og:description" content={desc} />
      <meta property="og:url" content={canonicalUrl} />
      <meta property="og:type" content="website" />
      <meta property="og:image" content={ogImageUrl} />

      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={fullTitle} />
      <meta name="twitter:description" content={desc} />
      <meta name="twitter:image" content={ogImageUrl} />
    </Head>
  );
}

