import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import Divider from '../Divider';

describe('Divider', () => {
  it('renders default "Or" text', () => {
    render(<Divider />);
    expect(screen.getByText('Or')).toBeInTheDocument();
  });

  it('renders custom text', () => {
    render(<Divider text="Continue with" />);
    expect(screen.getByText('Continue with')).toBeInTheDocument();
  });

  it('renders the horizontal line', () => {
    const { container } = render(<Divider />);
    expect(container.querySelector('.border-t')).toBeInTheDocument();
  });
});
