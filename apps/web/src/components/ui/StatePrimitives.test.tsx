import { fireEvent, render, screen } from '@testing-library/react';
import EmptyState from './EmptyState';
import InlineErrorState from './InlineErrorState';
import PageState from './PageState';
import SectionLoadingState from './SectionLoadingState';

describe('state primitives', () => {
  it('renders an empty state action', () => {
    const onAction = jest.fn();
    render(
      <EmptyState
        title="No items"
        description="Create one to get started."
        actionLabel="Create"
        onAction={onAction}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'Create' }));
    expect(onAction).toHaveBeenCalled();
  });

  it('renders an inline error retry action', () => {
    const onRetry = jest.fn();
    render(<InlineErrorState title="Request failed" message="Try again." onRetry={onRetry} />);

    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
    expect(onRetry).toHaveBeenCalled();
  });

  it('renders a page loading state with status semantics', () => {
    render(<PageState variant="loading" title="Loading page" description="Please wait." />);
    expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'Loading page');
  });

  it('renders a section loading state description', () => {
    render(<SectionLoadingState label="Loading section" description="Pulling records." />);
    expect(screen.getByText('Pulling records.')).toBeInTheDocument();
  });
});
