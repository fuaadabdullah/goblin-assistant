'use client';

import LoginPageScreen from '@/screens/LoginPage';
import { withRouteErrorBoundary } from '@/components/RouteBoundary';

export default withRouteErrorBoundary(LoginPageScreen, 'login');
