import LoginPage, { getServerSideProps } from '../screens/LoginPage';
import { withRouteErrorBoundary } from '../components/RouteBoundary';

export { getServerSideProps };

function RegisterPage() {
  return <LoginPage initialMode="register" />;
}

export default withRouteErrorBoundary(RegisterPage, 'register');
