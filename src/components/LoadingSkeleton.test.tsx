import { describe, it, expect } from '@jest/globals';
import { render } from '@testing-library/react';
import {
  StatusCardSkeleton,
  StatCardSkeleton,
  ListSkeleton,
  ListItemSkeleton,
  ProviderCardSkeleton,
  DashboardSkeleton,
} from './LoadingSkeleton';

describe('LoadingSkeleton Components', () => {
  describe('StatusCardSkeleton', () => {
    it('renders with loading accessibility attributes', () => {
      const { getByLabelText } = render(<StatusCardSkeleton />);

      const skeleton = getByLabelText('Loading card');
      expect(skeleton).toBeInTheDocument();
      expect(skeleton).toHaveAttribute('role', 'status');
    });

    it('displays animated skeleton elements', () => {
      const { container } = render(<StatusCardSkeleton />);

      // Should have multiple skeleton elements
      const skeletonElements = container.querySelectorAll('.animate-pulse');
      expect(skeletonElements.length).toBeGreaterThan(0);
    });
  });

  describe('StatCardSkeleton', () => {
    it('renders with loading label', () => {
      const { getByLabelText } = render(<StatCardSkeleton />);

      const skeleton = getByLabelText('Loading statistic');
      expect(skeleton).toBeInTheDocument();
    });

    it('has aria-busy attribute', () => {
      const { getByLabelText } = render(<StatCardSkeleton />);

      const skeleton = getByLabelText('Loading statistic');
      expect(skeleton).toHaveAttribute('role', 'status');
    });
  });

  describe('ListSkeleton', () => {
    it('renders default number of items', () => {
      const { getAllByLabelText } = render(<ListSkeleton />);

      const items = getAllByLabelText('Loading list item');
      expect(items.length).toBe(5); // Default count
    });

    it('renders custom number of items', () => {
      const { getAllByLabelText } = render(<ListSkeleton count={3} />);

      const items = getAllByLabelText('Loading list item');
      expect(items.length).toBe(3);
    });

    it('each item has aria-busy attribute', () => {
      const { getAllByLabelText } = render(<ListSkeleton count={2} />);

      const items = getAllByLabelText('Loading list item');
      items.forEach(item => {
        expect(item).toHaveAttribute('role', 'status');
      });
    });
  });

  describe('ListItemSkeleton', () => {
    it('renders with loading label', () => {
      const { getByLabelText } = render(<ListItemSkeleton />);

      const skeleton = getByLabelText('Loading list item');
      expect(skeleton).toBeInTheDocument();
    });
  });

  describe('ProviderCardSkeleton', () => {
    it('renders with loading label', () => {
      const { getByLabelText } = render(<ProviderCardSkeleton />);

      const skeleton = getByLabelText('Loading provider');
      expect(skeleton).toBeInTheDocument();
      expect(skeleton).toHaveAttribute('role', 'status');
    });

    it('displays multiple skeleton elements', () => {
      const { container } = render(<ProviderCardSkeleton />);

      const skeletonElements = container.querySelectorAll('.animate-pulse');
      expect(skeletonElements.length).toBeGreaterThan(0);
    });
  });

  describe('DashboardSkeleton', () => {
    it('renders dashboard loading state', () => {
      const { getByLabelText } = render(<DashboardSkeleton />);

      const skeleton = getByLabelText('Loading dashboard');
      expect(skeleton).toBeInTheDocument();
      expect(skeleton).toHaveAttribute('role', 'status');
    });

    it('renders multiple status card skeletons', () => {
      const { getAllByLabelText } = render(<DashboardSkeleton />);

      // Should contain multiple status card skeletons
      const statusCards = getAllByLabelText('Loading card');
      expect(statusCards.length).toBeGreaterThan(0);
    });

    it('renders stat card skeletons', () => {
      const { getAllByLabelText } = render(<DashboardSkeleton />);

      // Should contain stat card skeletons
      const statCards = getAllByLabelText('Loading statistic');
      expect(statCards.length).toBeGreaterThan(0);
    });

    it('has proper ARIA live region', () => {
      const { getByLabelText } = render(<DashboardSkeleton />);

      const skeleton = getByLabelText('Loading dashboard');
      expect(skeleton).toHaveAttribute('aria-live', 'polite');
    });
  });
});
