import React from 'react';
import { render, screen } from '@testing-library/react';

jest.mock('next/head', () =>
  function MockHead({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
  }
);
jest.mock('next/router', () => ({
  useRouter: () => ({ asPath: '/test-page' }),
}));

import Seo from '../Seo';

describe('Seo', () => {
  it('renders title with Goblin Assistant suffix', () => {
    render(<Seo title="Dashboard" />);
    const titleEl = document.querySelector('title');
    expect(titleEl?.textContent).toBe('Dashboard | Goblin Assistant');
  });

  it('does not duplicate Goblin Assistant in title', () => {
    render(<Seo title="Goblin Assistant" />);
    const titleEl = document.querySelector('title');
    expect(titleEl?.textContent).toBe('Goblin Assistant');
  });

  it('renders meta description', () => {
    render(<Seo title="Test" description="My description" />);
    const meta = document.querySelector('meta[name="description"]');
    expect(meta?.getAttribute('content')).toBe('My description');
  });

  it('uses default description when not provided', () => {
    render(<Seo title="Test" />);
    const meta = document.querySelector('meta[name="description"]');
    expect(meta?.getAttribute('content')).toContain('Goblin Assistant');
  });

  it('renders canonical link', () => {
    render(<Seo title="Test" />);
    const link = document.querySelector('link[rel="canonical"]');
    expect(link?.getAttribute('href')).toContain('/test-page');
  });

  it('uses custom canonical when provided', () => {
    render(<Seo title="Test" canonical="https://example.com/custom" />);
    const link = document.querySelector('link[rel="canonical"]');
    expect(link?.getAttribute('href')).toBe('https://example.com/custom');
  });

  it('renders robots meta', () => {
    render(<Seo title="Test" robots="noindex,nofollow" />);
    const meta = document.querySelector('meta[name="robots"]');
    expect(meta?.getAttribute('content')).toBe('noindex,nofollow');
  });

  it('defaults robots to index,follow', () => {
    render(<Seo title="Test" />);
    const meta = document.querySelector('meta[name="robots"]');
    expect(meta?.getAttribute('content')).toBe('index,follow');
  });

  it('renders og:title meta', () => {
    render(<Seo title="Dashboard" />);
    const meta = document.querySelector('meta[property="og:title"]');
    expect(meta?.getAttribute('content')).toBe('Dashboard | Goblin Assistant');
  });

  it('renders twitter:card meta', () => {
    render(<Seo title="Test" />);
    const meta = document.querySelector('meta[name="twitter:card"]');
    expect(meta?.getAttribute('content')).toBe('summary_large_image');
  });

  it('renders og:image meta', () => {
    render(<Seo title="Test" />);
    const meta = document.querySelector('meta[property="og:image"]');
    expect(meta?.getAttribute('content')).toContain('/goblin-logo.png');
  });
});
