"use client";

import { useState, useEffect } from "react";
import { Card, Button } from "@/components/ui";
import { 
  RefreshCw, 
  Database, 
  TrendingUp, 
  TrendingDown, 
  Activity,
  BarChart3
} from "lucide-react";
import { TooltipProvider } from "@/components/ui/Tooltip";

interface PerformanceData {
  timestamp: string;
  cache: {
    hit_ratio: number;
    hits: number;
    misses: number;
    total_requests: number;
    memory_usage: string;
    connected_clients: string;
  };
  performance: {
    avg_response_time: number;
    avg_error_rate: number;
    total_requests: number;
    total_errors: number;
  };
  tasks: {
    total_tasks: number;
    completed_tasks: number;
    failed_tasks: number;
    running_tasks: number;
    queued_tasks: number;
  };
  usage: {
    streaming_tasks: number;
    non_streaming_tasks: number;
    streaming_percentage: number;
  };
}

export function PerformanceSnapshot() {
  const [performanceData, setPerformanceData] = useState<PerformanceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Wrap in TooltipProvider to fix the build error
  return (
    <TooltipProvider>
      <PerformanceSnapshotContent 
        performanceData={performanceData}
        loading={loading}
        error={error}
        setPerformanceData={setPerformanceData}
        setLoading={setLoading}
        setError={setError}
      />
    </TooltipProvider>
  );
}

function PerformanceSnapshotContent({ 
  performanceData, 
  loading, 
  error, 
  setPerformanceData, 
  setLoading, 
  setError 
}: {
  performanceData: PerformanceData | null;
  loading: boolean;
  error: string | null;
  setPerformanceData: React.Dispatch<React.SetStateAction<PerformanceData | null>>;
  setLoading: React.Dispatch<React.SetStateAction<boolean>>;
  setError: React.Dispatch<React.SetStateAction<string | null>>;
}) {

  const fetchPerformanceData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/ops/performance/snapshot');
      if (!response.ok) {
        throw new Error('Failed to fetch performance data');
      }
      const data = await response.json();
      setPerformanceData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPerformanceData();
    // Refresh every 30 seconds
    const interval = setInterval(fetchPerformanceData, 30000);
    return () => clearInterval(interval);
  }, []);

  const formatResponseTime = (ms: number) => {
    if (ms < 1000) return `${ms.toFixed(0)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-8">
        <div className="flex items-center space-x-2">
          <RefreshCw className="h-6 w-6 animate-spin text-indigo-600" />
          <span>Loading performance metrics...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <Card className="border-red-200">
        <div className="p-6">
          <div className="flex items-center space-x-3">
            <Activity className="h-6 w-6 text-red-500" />
            <div>
              <h3 className="font-semibold text-red-900">Error Loading Performance Data</h3>
              <p className="text-red-600 text-sm">{error}</p>
            </div>
            <Button variant="primary" size="sm" onClick={fetchPerformanceData}>
              Retry
            </Button>
          </div>
        </div>
      </Card>
    );
  }

  if (!performanceData) {
    return null;
  }

  const { cache, performance, tasks, usage } = performanceData;

  return (
    <div className="space-y-6">
      {/* Cache Performance */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card className="border-blue-200">
          <div className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Cache Hit Ratio</p>
                <h3 className="text-2xl font-bold text-gray-900 mt-1">
                  {cache.hit_ratio.toFixed(1)}%
                </h3>
              </div>
              <Database className="h-8 w-8 text-blue-500" />
            </div>
            <div className="mt-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Hits:</span>
                <span className="font-medium">{cache.hits.toLocaleString()}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Misses:</span>
                <span className="font-medium">{cache.misses.toLocaleString()}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Memory:</span>
                <span className="font-medium">{cache.memory_usage}</span>
              </div>
            </div>
          </div>
        </Card>

        <Card className="border-green-200">
          <div className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Avg Response Time</p>
                <h3 className="text-2xl font-bold text-gray-900 mt-1">
                  {formatResponseTime(performance.avg_response_time)}
                </h3>
              </div>
              <TrendingUp className="h-8 w-8 text-green-500" />
            </div>
            <div className="mt-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Total Requests:</span>
                <span className="font-medium">{performance.total_requests.toLocaleString()}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Total Errors:</span>
                <span className="font-medium">{performance.total_errors.toLocaleString()}</span>
              </div>
            </div>
          </div>
        </Card>

        <Card className="border-yellow-200">
          <div className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Error Rate</p>
                <h3 className="text-2xl font-bold text-gray-900 mt-1">
                  {performance.avg_error_rate.toFixed(2)}%
                </h3>
              </div>
              <TrendingDown className="h-8 w-8 text-yellow-500" />
            </div>
            <div className="mt-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Success Rate:</span>
                <span className="font-medium">{(100 - performance.avg_error_rate).toFixed(2)}%</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Connected Clients:</span>
                <span className="font-medium">{cache.connected_clients}</span>
              </div>
            </div>
          </div>
        </Card>

        <Card className="border-purple-200">
          <div className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Streaming Usage</p>
                <h3 className="text-2xl font-bold text-gray-900 mt-1">
                  {usage.streaming_percentage.toFixed(1)}%
                </h3>
              </div>
              <BarChart3 className="h-8 w-8 text-purple-500" />
            </div>
            <div className="mt-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Streaming Tasks:</span>
                <span className="font-medium">{usage.streaming_tasks.toLocaleString()}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Non-Streaming:</span>
                <span className="font-medium">{usage.non_streaming_tasks.toLocaleString()}</span>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Task Status */}
      <Card className="border-gray-200">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900">Task Status</h3>
            <Button variant="ghost" size="sm" onClick={fetchPerformanceData}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{tasks.total_tasks}</div>
              <div className="text-sm text-gray-600">Total</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">{tasks.completed_tasks}</div>
              <div className="text-sm text-gray-600">Completed</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">{tasks.failed_tasks}</div>
              <div className="text-sm text-gray-600">Failed</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-yellow-600">{tasks.running_tasks}</div>
              <div className="text-sm text-gray-600">Running</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">{tasks.queued_tasks}</div>
              <div className="text-sm text-gray-600">Queued</div>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
