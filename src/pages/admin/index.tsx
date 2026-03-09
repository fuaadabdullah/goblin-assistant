import dynamic from 'next/dynamic';
import AdminLayout from '../../layout/AdminLayout';
import { withRouteErrorBoundary } from '../../components/RouteBoundary';

const EnhancedDashboard = dynamic(
  () => import('../../components/EnhancedDashboard'),
  {
    ssr: false,
    loading: () => (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-sm text-muted">Loading dashboard...</p>
        </div>
      </div>
    ),
  }
);

const AdminDashboardContent = withRouteErrorBoundary(
  function AdminDashboardContent() {
    return <EnhancedDashboard />;
  },
  'adminIndex'
);

export default function Admin() {
  return (
    <AdminLayout mainId="main-content" mainLabel="Admin Dashboard">
      <AdminDashboardContent />
    </AdminLayout>
  );
}

// Prevent static generation
export const getServerSideProps = async () => {
  return { props: {} };
};
