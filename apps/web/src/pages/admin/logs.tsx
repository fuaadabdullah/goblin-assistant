import LogsPage from '../../screens/LogsPage';
import AdminLayout from '../../layout/AdminLayout';
import { withRouteErrorBoundary } from '../../components/RouteBoundary';

const AdminLogsContent = withRouteErrorBoundary(
  function AdminLogsContent() {
    return <LogsPage />;
  },
  'adminLogs'
);

export default function AdminLogs() {
  return (
    <AdminLayout fullWidth>
      <AdminLogsContent />
    </AdminLayout>
  );
}
