import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

jest.mock('next/dynamic', () => () => {
  return function MockLottie(props: { animationData: unknown }) {
    return <div data-testid="lottie" />;
  };
});

// Mock fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

import GoblinLoader from '../GoblinLoader';

describe('GoblinLoader', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders fallback emoji initially', () => {
    mockFetch.mockReturnValue(new Promise(() => {})); // never resolves
    render(<GoblinLoader />);
    expect(screen.getByText('🧠')).toBeInTheDocument();
  });

  it('renders Lottie component after fetch succeeds', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ v: '5.0' }) });
    render(<GoblinLoader />);
    await waitFor(() => {
      expect(screen.getByTestId('lottie')).toBeInTheDocument();
    });
  });

  it('stays with fallback when fetch fails', async () => {
    mockFetch.mockRejectedValue(new Error('network error'));
    render(<GoblinLoader />);
    // Wait a tick for the catch to resolve
    await waitFor(() => {
      expect(screen.getByText('🧠')).toBeInTheDocument();
    });
  });

  it('stays with fallback when response is not ok', async () => {
    mockFetch.mockResolvedValue({ ok: false });
    render(<GoblinLoader />);
    await waitFor(() => {
      expect(screen.getByText('🧠')).toBeInTheDocument();
    });
  });

  it('applies default size of 96', () => {
    mockFetch.mockReturnValue(new Promise(() => {}));
    const { container } = render(<GoblinLoader />);
    const outerDiv = container.firstChild as HTMLElement;
    expect(outerDiv.style.width).toBe('96px');
    expect(outerDiv.style.height).toBe('96px');
  });

  it('applies custom size', () => {
    mockFetch.mockReturnValue(new Promise(() => {}));
    const { container } = render(<GoblinLoader size={200} />);
    const outerDiv = container.firstChild as HTMLElement;
    expect(outerDiv.style.width).toBe('200px');
    expect(outerDiv.style.height).toBe('200px');
  });

  it('applies custom className', () => {
    mockFetch.mockReturnValue(new Promise(() => {}));
    const { container } = render(<GoblinLoader className="my-custom" />);
    const outerDiv = container.firstChild as HTMLElement;
    expect(outerDiv.className).toContain('my-custom');
  });

  it('sets aria-hidden on container', () => {
    mockFetch.mockReturnValue(new Promise(() => {}));
    const { container } = render(<GoblinLoader />);
    const outerDiv = container.firstChild as HTMLElement;
    expect(outerDiv.getAttribute('aria-hidden')).toBe('true');
  });

  it('fetches /goblin_loader.json', () => {
    mockFetch.mockReturnValue(new Promise(() => {}));
    render(<GoblinLoader />);
    expect(mockFetch).toHaveBeenCalledWith('/goblin_loader.json');
  });
});
