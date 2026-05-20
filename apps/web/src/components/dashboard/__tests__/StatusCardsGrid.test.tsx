import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

jest.mock('@/components/StatusCard', () => {
  return function MockStatusCard(props: { title: string; status: string }) {
    return <div data-testid={`status-card-${props.title}`}>{props.title}: {props.status}</div>;
  };
});

import { StatusCardsGrid } from '../StatusCardsGrid';

const makeService = (status: string, latency: number | null = 50) => ({
  status,
  latency,
});

describe('StatusCardsGrid', () => {
  const baseProps = {
    backend: makeService('healthy'),
    chroma: makeService('healthy'),
    mcp: makeService('degraded'),
    rag: makeService('unhealthy'),
    sandbox: makeService('unknown'),
  };

  it('renders all 5 status cards', () => {
    render(<StatusCardsGrid {...baseProps as any} />);
    expect(screen.getByTestId('status-card-Backend API')).toBeInTheDocument();
    expect(screen.getByTestId('status-card-Chroma')).toBeInTheDocument();
    expect(screen.getByTestId('status-card-MCP')).toBeInTheDocument();
    expect(screen.getByTestId('status-card-RAG')).toBeInTheDocument();
    expect(screen.getByTestId('status-card-Sandbox')).toBeInTheDocument();
  });

  it('maps healthy status to healthy', () => {
    render(<StatusCardsGrid {...baseProps as any} />);
    expect(screen.getByTestId('status-card-Backend API')).toHaveTextContent('healthy');
  });

  it('maps degraded status to degraded', () => {
    render(<StatusCardsGrid {...baseProps as any} />);
    expect(screen.getByTestId('status-card-MCP')).toHaveTextContent('degraded');
  });

  it('maps unhealthy status to down', () => {
    render(<StatusCardsGrid {...baseProps as any} />);
    expect(screen.getByTestId('status-card-RAG')).toHaveTextContent('down');
  });

  it('maps unknown status to unknown', () => {
    render(<StatusCardsGrid {...baseProps as any} />);
    expect(screen.getByTestId('status-card-Sandbox')).toHaveTextContent('unknown');
  });

  it('maps other status values to unknown', () => {
    const props = {
      ...baseProps,
      backend: makeService('some-other-status'),
    };
    render(<StatusCardsGrid {...props as any} />);
    expect(screen.getByTestId('status-card-Backend API')).toHaveTextContent('unknown');
  });
});
