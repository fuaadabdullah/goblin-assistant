import Link from 'next/link';
import { useRouter } from 'next/router';

export default function NotFoundPage() {
  const router = useRouter();

  return (
    <div className="min-h-[70vh] flex items-center justify-center px-6 py-16">
      <div className="max-w-lg text-center space-y-4">
        <div className="text-5xl">🧭</div>
        <h1 className="text-3xl font-semibold text-text">Page not found</h1>
        <p className="text-muted">
          We couldn't find <span className="text-text">{router.asPath}</span>. Check the
          address or jump back to a known page.
        </p>
        <div className="flex flex-wrap justify-center gap-3">
          <Link
            href="/"
            className="px-4 py-2 rounded-lg bg-primary text-text-inverse font-medium shadow-glow-primary"
          >
            Back to Home
          </Link>
          <Link
            href="/chat"
            className="px-4 py-2 rounded-lg border border-border text-text hover:bg-surface-hover"
          >
            Go to Chat
          </Link>
        </div>
      </div>
    </div>
  );
}

// Prevent static generation
export const getServerSideProps = async () => {
  return { props: {} };
};
