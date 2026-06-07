import React from 'react';
import { render, screen } from '@testing-library/react';
import ModularCard from '../modular/ModularCard';

describe('ModularCard', () => {
  it('renders the formatted title', () => {
    render(<ModularCard title="  Hello World  " content="Some content" />);
    expect(screen.getByText('Hello World')).toBeInTheDocument();
  });

  it('renders the content', () => {
    render(<ModularCard title="Test" content="This is the card content" />);
    expect(screen.getByText('This is the card content')).toBeInTheDocument();
  });

  it('renders title inside an h4 element', () => {
    render(<ModularCard title="Card Title" content="Content" />);
    const heading = screen.getByText('Card Title');
    expect(heading.tagName).toBe('H4');
    expect(heading.className).toContain('modular-card-title');
  });

  it('has the modular-card class on the container', () => {
    const { container } = render(<ModularCard title="Title" content="Content" />);
    expect(container.firstChild).toHaveClass('modular-card');
  });

  it('strips special characters from title formatting', () => {
    render(<ModularCard title="Hello @#$ World" content="Content" />);
    // formatTitle: trim -> collapse spaces -> remove non-word chars -> "Hello  World" (two spaces)
    const heading = screen.getByRole('heading');
    expect(heading).toBeInTheDocument();
    expect(heading.textContent).toBe('Hello  World');
  });
});
