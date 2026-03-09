import SettingsPage from '../../screens/SettingsPage';
import AdminLayout from '../../layout/AdminLayout';
import { withRouteErrorBoundary } from '../../components/RouteBoundary';

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
