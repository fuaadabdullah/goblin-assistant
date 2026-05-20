import ProvidersPage, { getServerSideProps } from '../../screens/EnhancedProvidersPage';
import AdminLayout from '../../layout/AdminLayout';
import { withRouteErrorBoundary } from '../../components/RouteBoundary';

export { getServerSideProps };

const AdminProvidersContent = withRouteErrorBoundary(
  function AdminProvidersContent() {
    return <ProvidersPage />;
  },
  'adminProviders'
);

export default function AdminProviders() {
  return (
    <AdminLayout fullWidth>
      <AdminProvidersContent />
    </AdminLayout>
  );
}
