'use client';

import ChatPageScreen from '@/screens/ChatPage';
import { withRouteErrorBoundary } from '@/components/RouteBoundary';

export default withRouteErrorBoundary(ChatPageScreen, 'chat');
