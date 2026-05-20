import ProvidersManagerScreen from '../features/admin/providers/ProvidersManagerScreen';

export default function EnhancedProvidersPage() {
  return <ProvidersManagerScreen />;
}

// Prevent static generation - this page uses react-query
export const getServerSideProps = async () => {
  return { props: {} };
};

