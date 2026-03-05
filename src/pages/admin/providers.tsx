import ProvidersPage, { getServerSideProps } from '../../screens/EnhancedProvidersPage';
import AdminLayout from '../../layout/AdminLayout';

export { getServerSideProps };

export default function AdminProviders() {
  return (
    <AdminLayout fullWidth>
      <ProvidersPage />
    </AdminLayout>
  );
}
