import React from 'react';
import HealthHeader from './HealthHeader';

const StatusBar: React.FC = () => {
  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 bg-surface/70 backdrop-blur-sm border-t border-border p-2">
      <div className="max-w-6xl mx-auto flex items-center justify-between text-xs text-muted">
        <div className="flex items-center gap-3">
          <span className="font-mono">GoblinOS</span>
          <span className="hidden sm:inline">•</span>
          <span className="hidden sm:inline">Stable UI</span>
        </div>
        <div className="flex items-center">
          <HealthHeader compact />
        </div>
      </div>
    </div>
  );
};

export default StatusBar;
