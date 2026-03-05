import React from 'react';
import { Button } from '../../components/ui';
import { RefreshCw, Play, Pause } from 'lucide-react';

interface DashboardHeaderProps {
  onRefresh: () => void;
  autoRefresh: boolean;
  onToggleAutoRefresh: () => void;
  loading: boolean;
}

export function DashboardHeader({ onRefresh, autoRefresh, onToggleAutoRefresh, loading }: DashboardHeaderProps) {
  return (
    <div className="bg-white rounded-lg border p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-600">System Overview & Status</p>
        </div>
        <div className="flex space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            disabled={loading}
            className="flex items-center space-x-2"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </Button>
          <Button
            variant={autoRefresh ? "default" : "outline"}
            size="sm"
            onClick={onToggleAutoRefresh}
            className="flex items-center space-x-2"
          >
            {autoRefresh ? (
              <>
                <Pause className="h-4 w-4" />
                <span>Stop Auto-refresh</span>
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                <span>Auto-refresh</span>
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
