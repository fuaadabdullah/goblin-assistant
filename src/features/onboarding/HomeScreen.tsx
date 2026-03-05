import Link from 'next/link';
import Navigation from '../../components/Navigation';
import { useAuthStore } from '../../store/authStore';
import { BRAND_NAME, BRAND_TAGLINE, HOME_EXAMPLE_CARDS, HOME_VALUE_PROPS } from '../../content/brand';
import Seo from '../../components/Seo';

const CustomerHome = ({ isAuthenticated }: { isAuthenticated: boolean }) => (
  <div className="min-h-screen bg-bg">
    <Seo title="Home" description={`${BRAND_NAME} — ${BRAND_TAGLINE}`} robots="index,follow" />
    <Navigation showLogout={isAuthenticated} variant="customer" />
    <div className="max-w-6xl mx-auto p-6">
      <main role="main" id="main-content" tabIndex={-1}>
        <section className="bg-surface/80 border border-border rounded-3xl p-8 mb-8 shadow-card backdrop-blur">
          <h1 className="text-4xl font-semibold text-text mb-3">{BRAND_NAME}</h1>
          <p className="text-muted mb-6 text-base">
            {BRAND_TAGLINE}
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/chat"
              className="px-4 py-2 rounded-lg bg-primary text-text-inverse font-medium shadow-glow-primary hover:brightness-110"
            >
              Open Gateway Console
            </Link>
            <Link
              href="/search"
              className="px-4 py-2 rounded-lg bg-primary/15 text-text border border-border hover:bg-primary/20 font-medium"
            >
              Audit Logs
            </Link>
            <Link
              href="/help"
              className="px-4 py-2 rounded-lg bg-surface-hover text-text border border-border hover:bg-surface-active font-medium"
            >
              Documentation
            </Link>
          </div>
        </section>

        <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr]">
          <section className="bg-surface border border-border rounded-2xl p-6 shadow-card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-text">Gateway Activity</h2>
              <Link href="/chat" className="text-sm text-primary hover:underline">
                View all
              </Link>
            </div>
            <div className="rounded-xl border border-dashed border-border p-4 text-sm text-muted">
              No routing activity yet. Start using the gateway console.
            </div>
          </section>

          <section className="bg-surface border border-border rounded-2xl p-6 shadow-card">
            <h2 className="text-lg font-semibold text-text mb-4">Platform Capabilities</h2>
            <div className="grid gap-3 md:grid-cols-2">
              {HOME_VALUE_PROPS.map((capability, idx) => (
                <div key={idx} className="rounded-xl border border-border bg-surface-hover p-4">
                  <div className="text-lg mb-2">{capability.icon}</div>
                  <div className="text-sm font-medium text-text">{capability.title}</div>
                  <div className="text-xs text-muted mt-1">{capability.body}</div>
                </div>
              ))}
            </div>
          </section>
        </div>

        <section className="mt-8">
          <h2 className="text-lg font-semibold text-text mb-4">Enterprise Use Cases</h2>
          <div className="grid gap-4 md:grid-cols-3">
            {HOME_EXAMPLE_CARDS.map(item => (
              <div
                key={item.title}
                className="bg-surface border border-border rounded-2xl p-5 hover:bg-surface-hover transition-colors shadow-card"
              >
                <div className="text-2xl mb-2">{item.icon}</div>
                <h3 className="text-base font-semibold text-text mb-2">{item.title}</h3>
                <p className="text-sm text-muted">{item.body}</p>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  </div>
);

export default function HomeScreen() {
  const isAuthenticated = useAuthStore(state => state.isAuthenticated);
  return <CustomerHome isAuthenticated={isAuthenticated} />;
}
