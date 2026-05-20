import dynamic from 'next/dynamic';
import SandboxSkeleton from '../features/sandbox/components/SandboxSkeleton';

const SandboxScreen = dynamic(() => import('../features/sandbox/SandboxScreen'), {
  loading: () => <SandboxSkeleton />,
});

const SandboxPage = () => <SandboxScreen />;

export default SandboxPage;
