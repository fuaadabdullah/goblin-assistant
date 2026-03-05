import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from '@jest/globals';
import { ModularCard, formatTitle } from './index';

describe('ModularCard', () => {
  it('formats the title and renders content correctly', () => {
    render(<ModularCard title="  Hello   World! " content="This is content" />);
    expect(screen.getByText('Hello World')).toBeInTheDocument();
    expect(screen.getByText('This is content')).toBeInTheDocument();
  });

  it('formatTitle util removes extra whitespace and punctuation', () => {
    expect(formatTitle('  A   Title!?  ')).toBe('A Title');
  });
});
