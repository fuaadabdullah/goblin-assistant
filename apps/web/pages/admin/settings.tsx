import dynamic from 'next/dynamic';
import AdminLayout from '@/layout/AdminLayout';
import { withRouteErrorBoundary } from '@/components/RouteBoundary';
import PageState from '@/components/ui/PageState';

const SettingsPage = dynamic(() => import('@/screens/SettingsPage'), {
  ssr: false,
  loading: () => (
    <PageState
      variant="loading"
      title="Loading settings"
      description="Preparing provider and account controls."
    />
  ),
});

const AdminSettingsContent = withRouteErrorBoundary(function AdminSettingsContent() {
  return <SettingsPage />;
}, 'adminSettings');

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
