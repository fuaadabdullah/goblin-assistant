'use client';

import HomePageScreen from '@/screens/HomePage';
import { withRouteErrorBoundary } from '@/components/RouteBoundary';

export default withRouteErrorBoundary(HomePageScreen, 'home');
