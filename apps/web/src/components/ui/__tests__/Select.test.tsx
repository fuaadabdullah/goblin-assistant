import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
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
  it('renders SelectTrigger with SelectValue placeholder', () => {
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
    expect(screen.getByText('Pick one')).toBeInTheDocument();
  });

  it('renders SelectLabel inside SelectGroup with SelectItem', () => {
    render(
      <Select open>
        <SelectTrigger aria-label="group-select">
          <SelectValue placeholder="Choose" />
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            <SelectLabel>Group Label</SelectLabel>
            <SelectItem value="a">A</SelectItem>
          </SelectGroup>
        </SelectContent>
      </Select>
    );
    expect(screen.getByText('Group Label')).toBeInTheDocument();
    expect(screen.getByText('A')).toBeInTheDocument();
  });

  it('renders SelectSeparator', () => {
    render(
      <Select open>
        <SelectTrigger aria-label="separator-select">
          <SelectValue placeholder="Choose" />
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            <SelectItem value="a">A</SelectItem>
            <SelectSeparator className="separator-extra" />
            <SelectItem value="b">B</SelectItem>
          </SelectGroup>
        </SelectContent>
      </Select>
    );
    expect(document.querySelector('.separator-extra')).toBeInTheDocument();
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

  it('applies className to SelectContent and SelectItem', () => {
    render(
      <Select open>
        <SelectTrigger aria-label="test-content">
          <SelectValue placeholder="Test" />
        </SelectTrigger>
        <SelectContent className="content-extra">
          <SelectGroup>
            <SelectLabel className="label-extra">Label</SelectLabel>
            <SelectItem value="item-a" className="item-extra">
              Item A
            </SelectItem>
          </SelectGroup>
        </SelectContent>
      </Select>
    );

    expect(document.querySelector('.content-extra')).toBeInTheDocument();
    expect(screen.getByText('Label').className).toContain('label-extra');
    expect(screen.getByText('Item A').closest('[role="option"]')?.className).toContain(
      'item-extra'
    );
  });

  it('calls onValueChange when selecting an item', () => {
    const onValueChange = vi.fn();
    render(
      <Select open onValueChange={onValueChange}>
        <SelectTrigger aria-label="choose-value">
          <SelectValue placeholder="Pick one" />
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            <SelectItem value="alpha">Alpha</SelectItem>
            <SelectItem value="beta">Beta</SelectItem>
          </SelectGroup>
        </SelectContent>
      </Select>
    );

    fireEvent.click(screen.getByText('Beta'));
    expect(onValueChange).toHaveBeenCalledWith('beta');
  });
});
