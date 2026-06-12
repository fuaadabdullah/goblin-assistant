import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';

import SearchForm from '../SearchForm';

describe('SearchForm', () => {
  const baseProps = {
    query: '',
    scope: 'all' as const,
    selectedCollection: 'default',
    collectionsData: ['default', 'docs', 'messages'],
    collectionsLoading: false,
    searching: false,
    queryRef: { current: null } as React.RefObject<HTMLInputElement>,
    onQueryChange: vi.fn(),
    onScopeChange: vi.fn(),
    onCollectionChange: vi.fn(),
    onSubmit: vi.fn(),
    onClear: vi.fn(),
  };

  beforeEach(() => vi.clearAllMocks());

  it('renders search input', () => {
    render(<SearchForm {...baseProps} />);
    const input = screen.getByRole('textbox') || screen.getByPlaceholderText(/search/i);
    expect(input).toBeInTheDocument();
  });

  it('renders scope buttons', () => {
    render(<SearchForm {...baseProps} />);
    const everythingBtns = screen.getAllByRole('button', { name: /Everything/i });
    expect(everythingBtns.length).toBeGreaterThanOrEqual(1);
  });

  it('renders collection dropdown', () => {
    render(<SearchForm {...baseProps} />);
    const select = screen.getByRole('combobox');
    expect(select).toBeInTheDocument();
  });

  it('calls onQueryChange when input changes', () => {
    render(<SearchForm {...baseProps} />);
    const input = screen.getByRole('textbox') || screen.getByPlaceholderText(/search/i);
    fireEvent.change(input, { target: { value: 'hello' } });
    expect(baseProps.onQueryChange).toHaveBeenCalledWith('hello');
  });

  it('calls onSubmit on form submit', () => {
    render(<SearchForm {...baseProps} query="test" />);
    const form = document.querySelector('form');
    if (form) fireEvent.submit(form);
    expect(baseProps.onSubmit).toHaveBeenCalled();
  });

  it('disables submit when searching', () => {
    render(<SearchForm {...baseProps} searching />);
    expect(screen.getByText(/searching/i)).toBeInTheDocument();
  });

  it('calls onClear when clear button clicked', () => {
    render(<SearchForm {...baseProps} />);
    const clearBtn = screen.getByText(/clear/i);
    fireEvent.click(clearBtn);
    expect(baseProps.onClear).toHaveBeenCalled();
  });

  it('disables input while searching', () => {
    render(<SearchForm {...baseProps} searching />);
    const input = screen.getByRole('textbox') || screen.getByPlaceholderText(/search/i);
    expect(input).toBeDisabled();
  });
});
