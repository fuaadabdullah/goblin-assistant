import LoginPageScreen, { getServerSideProps } from '../screens/LoginPage';
import { withRouteErrorBoundary } from '../components/RouteBoundary';

export { getServerSideProps };

export default withRouteErrorBoundary(LoginPageScreen, 'login');
