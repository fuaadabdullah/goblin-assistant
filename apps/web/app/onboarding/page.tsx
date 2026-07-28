'use client';

import OnboardingWizard from '@/features/onboarding/OnboardingWizard';
import { withRouteErrorBoundary } from '@/components/RouteBoundary';

export default withRouteErrorBoundary(OnboardingWizard, 'onboarding');
