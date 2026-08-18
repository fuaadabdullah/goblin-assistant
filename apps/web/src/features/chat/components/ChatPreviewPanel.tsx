import Link from 'next/link';
import { Input } from '../../../components/ui/input';

const ChatPreviewPanel = () => {
  const loginHref = { pathname: '/login' };
  const samplePrompt =
    "Hey Goblin, can you summarize last quarter's revenue and flag anything surprising?";
  const loginWithPrompt = (prompt: string) => ({
    pathname: '/login',
    query: { from: `/chat?prompt=${encodeURIComponent(prompt)}` },
  });

  return (
    <div className="flex flex-col h-full">
      <div className="space-y-4">
        <div className="text-xs text-muted">Goblin • demo preview</div>
        <div className="space-y-3">
          <div className="text-xs uppercase tracking-wide text-muted">You</div>
          <div className="max-w-[80%] text-right ml-auto">
            <Link
              href={loginWithPrompt(samplePrompt)}
              aria-label="Sign in to continue this conversation"
            >
              <div className="rounded-2xl px-4 py-3 bg-primary text-text-inverse shadow-glow-primary text-sm">
                {samplePrompt}
              </div>
            </Link>
          </div>

          <div className="text-xs uppercase tracking-wide text-muted">Assistant</div>
          <div className="max-w-[80%]">
            <Link
              href={loginWithPrompt(samplePrompt)}
              aria-label="Sign in to continue this conversation"
            >
              <div className="rounded-2xl px-4 py-3 bg-surface text-text border border-border shadow-card text-sm">
                Sure — here's a quick summary: revenue up 12% YoY, gross margin improved by 3 pts.
              </div>
            </Link>
          </div>

          <div className="max-w-[80%]">
            <div className="rounded-2xl px-4 py-3 bg-surface text-text border border-border shadow-card text-sm flex items-center gap-2">
              <span className="inline-block w-3 h-3 rounded-full bg-muted/60" aria-hidden />
              <span className="typing-dots inline-flex items-center" aria-hidden>
                <span className="dot" />
                <span className="dot" />
                <span className="dot" />
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-6">
        <div className="text-sm text-muted">Preview features</div>
        <div className="mt-3 flex flex-wrap gap-2">
          <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface-hover text-sm">
            Finance analysis
          </span>
          <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface-hover text-sm">
            Live code
          </span>
          <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface-hover text-sm">
            Smart memory
          </span>
        </div>
      </div>

      <div className="mt-auto pt-6">
        <div className="text-sm text-muted">
          This preview is static — sign in to continue the conversation.
        </div>
        <div className="mt-3">
          <Input placeholder="Sign in to continue this conversation..." disabled />
        </div>
        <div className="mt-3 grid grid-cols-1 gap-2">
          <Link
            href={loginHref}
            className="inline-flex items-center justify-center px-4 py-2 rounded-lg bg-primary text-text-inverse font-medium"
          >
            Sign in to Goblin →
          </Link>
          <Link
            href={{ pathname: '/login', query: { mode: 'register' } }}
            className="inline-flex items-center justify-center px-4 py-2 rounded-lg border border-primary text-primary font-medium"
          >
            Create account
          </Link>
        </div>
      </div>
    </div>
  );
};

export default ChatPreviewPanel;
