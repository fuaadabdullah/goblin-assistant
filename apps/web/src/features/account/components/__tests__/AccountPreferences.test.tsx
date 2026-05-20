import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

import AccountPreferences from '../AccountPreferences';

describe('AccountPreferences', () => {
  const defaultPrefs = { summaries: true, notifications: true, familyMode: false };
  const onToggle = jest.fn();

  beforeEach(() => jest.clearAllMocks());

  it('renders Preferences heading', () => {
    render(<AccountPreferences preferences={defaultPrefs} onToggle={onToggle} />);
    expect(screen.getByText('Preferences')).toBeInTheDocument();
  });

  it('renders all three preference labels', () => {
    render(<AccountPreferences preferences={defaultPrefs} onToggle={onToggle} />);
    expect(screen.getByText('Auto-summarize long answers')).toBeInTheDocument();
    expect(screen.getByText('Email me important updates')).toBeInTheDocument();
    expect(screen.getByText('Plain-language mode')).toBeInTheDocument();
  });

  it('renders descriptions for each preference', () => {
    render(<AccountPreferences preferences={defaultPrefs} onToggle={onToggle} />);
    expect(screen.getByText(/Keeps replies short/)).toBeInTheDocument();
    expect(screen.getByText(/Only critical changes/)).toBeInTheDocument();
    expect(screen.getByText(/Less jargon/)).toBeInTheDocument();
  });

  it('checks summaries checkbox when true', () => {
    render(<AccountPreferences preferences={defaultPrefs} onToggle={onToggle} />);
    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes[0]).toBeChecked();
  });

  it('unchecks familyMode checkbox when false', () => {
    render(<AccountPreferences preferences={defaultPrefs} onToggle={onToggle} />);
    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes[2]).not.toBeChecked();
  });

  it('calls onToggle with summaries when clicked', () => {
    render(<AccountPreferences preferences={defaultPrefs} onToggle={onToggle} />);
    fireEvent.click(screen.getAllByRole('checkbox')[0]);
    expect(onToggle).toHaveBeenCalledWith('summaries');
  });

  it('calls onToggle with familyMode when clicked', () => {
    render(<AccountPreferences preferences={defaultPrefs} onToggle={onToggle} />);
    fireEvent.click(screen.getAllByRole('checkbox')[2]);
    expect(onToggle).toHaveBeenCalledWith('familyMode');
  });

  it('renders three checkboxes', () => {
    render(<AccountPreferences preferences={defaultPrefs} onToggle={onToggle} />);
    expect(screen.getAllByRole('checkbox')).toHaveLength(3);
  });
});
