import React from 'react';
import { render, screen } from '@testing-library/react';

import Sparkline from '../Sparkline';

describe('Sparkline', () => {
  it('renders svg with default dimensions', () => {
    const { container } = render(<Sparkline data={[1, 2, 3]} />);
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
    expect(svg).toHaveAttribute('width', '100');
    expect(svg).toHaveAttribute('height', '30');
  });

  it('renders svg with custom dimensions', () => {
    const { container } = render(<Sparkline data={[1, 2, 3]} width={200} height={50} />);
    const svg = container.querySelector('svg');
    expect(svg).toHaveAttribute('width', '200');
    expect(svg).toHaveAttribute('height', '50');
  });

  it('renders no data message when data is empty', () => {
    render(<Sparkline data={[]} />);
    expect(screen.getByText('No data')).toBeInTheDocument();
  });

  it('renders no data message when data is undefined', () => {
    render(<Sparkline data={undefined as unknown as number[]} />);
    expect(screen.getByText('No data')).toBeInTheDocument();
  });

  it('renders line path', () => {
    const { container } = render(<Sparkline data={[10, 20, 30]} />);
    const paths = container.querySelectorAll('path');
    expect(paths.length).toBeGreaterThan(0);
    const linePath = Array.from(paths).find((p) => p.getAttribute('fill') === 'none');
    expect(linePath).toBeInTheDocument();
    expect(linePath?.getAttribute('d')).toContain('M');
  });

  it('renders fill area when showFill is true', () => {
    const { container } = render(<Sparkline data={[10, 20, 30]} showFill />);
    const paths = container.querySelectorAll('path');
    const fillPath = Array.from(paths).find((p) => p.getAttribute('fill-opacity') === '0.2');
    expect(fillPath).toBeInTheDocument();
  });

  it('does not render fill area by default', () => {
    const { container } = render(<Sparkline data={[10, 20, 30]} />);
    const paths = container.querySelectorAll('path');
    const fillPath = Array.from(paths).find((p) => p.getAttribute('fill-opacity') === '0.2');
    expect(fillPath).not.toBeTruthy();
  });

  it('uses custom color for stroke', () => {
    const { container } = render(<Sparkline data={[10, 20, 30]} color="red" />);
    const linePath = container.querySelector('path[fill="none"]');
    expect(linePath).toHaveAttribute('stroke', 'red');
  });

  it('applies custom className', () => {
    const { container } = render(<Sparkline data={[10, 20]} className="my-class" />);
    expect(container.querySelector('svg.my-class')).toBeInTheDocument();
  });

  it('handles single data point', () => {
    const { container } = render(<Sparkline data={[5]} />);
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('handles uniform data', () => {
    const { container } = render(<Sparkline data={[5, 5, 5]} />);
    const path = container.querySelector('path[fill="none"]');
    expect(path?.getAttribute('d')).toBeDefined();
  });
});
