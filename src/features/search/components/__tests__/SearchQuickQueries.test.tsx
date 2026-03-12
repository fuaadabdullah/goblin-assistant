import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import SearchQuickQueries from '../SearchQuickQueries';

describe('SearchQuickQueries', () => {
  const queries = ['How to reset?', 'What is Goblin?', 'API docs'];
  const onSelect = jest.fn();

  beforeEach(() => jest.clearAllMocks());

  it('renders heading', () => {
    render(<SearchQuickQueries queries={queries} onSelect={onSelect} />);
    expect(screen.getByText('Quick Queries')).toBeInTheDocument();
  });

  it('renders description', () => {
    render(<SearchQuickQueries queries={queries} onSelect={onSelect} />);
    expect(screen.getByText(/Start with a suggestion/)).toBeInTheDocument();
  });

  it('renders all query buttons', () => {
    render(<SearchQuickQueries queries={queries} onSelect={onSelect} />);
    queries.forEach(q => expect(screen.getByText(q)).toBeInTheDocument());
  });

  it('calls onSelect when a query is clicked', () => {
    render(<SearchQuickQueries queries={queries} onSelect={onSelect} />);
    fireEvent.click(screen.getByText('API docs'));
    expect(onSelect).toHaveBeenCalledWith('API docs');
  });

  it('renders empty when no queries', () => {
    render(<SearchQuickQueries queries={[]} onSelect={onSelect} />);
    expect(screen.getByText('Quick Queries')).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});
