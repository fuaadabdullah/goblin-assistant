import ChatPageScreen, { getServerSideProps } from '../screens/ChatPage';
import { withRouteErrorBoundary } from '../components/RouteBoundary';

export { getServerSideProps };

export default withRouteErrorBoundary(ChatPageScreen, 'chat');
