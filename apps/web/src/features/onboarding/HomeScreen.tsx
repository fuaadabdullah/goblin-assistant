import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import Navigation from '../../components/Navigation';
import { useAuthSession } from '../../hooks/api/useAuthSession';
import { BRAND_NAME, BRAND_TAGLINE, HOME_EXAMPLE_CARDS, HOME_VALUE_PROPS } from '../../content/brand';
import Seo from '../../components/Seo';
import ControlPanelHero from './ControlPanelHero';

const LIVE_DEMO_PROMPTS = [
  {
    label: 'Analyze a stock',
    prompt: 'Pull the latest data for AAPL — price, P/E, recent earnings summary, and analyst consensus.',
    response:
      'Goblin would fetch the latest market data, summarize the earnings trend, and highlight valuation risks before you even sign in.',
  },
  {
    label: 'Run some code',
    prompt: 'Open the Python sandbox and show me how to fetch stock data with yfinance.',
    response:
      'Goblin would prefill a runnable example, ready to execute in the guest sandbox with no login required.',
  },
  {
    label: 'Research a topic',
    prompt: 'Give me a concise research brief on the current state of AI regulation in the US.',
    response:
      'Goblin would turn the prompt into a focused research brief with sources, structure, and next-step follow-ups.',
  },
] as const;

const CustomerHome = ({ isAuthenticated }: { isAuthenticated: boolean }) => {
  const [selectedPromptIndex, setSelectedPromptIndex] = useState(0);
  const selectedPrompt = LIVE_DEMO_PROMPTS[selectedPromptIndex];
  const router = useRouter();

  return (
    <div className="min-h-screen bg-bg">
      <Seo title="Home" description={`${BRAND_NAME} — ${BRAND_TAGLINE}`} robots="index,follow" />
      <Navigation showLogout={isAuthenticated} variant="customer" />
      <div className="max-w-6xl mx-auto p-6">
        <main role="main" id="main-content" tabIndex={-1}>
          <ControlPanelHero />

          <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr]">
            <section className="bg-surface border border-border rounded-2xl p-6 shadow-card">
              <div className="flex items-center justify-between mb-4 gap-4">
                <div>
                  <h2 className="text-lg font-semibold text-text">Live sandbox chat</h2>
                  <p className="text-sm text-muted mt-1">No login. Rate limited. Instantly interactive.</p>
                </div>
                <Link href="/sandbox?guest=1" className="text-sm text-primary hover:underline whitespace-nowrap">
                  Open guest sandbox
                </Link>
              </div>

              <div className="grid gap-4 lg:grid-cols-[0.95fr_1.05fr]">
                <div className="space-y-3">
                  {LIVE_DEMO_PROMPTS.map((demoPrompt, index) => (
                    <button
                      key={demoPrompt.label}
                      type="button"
                      onClick={() => setSelectedPromptIndex(index)}
                      className={`w-full rounded-xl border p-4 text-left transition-colors ${
                        selectedPromptIndex === index
                          ? 'border-primary bg-primary/10'
                          : 'border-border bg-surface-hover hover:bg-surface-active'
                      }`}
                    >
                      <div className="text-sm font-semibold text-text">{demoPrompt.label}</div>
                      <div className="text-xs text-muted mt-1 line-clamp-2">{demoPrompt.prompt}</div>
                    </button>
                  ))}
                </div>

                <div className="rounded-2xl border border-border bg-bg p-5 shadow-inner">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs font-mono uppercase tracking-wide text-muted">Preview</span>
                    <span className="text-xs text-muted">Guest sandbox ready</span>
                  </div>
                  <div className="space-y-3">
                    <div className="rounded-xl bg-primary/10 border border-primary/20 p-3">
                      <div className="text-[11px] uppercase tracking-wide text-primary font-semibold mb-1">You</div>
                      <p className="text-sm text-text">{selectedPrompt.prompt}</p>
                    </div>
                    <div className="rounded-xl bg-surface border border-border p-3">
                      <div className="text-[11px] uppercase tracking-wide text-muted font-semibold mb-1">Goblin</div>
                      <p className="text-sm text-text">{selectedPrompt.response}</p>
                    </div>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Link
                      href="/sandbox?guest=1"
                      className="px-4 py-2 rounded-lg bg-primary text-text-inverse text-sm font-medium shadow-glow-primary hover:brightness-110"
                    >
                      Open this demo
                    </Link>
                    <button
                      type="button"
                      onClick={() => setSelectedPromptIndex((selectedPromptIndex + 1) % LIVE_DEMO_PROMPTS.length)}
                      className="px-4 py-2 rounded-lg bg-surface-hover text-text border border-border hover:bg-surface-active text-sm font-medium"
                    >
                      Next prompt
                    </button>
                  </div>
                </div>
              </div>
            </section>

            <section className="bg-surface border border-border rounded-2xl p-6 shadow-card">
              <h2 className="text-lg font-semibold text-text mb-4">Platform Capabilities</h2>
              <div className="grid gap-3 md:grid-cols-2">
                {HOME_VALUE_PROPS.map((capability) => (
                  <div
                    key={capability.title}
                    className="rounded-xl border border-border bg-surface-hover p-4"
                  >
                    <div className="text-lg mb-2">{capability.icon}</div>
                    <div className="text-sm font-medium text-text">{capability.title}</div>
                    <div className="text-xs text-muted mt-1">{capability.body}</div>
                  </div>
                ))}
              </div>
            </section>
          </div>

          <section className="mt-8">
            <h2 className="text-lg font-semibold text-text mb-4">Ask Goblin Anything</h2>
            <div className="flex flex-wrap gap-3">
              {HOME_EXAMPLE_CARDS.map((item) => (
                <button
                  key={item.title}
                  type="button"
                  onClick={() => void router.push(`/chat?prompt=${encodeURIComponent(
                    `${item.title} — ${item.body}`
                  )}`)}
                  className="px-4 py-2 rounded-full bg-surface-hover border border-border text-sm text-text hover:bg-surface-active shadow-glow-cta transition"
                >
                  {item.title}
                </button>
              ))}
            </div>
          </section>
        </main>
      </div>
    </div>
  );
};

export default function HomeScreen() {
  const { isAuthenticated } = useAuthSession();
  return <CustomerHome isAuthenticated={isAuthenticated} />;
}
