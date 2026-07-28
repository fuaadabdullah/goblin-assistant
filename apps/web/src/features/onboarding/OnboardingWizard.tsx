'use client';

import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { CheckCircle2, MessageSquare, Search, Settings, SkipForward } from 'lucide-react';
import Seo from '../../components/Seo';
import { Badge, Button, Card } from '../../components/ui';
import { useProviderSettings } from '../../hooks/api/useSettings';

type OnboardingStepId = 'provider-setup' | 'first-chat' | 'search-demo';

interface OnboardingStep {
  id: OnboardingStepId;
  title: string;
  description: string;
}

const ONBOARDING_STORAGE_KEY = 'goblinos-onboarding-complete';

const STEPS: OnboardingStep[] = [
  {
    id: 'provider-setup',
    title: 'Provider setup',
    description: 'Confirm at least one provider is configured before routing work.',
  },
  {
    id: 'first-chat',
    title: 'First chat',
    description: 'Pick a starter prompt and continue in the chat console.',
  },
  {
    id: 'search-demo',
    title: 'Search demo',
    description: 'Preview how global search helps recover prior work.',
  },
];

const STARTER_PROMPTS = [
  'Summarize my current workspace and suggest the next engineering task.',
  'Compare provider options for a cost-sensitive coding workflow.',
  'Create a concise research brief from my recent project context.',
];

const OnboardingWizard = () => {
  const router = useRouter();
  const [activeStep, setActiveStep] = React.useState<OnboardingStepId>('provider-setup');
  const [selectedPrompt, setSelectedPrompt] = React.useState(STARTER_PROMPTS[0]);
  const { data: providers } = useProviderSettings();

  const providerRows = Array.isArray(providers) ? providers : [];
  const configuredCount = providerRows.filter((provider) =>
    Boolean(provider.enabled ?? provider.api_key)
  ).length;

  const completeOnboarding = async () => {
    try {
      localStorage.setItem(ONBOARDING_STORAGE_KEY, 'true');
    } catch {
      // localStorage can be unavailable in hardened browser modes.
    }
    router.push('/');
  };

  const activeIndex = STEPS.findIndex((step) => step.id === activeStep);
  const nextStep = STEPS[Math.min(activeIndex + 1, STEPS.length - 1)]?.id;
  const previousStep = STEPS[Math.max(activeIndex - 1, 0)]?.id;

  return (
    <div className="min-h-screen bg-bg px-4 py-10 text-text">
      <Seo title="Onboarding" description="Set up Goblin Assistant." robots="noindex,nofollow" />
      <main className="mx-auto max-w-5xl" id="main-content" tabIndex={-1} aria-label="Onboarding">
        <header className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-primary">First-run setup</h1>
            <p className="mt-2 text-sm text-muted">
              Configure providers, start a first chat, and try search in one pass.
            </p>
          </div>
          <Button
            variant="ghost"
            size="sm"
            icon={<SkipForward className="h-4 w-4" />}
            onClick={completeOnboarding}
          >
            Skip
          </Button>
        </header>

        <div className="mb-6 grid gap-2 md:grid-cols-3">
          {STEPS.map((step, index) => (
            <button
              key={step.id}
              type="button"
              onClick={() => setActiveStep(step.id)}
              className={`rounded-md border p-4 text-left transition-colors ${
                activeStep === step.id
                  ? 'border-primary bg-primary/10'
                  : 'border-border bg-surface hover:bg-surface-hover'
              }`}
            >
              <div className="text-xs font-semibold uppercase text-muted">Step {index + 1}</div>
              <div className="mt-1 font-semibold text-text">{step.title}</div>
              <p className="mt-1 text-sm text-muted">{step.description}</p>
            </button>
          ))}
        </div>

        <Card variant="default" padding="lg" className="shadow-card">
          {activeStep === 'provider-setup' && (
            <section>
              <div className="mb-5 flex items-start gap-3">
                <Settings className="mt-1 h-6 w-6 text-primary" aria-hidden="true" />
                <div>
                  <h2 className="text-xl font-semibold text-text">Provider setup</h2>
                  <p className="mt-1 text-sm text-muted">
                    {configuredCount > 0
                      ? `${configuredCount} provider${configuredCount === 1 ? '' : 's'} ready for use.`
                      : 'No configured providers detected yet.'}
                  </p>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge variant={configuredCount > 0 ? 'success' : 'warning'}>
                  {configuredCount > 0 ? 'Provider ready' : 'Setup needed'}
                </Badge>
                <Badge variant="neutral">{providerRows.length} providers found</Badge>
              </div>
              <div className="mt-6 flex flex-wrap gap-3">
                <Link
                  href="/settings"
                  className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-semibold text-text-inverse"
                >
                  Open Settings
                </Link>
                <Button variant="secondary" onClick={() => setActiveStep('first-chat')}>
                  Continue
                </Button>
              </div>
            </section>
          )}

          {activeStep === 'first-chat' && (
            <section>
              <div className="mb-5 flex items-start gap-3">
                <MessageSquare className="mt-1 h-6 w-6 text-primary" aria-hidden="true" />
                <div>
                  <h2 className="text-xl font-semibold text-text">First chat</h2>
                  <p className="mt-1 text-sm text-muted">
                    Choose a starter prompt for the chat console.
                  </p>
                </div>
              </div>
              <div className="grid gap-2">
                {STARTER_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => setSelectedPrompt(prompt)}
                    className={`rounded-md border p-3 text-left text-sm transition-colors ${
                      selectedPrompt === prompt
                        ? 'border-primary bg-primary/10 text-text'
                        : 'border-border bg-bg text-muted hover:bg-surface-hover hover:text-text'
                    }`}
                  >
                    {prompt}
                  </button>
                ))}
              </div>
              <div className="mt-6 flex flex-wrap gap-3">
                <Link
                  href={`/chat?prompt=${encodeURIComponent(selectedPrompt ?? '')}`}
                  className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-semibold text-text-inverse"
                >
                  Start chat
                </Link>
                <Button variant="secondary" onClick={() => setActiveStep('search-demo')}>
                  Continue
                </Button>
              </div>
            </section>
          )}

          {activeStep === 'search-demo' && (
            <section>
              <div className="mb-5 flex items-start gap-3">
                <Search className="mt-1 h-6 w-6 text-primary" aria-hidden="true" />
                <div>
                  <h2 className="text-xl font-semibold text-text">Search demo</h2>
                  <p className="mt-1 text-sm text-muted">
                    Search can recover provider decisions, chats, and indexed project material.
                  </p>
                </div>
              </div>
              <div className="rounded-md border border-border bg-bg p-4">
                <div className="text-xs font-semibold uppercase text-muted">Example query</div>
                <p className="mt-2 text-sm text-text">
                  provider routing decisions from the last incident
                </p>
              </div>
              <div className="mt-6 flex flex-wrap gap-3">
                <Link
                  href="/search"
                  className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-semibold text-text-inverse"
                >
                  Open Search
                </Link>
                <Button icon={<CheckCircle2 className="h-4 w-4" />} onClick={completeOnboarding}>
                  Complete
                </Button>
              </div>
            </section>
          )}
        </Card>

        <footer className="mt-6 flex items-center justify-between">
          <Button
            variant="ghost"
            disabled={activeStep === STEPS[0]!.id}
            onClick={() => previousStep && setActiveStep(previousStep)}
          >
            Back
          </Button>
          <Button
            variant="secondary"
            disabled={activeStep === STEPS[STEPS.length - 1]!.id}
            onClick={() => nextStep && setActiveStep(nextStep)}
          >
            Next
          </Button>
        </footer>
      </main>
    </div>
  );
};

export default OnboardingWizard;
