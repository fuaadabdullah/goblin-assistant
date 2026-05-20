import HomePageScreen, { getServerSideProps } from '../screens/HomePage';
import { withRouteErrorBoundary } from '../components/RouteBoundary';

export { getServerSideProps };

export default withRouteErrorBoundary(HomePageScreen, 'home');
