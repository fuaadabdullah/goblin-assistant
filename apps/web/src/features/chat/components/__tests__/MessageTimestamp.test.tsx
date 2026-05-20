import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import MessageTimestamp from '../MessageTimestamp';

describe('MessageTimestamp', () => {
  it('renders a time element', () => {
    const { container } = render(<MessageTimestamp createdAt="2024-01-15T10:30:00Z" />);
    expect(container.querySelector('time')).toBeInTheDocument();
  });

  it('shows "Today at" for today dates', () => {
    const now = new Date();
    now.setHours(14, 30, 0, 0);
    render(<MessageTimestamp createdAt={now.toISOString()} />);
    expect(screen.getByText(/Today at/)).toBeInTheDocument();
  });

  it('shows "Yesterday at" for yesterday dates', () => {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    yesterday.setHours(9, 0, 0, 0);
    render(<MessageTimestamp createdAt={yesterday.toISOString()} />);
    expect(screen.getByText(/Yesterday at/)).toBeInTheDocument();
  });

  it('shows full date for older dates', () => {
    const { container } = render(<MessageTimestamp createdAt="2023-03-15T10:30:00Z" />);
    const timeEl = container.querySelector('time')!;
    // Should NOT contain Today or Yesterday
    expect(timeEl.textContent).not.toContain('Today');
    expect(timeEl.textContent).not.toContain('Yesterday');
    // Should contain "at" and the date portion
    expect(timeEl.textContent).toContain('at');
  });

  it('shows only time when showRelative is false', () => {
    const now = new Date();
    now.setHours(14, 30, 0, 0);
    const { container } = render(<MessageTimestamp createdAt={now.toISOString()} showRelative={false} />);
    const timeEl = container.querySelector('time')!;
    expect(timeEl.textContent).not.toContain('Today');
  });

  it('sets dateTime attribute to ISO string', () => {
    const iso = '2024-01-15T10:30:00.000Z';
    const { container } = render(<MessageTimestamp createdAt={iso} />);
    const timeEl = container.querySelector('time')!;
    expect(timeEl.getAttribute('dateTime')).toBe(new Date(iso).toISOString());
  });

  it('sets title attribute', () => {
    const { container } = render(<MessageTimestamp createdAt="2024-01-15T10:30:00Z" />);
    const timeEl = container.querySelector('time')!;
    expect(timeEl.title).toBeTruthy();
  });

  it('defaults showRelative to true', () => {
    const now = new Date();
    render(<MessageTimestamp createdAt={now.toISOString()} />);
    expect(screen.getByText(/Today at/)).toBeInTheDocument();
  });
});
