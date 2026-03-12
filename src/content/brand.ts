export const BRAND_NAME = 'Goblin Assistant';

export const BRAND_HEADLINE = 'The Resourceful AI Assistant';

export const BRAND_TAGLINE =
  'Finance. Code. Learning. Whatever you need — Goblin figures it out.';

export const HOME_VALUE_PROPS = [
  {
    title: 'Financial Analysis',
    body: 'Analyze stocks, build DCF models, and break down your portfolio.',
    icon: '📈',
    mode: 'finance',
  },
  {
    title: 'Code & Problem Solving',
    body: 'Run Python and JavaScript live. Debug, build, and ship faster.',
    icon: '⚡',
    mode: 'general',
  },
  {
    title: 'Learn Anything',
    body: 'Get clear explanations, worked examples, and concept breakdowns.',
    icon: '🎓',
    mode: 'education',
  },
  {
    title: 'Smart Memory',
    body: 'Goblin remembers your context, preferences, and ongoing work.',
    icon: '🧠',
    mode: 'general',
  },
  {
    title: 'Research & Writing',
    body: 'Summarize documents, draft content, and synthesize information.',
    icon: '📋',
    mode: 'general',
  },
  {
    title: 'Multi-Model Routing',
    body: 'Always picks the best AI for your task. No model switching needed.',
    icon: '🔀',
    mode: 'general',
  },
] as const;

export const HOME_EXAMPLE_CARDS = [
  {
    title: 'Analyze NVDA earnings',
    body: 'Pull financials, summarize the latest call, and flag analyst concerns.',
    icon: '📊',
    mode: 'finance',
  },
  {
    title: 'Explain this concept',
    body: 'Break down compound interest, recursion, or the Black-Scholes model.',
    icon: '🎓',
    mode: 'education',
  },
  {
    title: 'Run Python live',
    body: 'Write and execute code directly in the chat. No setup needed.',
    icon: '⚡',
    mode: 'general',
  },
] as const;

export const CHAT_COMPOSER_PLACEHOLDER =
  'Ask anything — finance, code, research, or learning...';

export const CHAT_COMPOSER_TIP =
  'Try: "Analyze AAPL", "Explain recursion with examples", "Debug this Python code"';

// Mode-specific quick prompts
export const CHAT_QUICK_PROMPTS_FINANCE = [
  {
    label: 'Analyze a stock',
    prompt:
      'Pull the latest data for AAPL — price, P/E, recent earnings summary, and analyst consensus.',
  },
  {
    label: 'Build a DCF',
    prompt: 'Walk me through a simple DCF model for MSFT with realistic assumptions.',
  },
  {
    label: 'Portfolio check',
    prompt:
      "Analyze my portfolio risk. I'll paste my holdings — give me sector exposure and Sharpe ratio.",
  },
  {
    label: 'Earnings summary',
    prompt: 'Summarize the most recent NVDA earnings call. Key beats, misses, and guidance.',
  },
] as const;

export const CHAT_QUICK_PROMPTS_GENERAL = [
  {
    label: 'Run some code',
    prompt: 'Open the Python sandbox and show me how to fetch stock data with yfinance.',
  },
  {
    label: 'Summarize a doc',
    prompt: "I'll paste a document — summarize it and pull out the key action items.",
  },
  {
    label: 'Draft something',
    prompt: 'Help me write a professional email explaining a project delay to stakeholders.',
  },
  {
    label: 'Research a topic',
    prompt: 'Give me a concise research brief on the current state of AI regulation in the US.',
  },
] as const;

export const CHAT_QUICK_PROMPTS_EDUCATION = [
  {
    label: 'Explain a concept',
    prompt:
      'Explain present value and discounted cash flow like I understand basic math but not finance.',
  },
  {
    label: 'Worked example',
    prompt: 'Walk me through a worked example of calculating WACC from scratch with real numbers.',
  },
  {
    label: 'Quiz me',
    prompt:
      'Quiz me on corporate finance fundamentals. Start easy and get harder. Tell me when I get things wrong.',
  },
  {
    label: 'Study plan',
    prompt:
      "I'm studying for the CFA Level 1. Give me a 4-week study plan focused on my weakest areas.",
  },
] as const;

// Default shown on load — one from each mode
export const CHAT_QUICK_PROMPTS = [
  CHAT_QUICK_PROMPTS_FINANCE[0],
  CHAT_QUICK_PROMPTS_EDUCATION[0],
  CHAT_QUICK_PROMPTS_GENERAL[0],
  CHAT_QUICK_PROMPTS_FINANCE[1],
] as const;

export const SEARCH_QUICK_QUERIES = [
  'AAPL valuation analysis',
  'Explain Black-Scholes model',
  'Python pandas tutorial',
  'Portfolio risk metrics',
] as const;
