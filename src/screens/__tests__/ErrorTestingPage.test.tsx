import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

jest.mock('@/components/ErrorTestingPanel', () => ({
  ErrorTestingPanel: () => <div data-testid="panel">panel</div>,
}));

jest.mock('@/layout/AdminLayout', () => {
  return function MockAdminLayout({ children, mainId, mainLabel }: { children: React.ReactNode; mainId: string; mainLabel: string }) {
    return <main id={mainId} aria-label={mainLabel}>{children}</main>;
  };
});

jest.mock('@/components/Seo', () => {
  return function MockSeo(props: { title: string }) {
    return <div data-testid="seo">{props.title}</div>;
  };
});

import ErrorTestingPage from '../ErrorTestingPage';

describe('ErrorTestingPage', () => {
  it('renders the heading', () => {
    render(<ErrorTestingPage />);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/Error Testing/);
  });

  it('renders the Seo component', () => {
    render(<ErrorTestingPage />);
    expect(screen.getByTestId('seo')).toHaveTextContent('Error Testing');
  });

  it('renders the error testing panel', () => {
    render(<ErrorTestingPage />);
    expect(screen.getByTestId('panel')).toBeInTheDocument();
  });

  it('uses AdminLayout', () => {
    render(<ErrorTestingPage />);
    expect(document.getElementById('main-content')).toBeInTheDocument();
  });

  it('renders description text', () => {
    render(<ErrorTestingPage />);
    expect(screen.getByText(/Test Sentry error tracking/)).toBeInTheDocument();
  });
});
