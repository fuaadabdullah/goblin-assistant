import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import {
  Select,
  SelectGroup,
  SelectValue,
  SelectTrigger,
  SelectContent,
  SelectLabel,
  SelectItem,
  SelectSeparator,
} from '../Select';

describe('Select components', () => {
  it('renders SelectTrigger with SelectValue', () => {
    render(
      <Select>
        <SelectTrigger aria-label="choose">
          <SelectValue placeholder="Pick one" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="a">Option A</SelectItem>
        </SelectContent>
      </Select>
    );
    expect(screen.getByRole('combobox', { name: 'choose' })).toBeInTheDocument();
  });

  it('renders SelectLabel', () => {
    render(
      <Select>
        <SelectContent>
          <SelectLabel>Group Label</SelectLabel>
          <SelectItem value="a">A</SelectItem>
        </SelectContent>
      </Select>
    );
    expect(screen.getByText('Group Label')).toBeInTheDocument();
  });

  it('renders SelectSeparator', () => {
    const { container } = render(
      <Select>
        <SelectContent>
          <SelectSeparator />
        </SelectContent>
      </Select>
    );
    expect(container.querySelector('[role="separator"]')).toBeInTheDocument();
  });

  it('applies className to SelectTrigger', () => {
    render(
      <Select>
        <SelectTrigger aria-label="test" className="custom-class">
          <SelectValue placeholder="Test" />
        </SelectTrigger>
      </Select>
    );
    const trigger = screen.getByRole('combobox');
    expect(trigger.className).toContain('custom-class');
  });
});