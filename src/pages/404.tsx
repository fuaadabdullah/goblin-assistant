import NotFoundPageScreen from '../screens/NotFoundPage';
import { withRouteErrorBoundary } from '../components/RouteBoundary';

export default withRouteErrorBoundary(NotFoundPageScreen, 'notFound');
