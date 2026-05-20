'use client';

import { useState, useCallback, Children, isValidElement } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import type { Components } from 'react-markdown';
import { Copy, Check } from 'lucide-react';

interface MessageMarkdownProps {
  content: string;
  className?: string;
  inverse?: boolean;
}

const LANGUAGE_NAMES: Record<string, string> = {
  js: 'JavaScript', jsx: 'JSX', ts: 'TypeScript', tsx: 'TSX',
  py: 'Python', python: 'Python', rb: 'Ruby', go: 'Go', rs: 'Rust',
  java: 'Java', cpp: 'C++', c: 'C', cs: 'C#', php: 'PHP',
  swift: 'Swift', kotlin: 'Kotlin', sql: 'SQL',
  html: 'HTML', css: 'CSS', scss: 'SCSS',
  json: 'JSON', yaml: 'YAML', yml: 'YAML', xml: 'XML',
  md: 'Markdown', markdown: 'Markdown',
  bash: 'Bash', sh: 'Shell', shell: 'Shell', zsh: 'Zsh',
  powershell: 'PowerShell', dockerfile: 'Dockerfile',
  graphql: 'GraphQL', toml: 'TOML', ini: 'INI',
};

function extractLanguage(children: React.ReactNode): string | null {
  const child = Children.toArray(children)[0];
  if (!isValidElement(child)) return null;
  const className = (child.props as { className?: string }).className ?? '';
  const match = className.match(/language-(\w+)/);
  return match ? match[1] : null;
}

function extractText(node: React.ReactNode): string {
  if (typeof node === 'string') return node;
  if (typeof node === 'number') return String(node);
  if (!isValidElement(node)) return '';
  const children = (node.props as { children?: React.ReactNode }).children;
  return Children.toArray(children).map(extractText).join('');
}

function CodeBlock({ children, inverse }: { children: React.ReactNode; inverse: boolean }) {
  const [copied, setCopied] = useState(false);

  const lang = extractLanguage(children);
  const displayLang = lang ? (LANGUAGE_NAMES[lang] ?? lang) : null;

  const handleCopy = useCallback(() => {
    const text = extractText(children);
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [children]);

  const wrapperClassName = inverse
    ? 'my-3 rounded-xl border border-white/20 bg-black/40 text-sm'
    : 'my-3 rounded-xl border border-border bg-bg/80 text-sm';

  return (
    <div className={`relative group/code ${wrapperClassName}`}>
      <div className={`flex items-center justify-between px-3 py-1.5 border-b ${inverse ? 'border-white/10' : 'border-border/50'} text-xs text-muted`}>
        <span className="font-mono select-none">{displayLang ?? 'Code'}</span>
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1 px-1.5 py-0.5 rounded hover:bg-surface-hover transition-colors text-muted hover:text-text"
          aria-label={copied ? 'Copied' : 'Copy code'}
        >
          {copied ? (
            <>
              <Check size={14} className="text-success" />
              <span className="text-success">Copied!</span>
            </>
          ) : (
            <>
              <Copy size={14} />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      <pre className="p-3 overflow-x-auto">{children}</pre>
    </div>
  );
}

const getComponents = (inverse: boolean): Components => ({
  code({ className, children, ...props }) {
    const hasLanguage = /language-\w+/.test(className ?? '');
    if (hasLanguage) {
      return (
        <code className={className} {...props}>
          {children}
        </code>
      );
    }

    const inlineClassName = inverse
      ? 'rounded-md bg-black/30 px-1.5 py-0.5 font-mono text-[0.92em] text-text-inverse'
      : 'rounded-md bg-surface-hover px-1.5 py-0.5 font-mono text-[0.92em]';

    return (
      <code className={inlineClassName} {...props}>
        {children}
      </code>
    );
  },
  pre({ children }) {
    return <CodeBlock inverse={inverse}>{children}</CodeBlock>;
  },
  a({ href, children, ...props }) {
    const isHashLink = href?.startsWith('#');
    const linkClassName = inverse
      ? 'underline underline-offset-2 break-all decoration-text-inverse/60'
      : 'text-primary underline underline-offset-2 hover:opacity-90 break-all';

    return (
      <a
        href={href}
        target={isHashLink ? undefined : '_blank'}
        rel={isHashLink ? undefined : 'noreferrer'}
        className={linkClassName}
        {...props}
      >
        {children}
      </a>
    );
  },
  table({ children }) {
    return (
      <div className="my-3 overflow-x-auto">
        <table className="w-full border-collapse text-sm">{children}</table>
      </div>
    );
  },
  th({ children }) {
    return (
      <th className="border border-border bg-surface-hover px-2 py-1 text-left font-semibold">
        {children}
      </th>
    );
  },
  td({ children }) {
    return <td className="border border-border px-2 py-1 align-top">{children}</td>;
  },
});

const MessageMarkdown = ({ content, className, inverse = false }: MessageMarkdownProps) => {
  return (
    <div className={`chat-markdown break-words ${className ?? ''}`.trim()}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={getComponents(inverse)}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};

export default MessageMarkdown;
