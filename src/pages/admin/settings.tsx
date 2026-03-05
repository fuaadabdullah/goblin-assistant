import SettingsPage from '../../screens/SettingsPage';
import AdminLayout from '../../layout/AdminLayout';

export default function AdminSettings() {
  return (
    <AdminLayout mainId="main-content" mainLabel="Admin Settings">
      <SettingsPage />
    </AdminLayout>
  );
}
