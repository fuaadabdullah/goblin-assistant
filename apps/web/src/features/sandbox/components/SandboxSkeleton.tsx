import TwoColumnLayout from '../../../components/TwoColumnLayout';

const SkeletonBlock = ({ className }: { className: string }) => (
  <div className={`animate-pulse rounded-xl bg-surface-hover ${className}`} />
);

const SandboxSkeleton = () => (
  <div className="min-h-[calc(100vh-64px)] bg-bg">
    <TwoColumnLayout
      sidebar={
        <div className="space-y-4">
          <SkeletonBlock className="h-6 w-24" />
          <SkeletonBlock className="h-3 w-full" />
          <SkeletonBlock className="h-10 w-full" />
          <SkeletonBlock className="h-24 w-full" />
          <SkeletonBlock className="h-32 w-full" />
        </div>
      }
    >
      <div className="space-y-6">
        <div className="space-y-3">
          <SkeletonBlock className="h-8 w-48" />
          <SkeletonBlock className="h-4 w-96" />
        </div>
        <SkeletonBlock className="h-64 w-full" />
        <SkeletonBlock className="h-64 w-full" />
      </div>
    </TwoColumnLayout>
  </div>
);

export default SandboxSkeleton;
