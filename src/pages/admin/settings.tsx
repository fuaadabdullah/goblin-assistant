import dynamic from 'next/dynamic';
import AdminLayout from '../../layout/AdminLayout';
import { withRouteErrorBoundary } from '../../components/RouteBoundary';

const SettingsPage = dynamic(() => import('../../screens/SettingsPage'), {
  ssr: false,
  loading: () => (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
        <p className="text-sm text-muted">Loading settings...</p>
      </div>
    </div>
  ),
});

const AdminSettingsContent = withRouteErrorBoundary(
  function AdminSettingsContent() {
    return <SettingsPage />;
  },
  'adminSettings'
);

export default function AdminSettings() {
  return (
    <AdminLayout mainId="main-content" mainLabel="Admin Settings">
      <AdminSettingsContent />
    </AdminLayout>
  );
}

export const getServerSideProps = async () => {
  return { props: {} };
};
