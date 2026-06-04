import React from 'react';
import { render, screen } from '@testing-library/react';

jest.mock('../../features/onboarding/OnboardingWizard', () => {
  return function MockOnboardingWizard() {
    return <div data-testid="onboarding-wizard">Wizard</div>;
  };
});
jest.mock('../../components/RouteBoundary', () => ({
  withRouteErrorBoundary: (Component: React.ComponentType) => Component,
}));

import OnboardingPage from '../onboarding';

describe('onboarding page', () => {
  it('renders onboarding wizard', () => {
    render(<OnboardingPage />);
    expect(screen.getByTestId('onboarding-wizard')).toBeInTheDocument();
  });
});
