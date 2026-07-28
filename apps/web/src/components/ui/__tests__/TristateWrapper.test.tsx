import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';

import TristateWrapper from '../TristateWrapper';

describe('TristateWrapper', () => {
  it('renders children when no state is active', () => {
    render(
      <TristateWrapper>
        <div>content</div>
      </TristateWrapper>
    );

    expect(screen.getByText('content')).toBeInTheDocument();
  });

  it('renders the page loading state by default', () => {
    render(
      <TristateWrapper loading loadingTitle="Loading data" loadingDescription="Just a sec.">
        <div>content</div>
      </TristateWrapper>
    );

    expect(screen.getByRole('status', { name: 'Loading data' })).toBeInTheDocument();
    expect(screen.getByText('Loading data')).toBeInTheDocument();
    expect(screen.getByText('Just a sec.')).toBeInTheDocument();
  });

  it('prefers a custom loading child over built-in states', () => {
    render(
      <TristateWrapper loading loadingChild={<div>custom loading</div>}>
        <div>content</div>
      </TristateWrapper>
    );

    expect(screen.getByText('custom loading')).toBeInTheDocument();
    expect(screen.queryByText('content')).not.toBeInTheDocument();
  });

  it('renders the section loading state in plain mode', () => {
    render(
      <TristateWrapper loading plain loadingTitle="Loading records" loadingDescription="Working">
        <div>content</div>
      </TristateWrapper>
    );

    expect(screen.getByRole('status', { name: 'Loading records' })).toBeInTheDocument();
    expect(screen.getByText('Working')).toBeInTheDocument();
  });

  it('renders the page error state and retry action', () => {
    const onRetry = vi.fn();

    render(
      <TristateWrapper
        error={new Error('Backend offline')}
        errorTitle="Data failed"
        retryLabel="Retry now"
        onRetry={onRetry}
      >
        <div>content</div>
      </TristateWrapper>
    );

    expect(screen.getByText('Data failed')).toBeInTheDocument();
    expect(screen.getByText('Backend offline')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Retry now' }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('prefers a custom error child over built-in states', () => {
    render(
      <TristateWrapper error="Boom" errorChild={<div>custom error</div>}>
        <div>content</div>
      </TristateWrapper>
    );

    expect(screen.getByText('custom error')).toBeInTheDocument();
    expect(screen.queryByText('content')).not.toBeInTheDocument();
  });

  it('renders the plain error state', () => {
    const onRetry = vi.fn();

    render(
      <TristateWrapper error="Request failed" plain retryLabel="Try again" onRetry={onRetry}>
        <div>content</div>
      </TristateWrapper>
    );

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByText('Request failed')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('renders the page empty state and custom empty action', () => {
    const onEmptyAction = vi.fn();

    render(
      <TristateWrapper
        empty
        emptyTitle="Nothing here"
        emptyDescription="Add your first item."
        emptyActionLabel="Create item"
        emptyActionHref="/items/new"
        emptySecondaryAction={<button type="button">Help</button>}
        onEmptyAction={onEmptyAction}
      >
        <div>content</div>
      </TristateWrapper>
    );

    expect(screen.getByText('Nothing here')).toBeInTheDocument();
    expect(screen.getByText('Add your first item.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Create item' })).toHaveAttribute('href', '/items/new');
    expect(screen.getByRole('button', { name: 'Help' })).toBeInTheDocument();
  });

  it('prefers a custom empty child over built-in states', () => {
    render(
      <TristateWrapper empty emptyChild={<div>custom empty</div>}>
        <div>content</div>
      </TristateWrapper>
    );

    expect(screen.getByText('custom empty')).toBeInTheDocument();
    expect(screen.queryByText('content')).not.toBeInTheDocument();
  });

  it('renders the plain empty state', () => {
    const onEmptyAction = vi.fn();

    render(
      <TristateWrapper
        empty
        plain
        emptyTitle="No results"
        emptyDescription="Try a different filter."
        emptyActionLabel="Refresh"
        onEmptyAction={onEmptyAction}
      >
        <div>content</div>
      </TristateWrapper>
    );

    expect(screen.getByText('No results')).toBeInTheDocument();
    expect(screen.getByText('Try a different filter.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Refresh' }));
    expect(onEmptyAction).toHaveBeenCalledTimes(1);
  });
});
