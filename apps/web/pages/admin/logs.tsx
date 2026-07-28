import MonitoringScreen from '@/screens/MonitoringScreen';
import AdminLayout from '@/layout/AdminLayout';
import { withRouteErrorBoundary } from '@/components/RouteBoundary';

const AdminMonitoringContent = withRouteErrorBoundary(
  function AdminMonitoringContent() {
    return <MonitoringScreen />;
  },
  'adminLogs'
);

export default function AdminLogs() {
  return (
    <AdminLayout fullWidth>
      <AdminMonitoringContent />
    </AdminLayout>
  );
}
