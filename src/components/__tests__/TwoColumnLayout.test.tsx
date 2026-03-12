import React from 'react';
import { render, screen } from '@testing-library/react';

import TwoColumnLayout from '../TwoColumnLayout';

describe('TwoColumnLayout', () => {
  it('renders sidebar content', () => {
    render(
      <TwoColumnLayout sidebar={<div>Sidebar Content</div>}>
        <div>Main Content</div>
      </TwoColumnLayout>
    );
    expect(screen.getByText('Sidebar Content')).toBeInTheDocument();
  });

  it('renders main content', () => {
    render(
      <TwoColumnLayout sidebar={<div>Side</div>}>
        <div>Main Content</div>
      </TwoColumnLayout>
    );
    expect(screen.getByText('Main Content')).toBeInTheDocument();
  });

  it('renders aside element for sidebar', () => {
    const { container } = render(
      <TwoColumnLayout sidebar={<div>Side</div>}>
        <div>Main</div>
      </TwoColumnLayout>
    );
    expect(container.querySelector('aside')).toBeInTheDocument();
  });

  it('renders main element with default id', () => {
    render(
      <TwoColumnLayout sidebar={<div>Side</div>}>
        <div>Main</div>
      </TwoColumnLayout>
    );
    expect(document.getElementById('main-content')).toBeInTheDocument();
  });

  it('applies custom mainId', () => {
    render(
      <TwoColumnLayout sidebar={<div>Side</div>} mainId="custom-main">
        <div>Main</div>
      </TwoColumnLayout>
    );
    expect(document.getElementById('custom-main')).toBeInTheDocument();
  });

  it('applies aria-label to main when mainLabel provided', () => {
    render(
      <TwoColumnLayout sidebar={<div>Side</div>} mainLabel="Primary Content">
        <div>Main</div>
      </TwoColumnLayout>
    );
    expect(screen.getByLabelText('Primary Content')).toBeInTheDocument();
  });

  it('applies normal width class by default', () => {
    const { container } = render(
      <TwoColumnLayout sidebar={<div>Side</div>}>
        <div>Main</div>
      </TwoColumnLayout>
    );
    expect(container.querySelector('aside')).toHaveClass('w-64');
  });

  it('applies narrow width class', () => {
    const { container } = render(
      <TwoColumnLayout sidebar={<div>Side</div>} sidebarWidth="narrow">
        <div>Main</div>
      </TwoColumnLayout>
    );
    expect(container.querySelector('aside')).toHaveClass('w-48');
  });

  it('applies wide width class', () => {
    const { container } = render(
      <TwoColumnLayout sidebar={<div>Side</div>} sidebarWidth="wide">
        <div>Main</div>
      </TwoColumnLayout>
    );
    expect(container.querySelector('aside')).toHaveClass('w-80');
  });
});
