import { render } from '@testing-library/react';
import Grid from './Grid';

describe('Grid', () => {
  it('renders children in a grid layout', () => {
    const { getByText } = render(
      <Grid>
        <div>Item 1</div>
        <div>Item 2</div>
        <div>Item 3</div>
      </Grid>
    );

    expect(getByText('Item 1')).toBeInTheDocument();
    expect(getByText('Item 2')).toBeInTheDocument();
    expect(getByText('Item 3')).toBeInTheDocument();
  });

  it('applies default grid classes', () => {
    const { container } = render(
      <Grid>
        <div>Content</div>
      </Grid>
    );

    const grid = container.firstChild as HTMLElement;
    expect(grid).toHaveClass('grid');
    expect(grid).toHaveClass('gap-4'); // default gap=md
  });

  it('renders with different gap sizes', () => {
    const { container, rerender } = render(
      <Grid gap="sm">
        <div>Content</div>
      </Grid>
    );

    let grid = container.firstChild as HTMLElement;
    expect(grid).toHaveClass('gap-2');

    rerender(
      <Grid gap="md">
        <div>Content</div>
      </Grid>
    );
    grid = container.firstChild as HTMLElement;
    expect(grid).toHaveClass('gap-4');

    rerender(
      <Grid gap="lg">
        <div>Content</div>
      </Grid>
    );
    grid = container.firstChild as HTMLElement;
    expect(grid).toHaveClass('gap-6');
  });

  it('renders with default auto columns', () => {
    const { container } = render(
      <Grid>
        <div>Item 1</div>
        <div>Item 2</div>
      </Grid>
    );

    const grid = container.firstChild as HTMLElement;
    expect(grid).toHaveClass('grid-cols-1');
  });

  it('renders with specific column count', () => {
    const { container } = render(
      <Grid columns={2}>
        <div>Item</div>
      </Grid>
    );

    const grid = container.firstChild as HTMLElement;
    expect(grid).toHaveClass('grid-cols-1');
  });

  it('applies custom className', () => {
    const { container } = render(
      <Grid className="custom-grid">
        <div>Content</div>
      </Grid>
    );

    const grid = container.firstChild as HTMLElement;
    expect(grid).toHaveClass('custom-grid');
    expect(grid).toHaveClass('grid');
  });

  it('combines all props correctly', () => {
    const { container } = render(
      <Grid columns={3} gap="lg" className="special-grid">
        <div>Item 1</div>
        <div>Item 2</div>
        <div>Item 3</div>
      </Grid>
    );

    const grid = container.firstChild as HTMLElement;
    expect(grid).toHaveClass('grid');
    expect(grid).toHaveClass('gap-6');
    expect(grid).toHaveClass('special-grid');
  });
});
