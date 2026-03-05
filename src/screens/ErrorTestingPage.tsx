import React from 'react';
import { ErrorTestingPanel } from '@/components/ErrorTestingPanel';
import AdminLayout from '@/layout/AdminLayout';
import Seo from '@/components/Seo';

const ErrorTestingPage: React.FC = () => {
  return (
    <AdminLayout mainId="main-content" mainLabel="Error Testing">
      <Seo title="Error Testing" description="Error testing tools (internal)." robots="noindex,nofollow" />
      <div className="container mx-auto py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-text mb-2">
            Error Testing & Datadog Validation
          </h1>
          <p className="text-muted">
            Test Datadog RUM error tracking by generating various types of errors. This page is for
            development and testing purposes only.
          </p>
        </div>

        <ErrorTestingPanel />
      </div>
    </AdminLayout>
  );
};

export default ErrorTestingPage;
